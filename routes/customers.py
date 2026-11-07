
from fastapi import APIRouter, HTTPException

from database.supabase_client import supabase
from schemas.customer import CustomerCreate

router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


@router.post("/")
def create_customer(customer: CustomerCreate):
    """Create a new customer."""

    data = customer.model_dump()

    try:
        result = (
            supabase
            .table("customers")
            .insert(data)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Customer could not be created."
            )

        return {
            "success": True,
            "message": "Customer created successfully.",
            "customer": result.data[0]
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("/")
def get_customers():
    """Get all customers with their outstanding balances."""

    try:
        customers_result = (
            supabase
            .table("customer_balances")
            .select("*")
            .order("name")
            .execute()
        )

        return {
            "success": True,
            "count": len(customers_result.data),
            "customers": customers_result.data
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("/{customer_id}")
def get_customer(customer_id: str):
    """Get one customer's details."""

    try:
        result = (
            supabase
            .table("customers")
            .select("*")
            .eq("id", customer_id)
            .maybe_single()
            .execute()
        )

        if not result or not result.data:
            raise HTTPException(
                status_code=404,
                detail="Customer not found."
            )

        return {
            "success": True,
            "customer": result.data
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("/{customer_id}/balance")
def get_customer_balance(customer_id: str):
    """Get a customer's outstanding balance."""

    try:
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

        return {
            "success": True,
            "customer_id": customer_id,
            "name": result.data["name"],
            "outstanding_balance": result.data[
                "outstanding_balance"
            ]
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
