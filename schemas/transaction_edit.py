from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TransactionEdit(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    transaction_type: Literal["credit", "payment"]
    note: Optional[str] = Field(default=None, max_length=500)
