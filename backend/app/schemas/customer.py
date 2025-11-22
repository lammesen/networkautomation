"""Customer schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CustomerBase(BaseModel):
    """Base customer schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Customer creation schema."""
    pass


class CustomerUpdate(BaseModel):
    """Customer update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class CustomerResponse(CustomerBase):
    """Customer response schema."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
