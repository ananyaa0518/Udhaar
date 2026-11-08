import re
from typing import Optional

from database.supabase_client import supabase


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Keep digits only and normalize common international formatting."""

    if not phone:
        return None

    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits or None


def find_customer_matches(
    name: Optional[str] = None,
    phone: Optional[str] = None,
    merchant_id: Optional[str] = None,
) -> list[dict]:
    """Find phone matches first, otherwise exact case-insensitive name matches."""

    requested_phone = normalize_phone(phone)
    requested_name = (name or "").strip().casefold()
    result = (
        supabase
        .table("customers")
        .select("id, name, phone, preferred_language")
        .execute()
    )
    customers = result.data or []
    if merchant_id:
        customers = [
            customer for customer in customers
            if str(customer.get("merchant_id")) == str(merchant_id)
        ]

    if requested_phone:
        return [
            customer for customer in customers
            if normalize_phone(customer.get("phone")) == requested_phone
        ]

    if not requested_name:
        return []

    return [
        customer for customer in customers
        if (customer.get("name") or "").strip().casefold() == requested_name
    ]
