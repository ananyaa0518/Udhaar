-- Run after 20261108_atomic_transactions.sql.
-- Existing demo rows are intentionally left with merchant_id NULL. Review and
-- assign them manually only after identifying the correct Supabase user.

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS merchant_id uuid REFERENCES auth.users(id);

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS merchant_id uuid REFERENCES auth.users(id);

DROP INDEX IF EXISTS public.transactions_idempotency_key_unique;
DROP FUNCTION IF EXISTS public.record_transaction(uuid, text, numeric, text, text);

UPDATE public.transactions AS t
SET merchant_id = c.merchant_id
FROM public.customers AS c
WHERE t.customer_id = c.id
  AND t.merchant_id IS NULL
  AND c.merchant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS customers_merchant_id_idx
    ON public.customers (merchant_id);
CREATE INDEX IF NOT EXISTS transactions_merchant_id_idx
    ON public.transactions (merchant_id);

CREATE OR REPLACE VIEW public.customer_balances AS
SELECT
    c.id AS customer_id,
    c.name,
    COALESCE(SUM(
        CASE
            WHEN t.transaction_type = 'credit' THEN t.amount
            WHEN t.transaction_type = 'payment' THEN -t.amount
            ELSE 0
        END
    ), 0) AS outstanding_balance,
    c.merchant_id,
    c.phone,
    c.preferred_language
FROM public.customers AS c
LEFT JOIN public.transactions AS t
    ON t.customer_id = c.id
   AND t.merchant_id = c.merchant_id
GROUP BY c.id, c.merchant_id, c.name, c.phone, c.preferred_language;

ALTER VIEW public.customer_balances SET (security_invoker = true);

CREATE UNIQUE INDEX IF NOT EXISTS transactions_merchant_idempotency_key_unique
    ON public.transactions (merchant_id, idempotency_key)
    WHERE merchant_id IS NOT NULL AND idempotency_key IS NOT NULL;

ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customers_select_own ON public.customers;
DROP POLICY IF EXISTS customers_insert_own ON public.customers;
DROP POLICY IF EXISTS customers_update_own ON public.customers;
DROP POLICY IF EXISTS transactions_select_own ON public.transactions;
DROP POLICY IF EXISTS transactions_insert_own ON public.transactions;
DROP POLICY IF EXISTS transactions_update_own ON public.transactions;

CREATE POLICY customers_select_own ON public.customers
    FOR SELECT USING (merchant_id = auth.uid());
CREATE POLICY customers_insert_own ON public.customers
    FOR INSERT WITH CHECK (merchant_id = auth.uid());
CREATE POLICY customers_update_own ON public.customers
    FOR UPDATE USING (merchant_id = auth.uid())
    WITH CHECK (merchant_id = auth.uid());
CREATE POLICY transactions_select_own ON public.transactions
    FOR SELECT USING (merchant_id = auth.uid());
CREATE POLICY transactions_insert_own ON public.transactions
    FOR INSERT WITH CHECK (
        merchant_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM public.customers c
            WHERE c.id = customer_id AND c.merchant_id = auth.uid()
        )
    );
CREATE POLICY transactions_update_own ON public.transactions
    FOR UPDATE USING (merchant_id = auth.uid())
    WITH CHECK (merchant_id = auth.uid());

CREATE OR REPLACE FUNCTION public.record_transaction(
    p_customer_id uuid,
    p_merchant_id uuid,
    p_transaction_type text,
    p_amount numeric,
    p_note text,
    p_idempotency_key text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    customer_row public.customers%ROWTYPE;
    existing_transaction public.transactions%ROWTYPE;
    inserted_transaction public.transactions%ROWTYPE;
    current_balance numeric;
BEGIN
    IF p_merchant_id IS NULL OR p_merchant_id <> auth.uid() THEN
        RAISE EXCEPTION 'Authenticated merchant is required.' USING ERRCODE = '42501';
    END IF;
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Amount must be positive.' USING ERRCODE = '22023';
    END IF;
    IF p_transaction_type NOT IN ('credit', 'payment') THEN
        RAISE EXCEPTION 'Transaction type must be credit or payment.' USING ERRCODE = '22023';
    END IF;
    IF p_idempotency_key IS NULL OR btrim(p_idempotency_key) = '' THEN
        RAISE EXCEPTION 'Idempotency key is required.' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO customer_row
    FROM public.customers
    WHERE id = p_customer_id AND merchant_id = p_merchant_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Customer not found.' USING ERRCODE = 'P0002';
    END IF;

    SELECT * INTO existing_transaction
    FROM public.transactions
    WHERE merchant_id = p_merchant_id AND idempotency_key = p_idempotency_key;
    IF FOUND THEN
        IF existing_transaction.customer_id <> p_customer_id
           OR existing_transaction.transaction_type <> p_transaction_type
           OR existing_transaction.amount <> p_amount
           OR existing_transaction.note IS DISTINCT FROM p_note THEN
            RAISE EXCEPTION 'Idempotency key was already used for a different transaction.'
                USING ERRCODE = '23505';
        END IF;
        SELECT COALESCE(SUM(
            CASE WHEN transaction_type = 'credit' THEN amount
                 WHEN transaction_type = 'payment' THEN -amount ELSE 0 END
        ), 0) INTO current_balance
        FROM public.transactions
        WHERE customer_id = p_customer_id AND merchant_id = p_merchant_id;
        RETURN jsonb_build_object(
            'transaction', to_jsonb(existing_transaction),
            'outstanding_balance', current_balance,
            'idempotent_replay', true
        );
    END IF;

    SELECT COALESCE(SUM(
        CASE WHEN transaction_type = 'credit' THEN amount
             WHEN transaction_type = 'payment' THEN -amount ELSE 0 END
    ), 0) INTO current_balance
    FROM public.transactions
    WHERE customer_id = p_customer_id AND merchant_id = p_merchant_id;

    IF p_transaction_type = 'payment' AND p_amount > current_balance THEN
        RAISE EXCEPTION 'Payment exceeds outstanding balance. Current balance is ₹%.',
            to_char(current_balance, 'FM999999999990.00') USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.transactions (
        customer_id, merchant_id, transaction_type, amount, note, idempotency_key
    ) VALUES (
        p_customer_id, p_merchant_id, p_transaction_type, p_amount, p_note, p_idempotency_key
    ) RETURNING * INTO inserted_transaction;

    current_balance := current_balance +
        CASE WHEN p_transaction_type = 'credit' THEN p_amount ELSE -p_amount END;
    RETURN jsonb_build_object(
        'transaction', to_jsonb(inserted_transaction),
        'outstanding_balance', current_balance,
        'idempotent_replay', false
    );
END;
$$;

CREATE TABLE IF NOT EXISTS public.transaction_audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id uuid NOT NULL REFERENCES public.transactions(id),
    merchant_id uuid NOT NULL REFERENCES auth.users(id),
    previous_amount numeric NOT NULL,
    new_amount numeric NOT NULL,
    previous_transaction_type text NOT NULL,
    new_transaction_type text NOT NULL,
    previous_note text,
    new_note text,
    action text NOT NULL DEFAULT 'correction',
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.transaction_audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY transaction_audit_logs_own ON public.transaction_audit_logs
    FOR SELECT USING (merchant_id = auth.uid());

CREATE OR REPLACE FUNCTION public.update_transaction(
    p_transaction_id uuid,
    p_merchant_id uuid,
    p_amount numeric,
    p_transaction_type text,
    p_note text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    old_tx public.transactions%ROWTYPE;
    updated_transaction public.transactions%ROWTYPE;
    new_balance numeric;
BEGIN
    IF p_merchant_id IS NULL OR p_merchant_id <> auth.uid() THEN
        RAISE EXCEPTION 'Authenticated merchant is required.' USING ERRCODE = '42501';
    END IF;
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Amount must be positive.' USING ERRCODE = '22023';
    END IF;
    IF p_transaction_type NOT IN ('credit', 'payment') THEN
        RAISE EXCEPTION 'Transaction type must be credit or payment.' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO old_tx
    FROM public.transactions
    WHERE id = p_transaction_id AND merchant_id = p_merchant_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transaction not found.' USING ERRCODE = 'P0002';
    END IF;

    PERFORM 1 FROM public.customers
    WHERE id = old_tx.customer_id AND merchant_id = p_merchant_id
    FOR UPDATE;

    SELECT COALESCE(SUM(
        CASE WHEN transaction_type = 'credit' THEN amount
             WHEN transaction_type = 'payment' THEN -amount ELSE 0 END
    ), 0)
    - CASE WHEN old_tx.transaction_type = 'credit' THEN old_tx.amount ELSE -old_tx.amount END
    + CASE WHEN p_transaction_type = 'credit' THEN p_amount ELSE -p_amount END
    INTO new_balance
    FROM public.transactions
    WHERE customer_id = old_tx.customer_id AND merchant_id = p_merchant_id;

    IF new_balance < 0 THEN
        RAISE EXCEPTION 'Correction would make the outstanding balance negative.'
            USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.transaction_audit_logs (
        transaction_id, merchant_id, previous_amount, new_amount,
        previous_transaction_type, new_transaction_type,
        previous_note, new_note
    ) VALUES (
        old_tx.id, p_merchant_id, old_tx.amount, p_amount,
        old_tx.transaction_type, p_transaction_type, old_tx.note, p_note
    );

    UPDATE public.transactions
    SET amount = p_amount, transaction_type = p_transaction_type, note = p_note
    WHERE id = old_tx.id
    RETURNING * INTO updated_transaction;

    RETURN jsonb_build_object(
        'transaction', to_jsonb(updated_transaction),
        'outstanding_balance', new_balance
    );
END;
$$;

REVOKE ALL ON FUNCTION public.record_transaction(uuid, uuid, text, numeric, text, text)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.record_transaction(uuid, uuid, text, numeric, text, text)
    TO service_role;
REVOKE ALL ON FUNCTION public.update_transaction(uuid, uuid, numeric, text, text)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_transaction(uuid, uuid, numeric, text, text)
    TO service_role;
