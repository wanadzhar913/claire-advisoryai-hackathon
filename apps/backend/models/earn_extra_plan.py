"""Earn extra plan model for tracking user micro-plans."""

import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from backend.models.base import BaseModel


class EarnExtraPlan(BaseModel, table=True):
    """Earn extra plan model for storing generated and active micro-plans."""

    __tablename__ = "earn_extra_plan"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(foreign_key="app_users.id", index=True)
    file_id: Optional[str] = Field(default=None, foreign_key="user_upload.file_id")

    status: str = Field(default="generated")  # generated | active | completed | archived

    target_amount: Decimal = Field(default=Decimal("500.00"), sa_column=Column(Numeric(15, 2)))
    currency: str = Field(default="MYR")
    timeframe_days: int = Field(default=30)

    title: str
    summary: str
    actions: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSONB))
    expected_amount: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(15, 2)))
    confidence: Optional[str] = None  # low | med | high

    saved_so_far: Decimal = Field(default=Decimal("0.00"), sa_column=Column(Numeric(15, 2)))
    actions_progress: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSONB))

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
