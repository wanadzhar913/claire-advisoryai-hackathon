"""This file contains the banking transaction model for the application."""

from datetime import date, datetime
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

from sqlalchemy import Column, Numeric
from sqlmodel import (
    Field,
    Relationship,
)
from sqlalchemy.dialects.postgresql import JSONB

from backend.models.base import BaseModel

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.user_upload import UserUpload


class BankingTransaction(BaseModel, table=True):
    """Banking transaction model for storing structured transaction data.

    Attributes:
        id: The primary key (transaction identifier)
        user_id: Foreign key to the user
        file_id: Foreign key to the user upload file
        transaction_date: Date of the transaction
        transaction_year: Year of the transaction
        transaction_month: Month of the transaction (1-12)
        transaction_day: Day of the transaction (1-31)
        description: Description of the transaction
        merchant_name: Name of the merchant (optional)
        amount: Transaction amount
        transaction_type: Type of transaction (debit or credit)
        balance: Account balance after transaction (optional)
        reference_number: Reference number for the transaction (optional)
        transaction_code: Transaction code (optional)
        category: Transaction category (optional)
        currency: Currency code (defaults to MYR)
        subscription_status: AI classification status (predicted, confirmed, rejected, needs_review)
        subscription_confidence: AI confidence score (0.0 to 1.0)
        subscription_merchant_key: Normalized merchant key for grouping
        subscription_name: Display name for the subscription
        subscription_reason_codes: Array of reason codes from AI classification
        subscription_updated_at: When subscription classification was last updated
        created_at: When the transaction was created
        user: Relationship to the user
        user_upload: Relationship to the source upload
    """
    __tablename__ = "statement_banking_transaction"

    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="app_users.id")
    file_id: str = Field(foreign_key="user_upload.file_id")
    transaction_date: date
    transaction_year: int
    transaction_month: int = Field(ge=1, le=12)
    transaction_day: int = Field(ge=1, le=31)
    description: str
    merchant_name: Optional[str] = None
    amount: Decimal = Field(sa_column=Column(Numeric(15, 2)))
    is_subscription: bool = Field(default=False)
    transaction_type: str  # Values: 'debit' or 'credit'
    balance: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(15, 2)))
    reference_number: Optional[str] = None
    transaction_code: Optional[str] = None
    category: Optional[str] = None
    currency: str = Field(default="MYR")
    # Subscription classification metadata (populated by AI agent)
    subscription_status: Optional[str] = None  # 'predicted', 'confirmed', 'rejected', 'needs_review'
    subscription_confidence: Optional[float] = None  # 0.0 to 1.0
    subscription_merchant_key: Optional[str] = None  # Normalized grouping key
    subscription_name: Optional[str] = None  # Display name
    subscription_reason_codes: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    subscription_updated_at: Optional[datetime] = None
    user: "User" = Relationship()
    user_upload: "UserUpload" = Relationship(back_populates="banking_transactions")


# Avoid circular imports
from backend.models.user import User  # noqa: E402
from backend.models.user_upload import UserUpload  # noqa: E402
