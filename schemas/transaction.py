
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    customer_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    note: Optional[str] = Field(default=None, max_length=500)


class TransactionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    transaction_type: str
    amount: Decimal
    note: Optional[str] = None
