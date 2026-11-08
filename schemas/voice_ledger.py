from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class VoiceLedgerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    customer_id: Optional[UUID] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    amount: float = Field(gt=0)
    transaction_type: Literal["credit", "payment"]
    preferred_language: Literal[
        "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN",
        "ml-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN"
    ] = "hi-IN"
    description: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=200)