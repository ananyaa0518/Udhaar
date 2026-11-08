from fastapi import APIRouter, HTTPException
from database.supabase_client import supabase
from schemas.voice_ledger import VoiceLedgerRequest
from services.ledger_service import (
    add_transaction,
    get_customer_balance,
)

router = APIRouter(
    prefix="/ledger",
    tags=["Voice Ledger"]
)


@router.post("/from-voice")
def ledger_from_voice(request: VoiceLedgerRequest):

    # 1. Validate and normalize customer name.
    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Customer name cannot be empty."
        )

    try:
        # 2. Find an existing customer.
        existing = (
            supabase.table("customers")
            .select("id, name")
            .eq("name", name)
            .limit(1)
            .execute()
        )

        if existing.data:
            customer_id = existing.data[0]["id"]
            customer_created = False

        else:
            # 3. Create customer if not found.
            created = (
                supabase.table("customers")
                .insert({
                    "name": name,
                    "preferred_language": request.preferred_language,
                })
                .execute()
            )

            if not created.data:
                raise HTTPException(
                    status_code=500,
                    detail="Could not create customer."
                )

            customer_id = created.data[0]["id"]
            customer_created = True

        # 4. Save credit/payment using existing validation.
        transaction = add_transaction(
            customer_id=customer_id,
            transaction_type=request.transaction_type,
            amount=request.amount,
            note=request.description,
        )

        # 5. Fetch updated balance.
        balance_data = get_customer_balance(customer_id)

        balance = float(
            balance_data["outstanding_balance"]
        )

        return {
            "success": True,
            "message": "Voice transaction saved successfully.",
            "customer_id": customer_id,
            "customer_name": name,
            "customer_created": customer_created,
            "transaction": transaction,
            "transaction_type": request.transaction_type,
            "amount": request.amount,
            "outstanding_balance": balance,
            "preferred_language": request.preferred_language,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Voice ledger error: {str(error)}"
        )