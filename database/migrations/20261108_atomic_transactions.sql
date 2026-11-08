-- Udhaar Voice: atomic transaction recording and temporary idempotency.
--
-- This project does not have merchant authentication yet. Until a merchant_id
-- exists on customers and transactions, idempotency_key is globally unique.
-- When merchant ownership is added, replace this index with a composite
-- unique index on (merchant_id, idempotency_key), and add merchant validation
-- to record_transaction.

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS idempotency_key text;

CREATE UNIQUE INDEX IF NOT EXISTS transactions_idempotency_key_unique
    ON public.transactions (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE OR REPLACE FUNCTION public.record_transaction(
    p_customer_id uuid,
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
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Amount must be positive.'
            USING ERRCODE = '22023';
    END IF;

    IF p_transaction_type NOT IN ('credit', 'payment') THEN
        RAISE EXCEPTION 'Transaction type must be credit or payment.'
            USING ERRCODE = '22023';
    END IF;

    IF p_idempotency_key IS NULL OR btrim(p_idempotency_key) = '' THEN
        RAISE EXCEPTION 'Idempotency key is required.'
            USING ERRCODE = '22023';
    END IF;

    SELECT *
    INTO customer_row
    FROM public.customers
    WHERE id = p_customer_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Customer not found.'
            USING ERRCODE = 'P0002';
    END IF;

    SELECT *
    INTO existing_transaction
    FROM public.transactions
    WHERE idempotency_key = p_idempotency_key;

    IF FOUND THEN
        IF existing_transaction.customer_id <> p_customer_id
           OR existing_transaction.transaction_type <> p_transaction_type
           OR existing_transaction.amount <> p_amount
           OR existing_transaction.note IS DISTINCT FROM p_note THEN
            RAISE EXCEPTION 'Idempotency key was already used for a different transaction.'
                USING ERRCODE = '23505';
        END IF;

        SELECT COALESCE(
            SUM(CASE
                WHEN transaction_type = 'credit' THEN amount
                WHEN transaction_type = 'payment' THEN -amount
                ELSE 0
            END),
            0
        )
        INTO current_balance
        FROM public.transactions
        WHERE customer_id = p_customer_id;

        RETURN jsonb_build_object(
            'transaction', to_jsonb(existing_transaction),
            'outstanding_balance', current_balance,
            'idempotent_replay', true
        );
    END IF;

    SELECT COALESCE(
        SUM(CASE
            WHEN transaction_type = 'credit' THEN amount
            WHEN transaction_type = 'payment' THEN -amount
            ELSE 0
        END),
        0
    )
    INTO current_balance
    FROM public.transactions
    WHERE customer_id = p_customer_id;

    IF p_transaction_type = 'payment' AND p_amount > current_balance THEN
        RAISE EXCEPTION 'Payment exceeds outstanding balance. Current balance is ₹% .',
            to_char(current_balance, 'FM999999999990.00')
            USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.transactions (
        customer_id,
        transaction_type,
        amount,
        note,
        idempotency_key
    )
    VALUES (
        p_customer_id,
        p_transaction_type,
        p_amount,
        p_note,
        p_idempotency_key
    )
    RETURNING *
    INTO inserted_transaction;

    current_balance := current_balance
        + CASE
            WHEN p_transaction_type = 'credit' THEN p_amount
            ELSE -p_amount
          END;

    RETURN jsonb_build_object(
        'transaction', to_jsonb(inserted_transaction),
        'outstanding_balance', current_balance,
        'idempotent_replay', false
    );
END;
$$;

REVOKE ALL ON FUNCTION public.record_transaction(uuid, text, numeric, text, text)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.record_transaction(uuid, text, numeric, text, text)
    TO service_role;
