"""Banking transaction query endpoints."""
import asyncio
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

import pandas as pd

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.utils.sankey import to_sankey
from backend.services.db.postgres_connector import database_service
from backend.services.ai_agent.subscription_classifier import subscription_classifier
from backend.schemas.transaction_response import (
    BankingTransactionResponse,
    ClassificationSummaryResponse,
    SubscriptionAggregatedResponse,
    SubscriptionReviewRequest,
)

router = APIRouter()


@router.get("/transactions", response_model=List[BankingTransactionResponse])
async def query_transactions_all(
    current_user: User = Depends(get_current_user),
    file_id: Optional[str] = Query(default=None, description="Filter by file ID (user upload file ID)"),
    start_date: Optional[date] = Query(default=None, description="Filter transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter transactions up to this date (inclusive)"),
    merchant_name: Optional[str] = Query(default=None, description="Filter by merchant name (partial match, case-insensitive)"),
    transaction_type: Optional[str] = Query(default=None, pattern="^(debit|credit)$", description="Filter by transaction type ('debit' or 'credit')"),
    category: Optional[str] = Query(default=None, description="Filter by transaction category"),
    min_amount: Optional[Decimal] = Query(default=None, description="Minimum transaction amount (inclusive)"),
    max_amount: Optional[Decimal] = Query(default=None, description="Maximum transaction amount (inclusive)"),
    is_subscription: Optional[bool] = Query(default=None, description="Filter by subscription status (likely to recur monthly)"),
    transaction_year: Optional[int] = Query(default=None, description="Filter by transaction year"),
    transaction_month: Optional[int] = Query(default=None, ge=1, le=12, description="Filter by transaction month (1-12)"),
    currency: Optional[str] = Query(default=None, description="Filter by currency code (e.g., 'MYR')"),
    description: Optional[str] = Query(default=None, description="Filter by description (partial match, case-insensitive)"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
    order_by: str = Query(default="transaction_date", description="Field to order by (default: 'transaction_date')"),
    order_desc: bool = Query(default=True, description="If True, order descending; if False, order ascending"),
) -> List[BankingTransactionResponse]:
    """Query banking transactions with various filters.
    
    This endpoint allows filtering banking transactions by multiple criteria including:
    - File filters
    - Date ranges
    - Amount ranges
    - Transaction type, category, merchant name
    - Year/month filters
    - Currency and description search
    
    Args:
        current_user: Authenticated user (from Clerk JWT)
        file_id: Filter by file ID (user upload file ID)
        start_date: Filter transactions from this date onwards (inclusive)
        end_date: Filter transactions up to this date (inclusive)
        merchant_name: Filter by merchant name (partial match, case-insensitive)
        transaction_type: Filter by transaction type ('debit' or 'credit')
        category: Filter by transaction category
        min_amount: Minimum transaction amount (inclusive)
        max_amount: Maximum transaction amount (inclusive)
        transaction_year: Filter by transaction year
        transaction_month: Filter by transaction month (1-12)
        currency: Filter by currency code (e.g., 'MYR')
        description: Filter by description (partial match, case-insensitive)
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)
        order_by: Field to order by (default: 'transaction_date')
        order_desc: If True, order descending; if False, order ascending
        
    Returns:
    - `List[BankingTransactionResponse]`: List of matching banking transactions
        
    Raises:
    - `HTTPException`: If query fails
    """
    user_id = current_user.id
    try:
        transactions = database_service.filter_banking_transactions(
            user_id=user_id,
            file_id=file_id,
            start_date=start_date,
            end_date=end_date,
            merchant_name=merchant_name,
            transaction_type=transaction_type,
            category=category,
            min_amount=min_amount,
            max_amount=max_amount,
            is_subscription=is_subscription,
            transaction_year=transaction_year,
            transaction_month=transaction_month,
            currency=currency,
            description=description,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )
        
        # Convert to response models
        return [
            BankingTransactionResponse(
                id=tx.id,
                user_id=tx.user_id,
                file_id=tx.file_id,
                transaction_date=tx.transaction_date,
                transaction_year=tx.transaction_year,
                transaction_month=tx.transaction_month,
                transaction_day=tx.transaction_day,
                description=tx.description,
                merchant_name=tx.merchant_name,
                amount=tx.amount,
                transaction_type=tx.transaction_type,
                is_subscription=tx.is_subscription,
                balance=tx.balance,
                reference_number=tx.reference_number,
                transaction_code=tx.transaction_code,
                category=tx.category,
                currency=tx.currency,
                created_at=tx.created_at.isoformat() if tx.created_at else None,
            )
            for tx in transactions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query transactions: {str(e)}"
        )

@router.get("/transactions/sankey_diagram")
async def query_transactions_sankey_diagram(
    current_user: User = Depends(get_current_user),
    file_id: Optional[str] = Query(default=None, description="Filter by file ID (user upload file ID)"),
    start_date: Optional[date] = Query(default=None, description="Filter transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter transactions up to this date (inclusive)"),
    merchant_name: Optional[str] = Query(default=None, description="Filter by merchant name (partial match, case-insensitive)"),
    transaction_type: Optional[str] = Query(default=None, pattern="^(debit|credit)$", description="Filter by transaction type ('debit' or 'credit')"),
    category: Optional[str] = Query(default=None, description="Filter by transaction category"),
    min_amount: Optional[Decimal] = Query(default=None, description="Minimum transaction amount (inclusive)"),
    max_amount: Optional[Decimal] = Query(default=None, description="Maximum transaction amount (inclusive)"),
    is_subscription: Optional[bool] = Query(default=None, description="Filter by subscription status (likely to recur monthly)"),
    transaction_year: Optional[int] = Query(default=None, description="Filter by transaction year"),
    transaction_month: Optional[int] = Query(default=None, ge=1, le=12, description="Filter by transaction month (1-12)"),
    currency: Optional[str] = Query(default=None, description="Filter by currency code (e.g., 'MYR')"),
    description: Optional[str] = Query(default=None, description="Filter by description (partial match, case-insensitive)"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
    order_by: str = Query(default="transaction_date", description="Field to order by (default: 'transaction_date')"),
    order_desc: bool = Query(default=True, description="If True, order descending; if False, order ascending"),
):
    """Query banking transactions with various filters.
    
    This endpoint allows filtering banking transactions by multiple criteria including:
    - User and file filters
    - Date ranges
    - Amount ranges
    - Transaction type, category, merchant name
    - Year/month filters
    - Currency and description search
    
    Args:
        current_user: Authenticated user (from Clerk JWT)
        file_id: Filter by file ID (user upload file ID)
        start_date: Filter transactions from this date onwards (inclusive)
        end_date: Filter transactions up to this date (inclusive)
        merchant_name: Filter by merchant name (partial match, case-insensitive)
        transaction_type: Filter by transaction type ('debit' or 'credit')
        min_amount: Minimum transaction amount (inclusive)
        max_amount: Maximum transaction amount (inclusive)
        transaction_year: Filter by transaction year
        transaction_month: Filter by transaction month (1-12)
        currency: Filter by currency code (e.g., 'MYR')
        description: Filter by description (partial match, case-insensitive)
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)
        order_by: Field to order by (default: 'transaction_date')
        order_desc: If True, order descending; if False, order ascending
        
    Returns:
    - `List[Dict[str, Any]]`: List of matching banking transactions converted to a dictionary format for sankey diagram
        
    Raises:
    - `HTTPException`: If query fails
    """
    user_id = current_user.id
    try:
        transactions = database_service.filter_banking_transactions(
            user_id=user_id,
            file_id=file_id,
            start_date=start_date,
            end_date=end_date,
            merchant_name=merchant_name,
            transaction_type=transaction_type,
            category=category,
            min_amount=min_amount,
            max_amount=max_amount,
            is_subscription=is_subscription,
            transaction_year=transaction_year,
            transaction_month=transaction_month,
            currency=currency,
            description=description,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )

        # Convert SQLModel objects to dictionaries for sankey diagram
        transactions_dict = [
            {
                'amount': float(tx.amount) if tx.amount else 0.0,
                'transaction_type': tx.transaction_type,
                'merchant_name': tx.merchant_name,
                'category': tx.category,
            }
            for tx in transactions
        ]

        # Format to sankey diagram appropriate format
        return await asyncio.to_thread(to_sankey, transactions_dict)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query transactions: {str(e)}"
        )

@router.post("/transactions/subscriptions/classify", response_model=ClassificationSummaryResponse)
async def classify_subscriptions(
    current_user: User = Depends(get_current_user),
    start_date: date = Query(..., description="Start date for classification range (inclusive)"),
    end_date: date = Query(..., description="End date for classification range (inclusive)"),
) -> ClassificationSummaryResponse:
    """Classify transactions in a date range as subscriptions using AI.
    
    This endpoint triggers the AI-powered subscription classification pipeline.
    It analyzes debit transactions in the specified date range and classifies them
    as subscriptions or non-subscriptions.
    
    Args:
    - `current_user`: Authenticated user (from Clerk JWT)
    - `start_date`: Start date for classification range (inclusive, required)
    - `end_date`: End date for classification range (inclusive, required)
        
    Returns:
    - `ClassificationSummaryResponse`: Summary of classification results including counts
        
    Raises:
    - `HTTPException`: If classification fails or date range is invalid
    """
    user_id = current_user.id
    
    # Validate date range
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be >= start_date"
        )
    
    days_diff = (end_date - start_date).days
    if days_diff > 365:
        raise HTTPException(
            status_code=400,
            detail="Date range cannot exceed 365 days"
        )
    
    try:
        summary = subscription_classifier.classify_subscriptions_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        return ClassificationSummaryResponse(
            total_processed=summary.total_processed,
            predicted_count=summary.predicted_count,
            rejected_count=summary.rejected_count,
            needs_review_count=summary.needs_review_count,
            failed_batches=summary.failed_batches,
            start_date=summary.start_date,
            end_date=summary.end_date,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to classify subscriptions: {str(e)}"
        )


@router.post("/transactions/subscriptions/review", response_model=BankingTransactionResponse)
async def review_subscription_transaction(
    payload: SubscriptionReviewRequest,
    current_user: User = Depends(get_current_user),
) -> BankingTransactionResponse:
    """User review endpoint for resolving subscription classifications.

    This endpoint is intended to resolve transactions marked as 'needs_review' by allowing
    the user to confirm it is a subscription or reject it as not a subscription.
    """
    user_id = current_user.id

    try:
        tx = database_service.review_subscription_transaction(
            user_id=user_id,
            transaction_id=payload.transaction_id,
            decision=payload.decision,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Transaction not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg == "Transaction subscription status is already finalized":
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review subscription: {str(e)}")

    return BankingTransactionResponse(
        id=tx.id,
        user_id=tx.user_id,
        file_id=tx.file_id,
        transaction_date=tx.transaction_date,
        transaction_year=tx.transaction_year,
        transaction_month=tx.transaction_month,
        transaction_day=tx.transaction_day,
        description=tx.description,
        merchant_name=tx.merchant_name,
        is_subscription=tx.is_subscription,
        amount=tx.amount,
        transaction_type=tx.transaction_type,
        balance=tx.balance,
        reference_number=tx.reference_number,
        transaction_code=tx.transaction_code,
        category=tx.category,
        currency=tx.currency,
        subscription_status=tx.subscription_status,
        subscription_confidence=tx.subscription_confidence,
        subscription_merchant_key=tx.subscription_merchant_key,
        subscription_name=tx.subscription_name,
        subscription_reason_codes=tx.subscription_reason_codes,
        subscription_updated_at=tx.subscription_updated_at,
        created_at=tx.created_at.isoformat() if tx.created_at else None,
    )


@router.get("/transactions/subscriptions/needs-review", response_model=List[BankingTransactionResponse])
async def query_subscriptions_needs_review(
    current_user: User = Depends(get_current_user),
    start_date: Optional[date] = Query(default=None, description="Filter transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter transactions up to this date (inclusive)"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
) -> List[BankingTransactionResponse]:
    """Query debit transactions that need manual subscription review."""
    user_id = current_user.id

    # Validate date range - if one is provided, both must be provided
    if (start_date is None) != (end_date is None):
        raise HTTPException(
            status_code=400,
            detail="Both start_date and end_date must be provided together, or neither",
        )
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")

    try:
        transactions = database_service.get_subscription_needs_review(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        return [
            BankingTransactionResponse(
                id=tx.id,
                user_id=tx.user_id,
                file_id=tx.file_id,
                transaction_date=tx.transaction_date,
                transaction_year=tx.transaction_year,
                transaction_month=tx.transaction_month,
                transaction_day=tx.transaction_day,
                description=tx.description,
                merchant_name=tx.merchant_name,
                is_subscription=tx.is_subscription,
                amount=tx.amount,
                transaction_type=tx.transaction_type,
                balance=tx.balance,
                reference_number=tx.reference_number,
                transaction_code=tx.transaction_code,
                category=tx.category,
                currency=tx.currency,
                subscription_status=tx.subscription_status,
                subscription_confidence=tx.subscription_confidence,
                subscription_merchant_key=tx.subscription_merchant_key,
                subscription_name=tx.subscription_name,
                subscription_reason_codes=tx.subscription_reason_codes,
                subscription_updated_at=tx.subscription_updated_at,
                created_at=tx.created_at.isoformat() if tx.created_at else None,
            )
            for tx in transactions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query needs-review subscriptions: {str(e)}",
        )


@router.get("/transactions/subscriptions", response_model=List[BankingTransactionResponse])
async def query_subscriptions_all(
    current_user: User = Depends(get_current_user),
    start_date: Optional[date] = Query(default=None, description="Filter transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter transactions up to this date (inclusive)"),
    transaction_year: Optional[int] = Query(default=None, description="Filter by transaction year"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
    order_by: str = Query(default="transaction_date", description="Field to order by (default: 'transaction_date')"),
    order_desc: bool = Query(default=True, description="If True, order descending; if False, order ascending"),
) -> List[BankingTransactionResponse]:
    """Query all banking transactions classified as subscriptions.
    
    This endpoint returns transactions where is_subscription == True and transaction_type == 'debit'.
    Supports optional date range filtering.
    
    Args:
    - `current_user`: Authenticated user (from Clerk JWT)
    - `start_date`: Filter transactions from this date onwards (inclusive)
    - `end_date`: Filter transactions up to this date (inclusive)
    - `transaction_year`: Filter by transaction year
    - `limit`: Maximum number of results to return
    - `offset`: Number of results to skip (for pagination)
    - `order_by`: Field to order by (default: 'transaction_date')
    - `order_desc`: If True, order descending; if False, order ascending
        
    Returns:
    - `List[BankingTransactionResponse]`: List of matching subscription transactions
        
    Raises:
    - `HTTPException`: If query fails or date range is invalid
    """
    user_id = current_user.id
    
    # Validate date range - if one is provided, both must be provided
    if (start_date is None) != (end_date is None):
        raise HTTPException(
            status_code=400,
            detail="Both start_date and end_date must be provided together, or neither"
        )
    
    if start_date and end_date and end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be >= start_date"
        )
    
    try:
        transactions = database_service.filter_banking_transactions(
            user_id=user_id,
            transaction_type='debit',  # Only debit transactions are considered as subscriptions
            is_subscription=True,
            start_date=start_date,
            end_date=end_date,
            transaction_year=transaction_year,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )
        
        # Convert to response models with subscription metadata
        return [
            BankingTransactionResponse(
                id=tx.id,
                user_id=tx.user_id,
                file_id=tx.file_id,
                transaction_date=tx.transaction_date,
                transaction_year=tx.transaction_year,
                transaction_month=tx.transaction_month,
                transaction_day=tx.transaction_day,
                description=tx.description,
                merchant_name=tx.merchant_name,
                is_subscription=tx.is_subscription,
                amount=tx.amount,
                transaction_type=tx.transaction_type,
                balance=tx.balance,
                reference_number=tx.reference_number,
                transaction_code=tx.transaction_code,
                category=tx.category,
                currency=tx.currency,
                subscription_status=tx.subscription_status,
                subscription_confidence=tx.subscription_confidence,
                subscription_merchant_key=tx.subscription_merchant_key,
                subscription_name=tx.subscription_name,
                subscription_reason_codes=tx.subscription_reason_codes,
                subscription_updated_at=tx.subscription_updated_at,
                created_at=tx.created_at.isoformat() if tx.created_at else None,
            )
            for tx in transactions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query subscription transactions: {str(e)}"
        )

@router.get("/transactions/subscriptions/aggregated", response_model=List[SubscriptionAggregatedResponse])
async def query_subscriptions_aggregated(
    current_user: User = Depends(get_current_user),
    start_date: Optional[date] = Query(default=None, description="Filter transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter transactions up to this date (inclusive)"),
    transaction_year: Optional[int] = Query(default=None, description="Filter by transaction year"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
    order_by: str = Query(default="transaction_date", description="Field to order by (default: 'transaction_date')"),
    order_desc: bool = Query(default=True, description="If True, order descending; if False, order ascending"),
) -> List[SubscriptionAggregatedResponse]:
    """Query subscription transactions aggregated by merchant.
    
    This endpoint returns subscription transactions grouped by subscription_merchant_key
    (falling back to merchant_name if not available). Supports optional date range filtering.
    
    Args:
    - `current_user`: Authenticated user (from Clerk JWT)
    - `start_date`: Filter transactions from this date onwards (inclusive)
    - `end_date`: Filter transactions up to this date (inclusive)
    - `transaction_year`: Filter by transaction year
    - `limit`: Maximum number of results to return
    - `offset`: Number of results to skip (for pagination)
    - `order_by`: Field to order by (default: 'transaction_date')
    - `order_desc`: If True, order descending; if False, order ascending
        
    Returns:
    - `List[SubscriptionAggregatedResponse]`: Aggregated subscription data by merchant
        
    Raises:
    - `HTTPException`: If query fails or date range is invalid
    """
    user_id = current_user.id
    
    # Validate date range - if one is provided, both must be provided
    if (start_date is None) != (end_date is None):
        raise HTTPException(
            status_code=400,
            detail="Both start_date and end_date must be provided together, or neither"
        )
    
    if start_date and end_date and end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be >= start_date"
        )
    
    try:
        transactions = database_service.filter_banking_transactions(
            user_id=user_id,
            is_subscription=True,
            transaction_type='debit',  # Only debit transactions are considered as subscriptions
            start_date=start_date,
            end_date=end_date,
            transaction_year=transaction_year,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )

        if not transactions:
            return []

        # Convert SQLModel objects to dictionaries for pandas DataFrame
        # Use subscription_merchant_key if available, otherwise fall back to merchant_name
        transactions_dict = [
            {
                'merchant_key': tx.subscription_merchant_key or tx.merchant_name or 'Unknown',
                'display_name': tx.subscription_name or tx.merchant_name or 'Unknown',
                'category': tx.category,
                'amount': float(tx.amount) if tx.amount else 0.0,
                'transaction_month': tx.transaction_month,
                'confidence': tx.subscription_confidence,
            }
            for tx in transactions
        ]
        
        transactions_df = pd.DataFrame(transactions_dict)
        
        # Group by merchant_key and category
        aggregated_df = transactions_df.groupby(['merchant_key', 'category']).agg({
            'display_name': 'first',  # Take first display name
            'amount': 'sum',
            'transaction_month': 'nunique',
            'confidence': 'mean',
            'merchant_key': 'count',  # Count for transaction_count
        }).rename(columns={'merchant_key': 'transaction_count'}).reset_index()

        aggregated_df['average_monthly_amount'] = aggregated_df['amount'] / aggregated_df['transaction_month']
        aggregated_df.rename(columns={
            'transaction_month': 'no_months_subscribed',
            'amount': 'total_amount',
            'confidence': 'confidence_avg',
        }, inplace=True)

        # Convert to response models
        return [
            SubscriptionAggregatedResponse(
                merchant_key=row['merchant_key'],
                display_name=row['display_name'],
                category=row['category'],
                total_amount=Decimal(str(row['total_amount'])),
                no_months_subscribed=int(row['no_months_subscribed']),
                average_monthly_amount=Decimal(str(row['average_monthly_amount'])),
                confidence_avg=row['confidence_avg'] if pd.notna(row['confidence_avg']) else None,
                transaction_count=int(row['transaction_count']),
            )
            for _, row in aggregated_df.iterrows()
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query subscription transactions: {str(e)}"
        )