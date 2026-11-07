
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    preferred_language: Literal[
        "bn-IN",
        "en-IN",
        "gu-IN",
        "hi-IN",
        "kn-IN",
        "ml-IN",
        "mr-IN",
        "pa-IN",
        "ta-IN",
        "te-IN",
    ] = "hi-IN"


class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    preferred_language: str
