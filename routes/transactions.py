
from fastapi import APIRouter, HTTPException

from schemas.transaction import TransactionCreate
from services.ledger_service import (
    add_transaction,
    get_customer_balance,
    get_customer_transactions,
)

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


@router.post("/credit")
def add_credit(request: TransactionCreate):
    """Add udhaar to a customer's account."""

    try:
        transaction = add_transaction(
            customer_id=str(request.customer_id),
            transaction_type="credit",
            amount=float(request.amount),
            note=request.note,
        )

        balance = get_customer_balance(
            str(request.customer_id)
        )

        return {
            "success": True,
            "message": "Credit added successfully.",
            "transaction": transaction,
            "outstanding_balance": balance[
                "outstanding_balance"
            ],
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/payment")
def add_payment(request: TransactionCreate):
    """Record a full or partial customer payment."""

    try:
        transaction = add_transaction(
            customer_id=str(request.customer_id),
            transaction_type="payment",
            amount=float(request.amount),
            note=request.note,
        )

        balance = get_customer_balance(
            str(request.customer_id)
        )

        return {
            "success": True,
            "message": "Payment recorded successfully.",
            "transaction": transaction,
            "outstanding_balance": balance[
                "outstanding_balance"
            ],
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("/{customer_id}/history")
def transaction_history(customer_id: str):
    """Get a customer's complete transaction history."""

    try:
        transactions = get_customer_transactions(
            customer_id
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
