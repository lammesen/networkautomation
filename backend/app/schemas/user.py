from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Role = Literal["viewer", "operator", "admin"]


class UserCreate(BaseModel):
    username: str
    password: str
    role: Role = "viewer"


class UserRead(BaseModel):
    id: int
    username: str
    role: Role
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
