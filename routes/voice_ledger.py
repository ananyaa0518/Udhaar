from fastapi import APIRouter, Depends, HTTPException
from database.supabase_client import supabase
from schemas.voice_ledger import VoiceLedgerRequest
from services.ledger_service import (
    add_transaction,
)
from services.customer_matching import find_customer_matches
from services.auth import get_current_user

router = APIRouter(
    prefix="/ledger",
    tags=["Voice Ledger"]
)


@router.post("/from-voice")
def ledger_from_voice(
    request: VoiceLedgerRequest,
    current_user: dict = Depends(get_current_user),
):

    # 1. Validate and normalize customer name.
    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Customer name cannot be empty."
        )

    try:
        # 2. Use an explicitly selected customer when supplied.
        if request.customer_id:
            selected = (
                supabase.table("customers")
                .select("id, name, phone, preferred_language")
                .eq("id", str(request.customer_id))
                .eq("merchant_id", current_user["id"])
                .maybe_single()
                .execute()
            )
            if not selected.data:
                raise HTTPException(status_code=404, detail="Customer not found.")
            customer_id = str(request.customer_id)
            name = selected.data["name"]
            customer_created = False
        else:
            # Legacy callers may omit customer_id. Never guess among duplicates.
            matches = find_customer_matches(
                name=name, phone=request.phone, merchant_id=current_user["id"]
            )
            if len(matches) > 1:
                raise HTTPException(
                    status_code=409,
                    detail="Multiple customers match. Select a customer before saving.",
                )
            if matches:
                customer_id = matches[0]["id"]
                name = matches[0]["name"]
                customer_created = False
            else:
                # 3. Create customer only when the explicit search found no match.
                customer_data = {
                    "name": name,
                    "preferred_language": request.preferred_language,
                    "merchant_id": current_user["id"],
                }
                if request.phone:
                    customer_data["phone"] = request.phone

                created = (
                    supabase.table("customers")
                    .insert(customer_data)
                    .execute()
                )

                if not created.data:
                    raise HTTPException(
                        status_code=500,
                        detail="Could not create customer."
                    )

                customer_id = created.data[0]["id"]
                customer_created = True

        # 3. Save credit/payment through the atomic RPC.
        result = add_transaction(
            customer_id=customer_id,
            transaction_type=request.transaction_type,
            amount=request.amount,
            note=request.description,
            idempotency_key=request.idempotency_key,
            merchant_id=current_user["id"],
            access_token=current_user["_access_token"],
        )

        return {
            "success": True,
            "message": "Voice transaction saved successfully.",
            "customer_id": customer_id,
            "customer_name": name,
            "customer_created": customer_created,
            **result,
            "transaction_type": request.transaction_type,
            "amount": request.amount,
            "preferred_language": request.preferred_language,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Voice ledger error: {str(error)}"
        )