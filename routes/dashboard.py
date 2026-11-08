from fastapi import APIRouter, Depends, HTTPException

from database.supabase_client import supabase
from services.auth import get_current_user


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary(current_user: dict = Depends(get_current_user)):
    """Return merchant-scoped summary data from the ledger."""

    merchant_id = current_user["id"]
    try:
        customers = (
            supabase.table("customer_balances")
            .select("customer_id, outstanding_balance")
            .eq("merchant_id", merchant_id)
            .execute()
        ).data or []
        transactions = (
            supabase.table("transactions")
            .select("transaction_type, amount")
            .eq("merchant_id", merchant_id)
            .execute()
        ).data or []
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

    outstanding = sum(float(row["outstanding_balance"] or 0) for row in customers)
    payments = sum(
        float(row["amount"] or 0)
        for row in transactions
        if row["transaction_type"] == "payment"
    )
    return {
        "success": True,
        "total_outstanding_credit": outstanding,
        "total_payments_received": payments,
        "total_customers": len(customers),
        "customers_with_pending_dues": sum(
            1 for row in customers if float(row["outstanding_balance"] or 0) > 0
        ),
    }
