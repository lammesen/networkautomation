"""Customer IP Range schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CustomerIPRangeBase(BaseModel):
    """Base customer IP range schema."""

    cidr: str = Field(..., description="CIDR network (e.g., 10.0.0.0/24)")
    description: Optional[str] = None


class CustomerIPRangeCreate(CustomerIPRangeBase):
    """Customer IP range creation schema."""
    pass


class CustomerIPRangeResponse(CustomerIPRangeBase):
    """Customer IP range response schema."""

    id: int
    customer_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
