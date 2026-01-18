from datetime import date
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel


class BankingTransactionResponse(BaseModel):
    """Banking transaction response model."""
    id: str
    user_id: int
    file_id: str
    transaction_date: date
    transaction_year: int
    transaction_month: int
    transaction_day: int
    description: str
    merchant_name: Optional[str] = None
    amount: Decimal
    transaction_type: str
    is_subscription: bool
    balance: Optional[Decimal] = None
    reference_number: Optional[str] = None
    transaction_code: Optional[str] = None
    category: Optional[str] = None
    currency: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
