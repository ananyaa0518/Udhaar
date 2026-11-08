
from fastapi import HTTPException

from database.supabase_client import supabase


def get_customer_balance(customer_id: str) -> dict:
    """Get the current calculated balance for a customer."""

    result = (
        supabase
        .table("customer_balances")
        .select("*")
        .eq("customer_id", customer_id)
        .maybe_single()
        .execute()
    )

    if not result or not result.data:
        raise HTTPException(
            status_code=404,
            detail="Customer not found."
        )

    return result.data


def add_transaction(
    customer_id: str,
    transaction_type: str,
    amount: float,
    note: str = None,
) -> dict:
    """Insert a credit or payment transaction."""

    # Confirm that the customer exists.
    get_customer_balance(customer_id)

    if transaction_type == "payment":
        balance_data = get_customer_balance(customer_id)

        current_balance = float(
            balance_data["outstanding_balance"]
        )

        if amount > current_balance:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Payment exceeds outstanding balance. "
                    f"Current balance is ₹{current_balance:.2f}."
                )
            )

    result = (
        supabase
        .table("transactions")
        .insert({
            "customer_id": customer_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "note": note,
        })
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="Transaction could not be saved."
        )

    return result.data[0]


def get_customer_transactions(customer_id: str) -> list:
    """Get all transactions for a customer."""

    get_customer_balance(customer_id)

    result = (
        supabase
        .table("transactions")
        .select("*")
        .eq("customer_id", customer_id)
        .order("created_at", desc=True)
        .execute()
    )

    return result.data or []
