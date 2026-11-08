
from fastapi import HTTPException
from uuid import uuid4

from database.supabase_client import supabase, user_supabase


def get_customer_balance(customer_id: str, merchant_id: str = None) -> dict:
    """Get the current calculated balance for a customer."""

    result = (
        supabase
        .table("customer_balances")
        .select("*")
        .eq("customer_id", customer_id)
        .maybe_single()
        .execute()
    )
    data = result.data
    if merchant_id and data and str(data.get("merchant_id")) != str(merchant_id):
        data = None

    if not result or not data:
        raise HTTPException(
            status_code=404,
            detail="Customer not found."
        )

    return data


def add_transaction(
    customer_id: str,
    transaction_type: str,
    amount: float,
    note: str = None,
    idempotency_key: str = None,
    merchant_id: str = None,
    access_token: str = None,
) -> dict:
    """Atomically validate and record a credit or payment transaction."""

    try:
        rpc_client = user_supabase(access_token) if access_token else supabase
        rpc_name = "record_transaction"
        rpc_args = {
            "p_customer_id": customer_id,
            "p_merchant_id": merchant_id,
            "p_transaction_type": transaction_type,
            "p_amount": amount,
            "p_note": note,
            "p_idempotency_key": idempotency_key or str(uuid4()),
        }
        result = rpc_client.rpc(
            rpc_name,
            rpc_args,
        ).execute()
    except Exception as error:
        message = str(error)
        if "Customer not found" in message:
            raise HTTPException(status_code=404, detail="Customer not found.")
        if "Authenticated merchant is required" in message:
            raise HTTPException(status_code=401, detail=message)
        if "Payment exceeds outstanding balance" in message:
            raise HTTPException(status_code=400, detail=message)
        if (
            "Idempotency key was already used" in message
            or "transactions_idempotency_key_unique" in message
        ):
            raise HTTPException(status_code=409, detail=message)
        if "Amount must be positive" in message or "Transaction type must" in message:
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail=message)

    if not result.data:
        raise HTTPException(status_code=500, detail="Transaction could not be saved.")

    return result.data


def get_customer_transactions(customer_id: str, merchant_id: str = None) -> list:
    """Get all transactions for a customer."""

    get_customer_balance(customer_id, merchant_id)

    result = (
        supabase
        .table("transactions")
        .select("*")
        .eq("customer_id", customer_id)
        .order("created_at", desc=True)
        .execute()
    )

    transactions = result.data or []
    if merchant_id:
        transactions = [
            item for item in transactions
            if str(item.get("merchant_id")) == str(merchant_id)
        ]
    return transactions
