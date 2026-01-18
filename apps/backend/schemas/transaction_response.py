from datetime import date, datetime
from typing import List, Optional, Literal
from decimal import Decimal

from pydantic import BaseModel, Field


class SubscriptionReviewRequest(BaseModel):
    """Request model for user review of a subscription classification."""
    transaction_id: str = Field(..., description="Transaction ID to review")
    decision: Literal["confirmed", "rejected"] = Field(
        ...,
        description="User decision: 'confirmed' (is a subscription) or 'rejected' (not a subscription)",
    )


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
    # Subscription classification metadata
    subscription_status: Optional[str] = None
    subscription_confidence: Optional[float] = None
    subscription_merchant_key: Optional[str] = None
    subscription_name: Optional[str] = None
    subscription_reason_codes: Optional[List[str]] = None
    subscription_updated_at: Optional[datetime] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionAggregatedResponse(BaseModel):
    """Aggregated subscription response model for grouped subscription data."""
    merchant_key: str = Field(..., description="Normalized merchant key for grouping")
    display_name: str = Field(..., description="Display name for the subscription")
    category: Optional[str] = Field(None, description="Transaction category")
    total_amount: Decimal = Field(..., description="Total amount spent on this subscription")
    no_months_subscribed: int = Field(..., description="Number of distinct months with this subscription")
    average_monthly_amount: Decimal = Field(..., description="Average monthly amount")
    confidence_avg: Optional[float] = Field(None, description="Average confidence score from AI classification")
    transaction_count: int = Field(..., description="Total number of transactions")

    class Config:
        from_attributes = True


class ClassificationSummaryResponse(BaseModel):
    """Response model for subscription classification results."""
    total_processed: int = Field(..., description="Total number of transactions processed")
    predicted_count: int = Field(..., description="Number of transactions predicted as subscriptions")
    rejected_count: int = Field(..., description="Number of transactions rejected as non-subscriptions")
    needs_review_count: int = Field(..., description="Number of transactions needing manual review")
    failed_batches: List[dict] = Field(default_factory=list, description="List of failed batches with reasons")
    start_date: date = Field(..., description="Start date of the classification range")
    end_date: date = Field(..., description="End date of the classification range")

    class Config:
        from_attributes = True
