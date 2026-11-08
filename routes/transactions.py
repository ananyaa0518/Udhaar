
from fastapi import APIRouter, Depends, HTTPException

from schemas.transaction import TransactionCreate
from services.ledger_service import (
    add_transaction,
    get_customer_balance,
    get_customer_transactions,
)
from services.auth import get_current_user
from schemas.transaction_edit import TransactionEdit
from database.supabase_client import supabase, user_supabase

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


@router.post("/credit")
def add_credit(request: TransactionCreate, current_user: dict = Depends(get_current_user)):
    """Add udhaar to a customer's account."""

    try:
        result = add_transaction(
            customer_id=str(request.customer_id),
            transaction_type="credit",
            amount=float(request.amount),
            note=request.note,
            idempotency_key=request.idempotency_key,
            merchant_id=current_user["id"],
            access_token=current_user["_access_token"],
        )

        return {
            "success": True,
            "message": "Credit added successfully.",
            **result,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/payment")
def add_payment(request: TransactionCreate, current_user: dict = Depends(get_current_user)):
    """Record a full or partial customer payment."""

    try:
        result = add_transaction(
            customer_id=str(request.customer_id),
            transaction_type="payment",
            amount=float(request.amount),
            note=request.note,
            idempotency_key=request.idempotency_key,
            merchant_id=current_user["id"],
            access_token=current_user["_access_token"],
        )

        return {
            "success": True,
            "message": "Payment recorded successfully.",
            **result,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("/{customer_id}/history")
def transaction_history(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Get a customer's complete transaction history."""

    try:
        transactions = get_customer_transactions(
            customer_id, current_user["id"]
        )

        return {
            "success": True,
            "count": len(transactions),
            "transactions": transactions,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = (
            supabase.table("transactions")
            .select("*")
            .eq("id", transaction_id)
            .eq("merchant_id", current_user["id"])
            .maybe_single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found.")
        return {"success": True, "transaction": result.data}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.put("/{transaction_id}")
def edit_transaction(
    transaction_id: str,
    request: TransactionEdit,
    current_user: dict = Depends(get_current_user),
):
    try:
        result = (
            user_supabase(current_user["_access_token"]).rpc(
                "update_transaction",
                {
                    "p_transaction_id": transaction_id,
                    "p_merchant_id": current_user["id"],
                    "p_amount": float(request.amount),
                    "p_transaction_type": request.transaction_type,
                    "p_note": request.note,
                },
            ).execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Transaction could not be updated.")
        return {"success": True, **result.data}
    except HTTPException:
        raise
    except Exception as error:
        detail = str(error)
        status = 400 if "negative" in detail or "positive" in detail else 500
        raise HTTPException(status_code=status, detail=detail)
