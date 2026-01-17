"""Banking transaction query endpoints."""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.schemas.transaction_category import FinancialTransactionCategory
from backend.services.db.postgres_connector import database_service

router = APIRouter()


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
    balance: Optional[Decimal] = None
    reference_number: Optional[str] = None
    transaction_code: Optional[str] = None
    category: Optional[str] = None
    currency: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/transactions", tags=["Transactions"], response_model=List[BankingTransactionResponse])
async def query_transactions(
    current_user: User = Depends(get_current_user),
    file_id: Optional[str] = Query(default=None, description="Filter by file ID (user upload file ID)"),
    start_date: Optional[date] = Query(default=None, description="Filter transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter transactions up to this date (inclusive)"),
    merchant_name: Optional[str] = Query(default=None, description="Filter by merchant name (partial match, case-insensitive)"),
    transaction_type: Optional[str] = Query(default=None, regex="^(debit|credit)$", description="Filter by transaction type ('debit' or 'credit')"),
    category: Optional[str] = Query(default=None, description="Filter by transaction category"),
    min_amount: Optional[Decimal] = Query(default=None, description="Minimum transaction amount (inclusive)"),
    max_amount: Optional[Decimal] = Query(default=None, description="Maximum transaction amount (inclusive)"),
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
        List[BankingTransactionResponse]: List of matching banking transactions
        
    Raises:
        HTTPException: If query fails
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


@router.get("/transactions/subscriptions", tags=["Transactions"], response_model=List[BankingTransactionResponse])
async def query_subscriptions(
    current_user: User = Depends(get_current_user),
    file_id: Optional[str] = Query(default=None, description="Filter by file ID (user upload file ID)"),
    start_date: Optional[date] = Query(default=None, description="Filter transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter transactions up to this date (inclusive)"),
    merchant_name: Optional[str] = Query(default=None, description="Filter by merchant name (partial match, case-insensitive)"),
    transaction_type: Optional[str] = Query(default=None, regex="^(debit|credit)$", description="Filter by transaction type ('debit' or 'credit')"),
    min_amount: Optional[Decimal] = Query(default=None, description="Minimum transaction amount (inclusive)"),
    max_amount: Optional[Decimal] = Query(default=None, description="Maximum transaction amount (inclusive)"),
    transaction_year: Optional[int] = Query(default=None, description="Filter by transaction year"),
    transaction_month: Optional[int] = Query(default=None, ge=1, le=12, description="Filter by transaction month (1-12)"),
    currency: Optional[str] = Query(default=None, description="Filter by currency code (e.g., 'MYR')"),
    description: Optional[str] = Query(default=None, description="Filter by description (partial match, case-insensitive)"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
    order_by: str = Query(default="transaction_date", description="Field to order by (default: 'transaction_date')"),
    order_desc: bool = Query(default=True, description="If True, order descending; if False, order ascending"),
) -> List[BankingTransactionResponse]:
    """Query banking transactions filtered by subscriptions and memberships category.
    
    This endpoint specifically filters transactions where category == 'subscriptions_and_memberships'.
    All other filter parameters work the same as the general transactions endpoint.
    
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
        List[BankingTransactionResponse]: List of matching subscription transactions
        
    Raises:
        HTTPException: If query fails
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
            category=FinancialTransactionCategory.SUBSCRIPTIONS_AND_MEMBERSHIPS.value,
            min_amount=min_amount,
            max_amount=max_amount,
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
            detail=f"Failed to query subscription transactions: {str(e)}"
        )
