"""Banking transaction query endpoints."""
import asyncio
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query

import pandas as pd

from backend.utils.sankey import to_sankey
from backend.services.db.postgres_connector import database_service
from backend.schemas.transaction_response import BankingTransactionResponse

router = APIRouter()


@router.get("/transactions", response_model=List[BankingTransactionResponse])
async def query_transactions_all(
    user_id: Optional[int] = Query(default=1, description="Filter by user ID"),
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
    - User and file filters
    - Date ranges
    - Amount ranges
    - Transaction type, category, merchant name
    - Year/month filters
    - Currency and description search
    
    Args:
    - `user_id`: Filter by user ID
    - `file_id`: Filter by file ID (user upload file ID)
    - `start_date`: Filter transactions from this date onwards (inclusive)
    - `end_date`: Filter transactions up to this date (inclusive)
    - `merchant_name`: Filter by merchant name (partial match, case-insensitive)
    - `transaction_type`: Filter by transaction type ('debit' or 'credit')
    - `category`: Filter by transaction category
    - `min_amount`: Minimum transaction amount (inclusive)
    - `max_amount`: Maximum transaction amount (inclusive)
    - `is_subscription`: Filter by subscription status (likely to recur monthly)
    - `transaction_year`: Filter by transaction year
    - `transaction_month`: Filter by transaction month (1-12)
    - `currency`: Filter by currency code (e.g., 'MYR')
    - `description`: Filter by description (partial match, case-insensitive)
    - `limit`: Maximum number of results to return
    - `offset`: Number of results to skip (for pagination)
    - `order_by`: Field to order by (default: 'transaction_date')
    - `order_desc`: If True, order descending; if False, order ascending
        
    Returns:
    - `List[BankingTransactionResponse]`: List of matching banking transactions
        
    Raises:
    - `HTTPException`: If query fails
    """
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
    user_id: Optional[int] = Query(default=1, description="Filter by user ID"),
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
    - `user_id`: Filter by user ID
    - `file_id`: Filter by file ID (user upload file ID)
    - `start_date`: Filter transactions from this date onwards (inclusive)
    - `end_date`: Filter transactions up to this date (inclusive)
    - `merchant_name`: Filter by merchant name (partial match, case-insensitive)
    - `transaction_type`: Filter by transaction type ('debit' or 'credit')
    - `category`: Filter by transaction category
    - `min_amount`: Minimum transaction amount (inclusive)
    - `max_amount`: Maximum transaction amount (inclusive)
    - `is_subscription`: Filter by subscription status (likely to recur monthly)
    - `transaction_year`: Filter by transaction year
    - `transaction_month`: Filter by transaction month (1-12)
    - `currency`: Filter by currency code (e.g., 'MYR')
    - `description`: Filter by description (partial match, case-insensitive)
    - `limit`: Maximum number of results to return
    - `offset`: Number of results to skip (for pagination)
    - `order_by`: Field to order by (default: 'transaction_date')
    - `order_desc`: If True, order descending; if False, order ascending
        
    Returns:
    - `List[Dict[str, Any]]`: List of matching banking transactions converted to a dictionary format for sankey diagram
        
    Raises:
    - `HTTPException`: If query fails
    """
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

@router.get("/transactions/subscriptions", response_model=List[BankingTransactionResponse])
async def query_subscriptions_all(
    user_id: Optional[int] = Query(default=1, description="Filter by user ID"),
    transaction_year: Optional[int] = Query(default=None, description="Filter by transaction year"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
    order_by: str = Query(default="transaction_date", description="Field to order by (default: 'transaction_date')"),
    order_desc: bool = Query(default=True, description="If True, order descending; if False, order ascending"),
) -> List[BankingTransactionResponse]:
    """Query all banking transactions filtered by subscriptions and memberships category.
    
    This endpoint specifically filters transactions where category == 'subscriptions_and_memberships' and transaction_type == 'debit', and return all transactions in a single response.
    All other filter parameters work the same as the general transactions endpoint.
    
    Args:
    - `user_id`: Filter by user ID
    - `transaction_year`: Filter by transaction year
    - `limit`: Maximum number of results to return
    - `offset`: Number of results to skip (for pagination)
    - `order_by`: Field to order by (default: 'transaction_date')
    - `order_desc`: If True, order descending; if False, order ascending
        
    Returns:
    - `List[BankingTransactionResponse]`: List of matching subscription transactions
        
    Raises:
    - `HTTPException`: If query fails
    """
    try:
        transactions = database_service.filter_banking_transactions(
            user_id=user_id,
            transaction_type='debit', # Only debit transactions are considered as subscriptions
            is_subscription=True,
            transaction_year=transaction_year,
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
                is_subscription=tx.is_subscription,
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

@router.get("/transactions/subscriptions/aggregated")
async def query_subscriptions_aggregated(
    user_id: Optional[int] = Query(default=1, description="Filter by user ID"),
    transaction_year: Optional[int] = Query(default=None, description="Filter by transaction year"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip (for pagination)"),
    order_by: str = Query(default="transaction_date", description="Field to order by (default: 'transaction_date')"),
    order_desc: bool = Query(default=True, description="If True, order descending; if False, order ascending"),
):
    """Query banking transactions filtered by subscriptions and memberships category and returns an aggregated view by `merchant_name`.
    
    This endpoint specifically filters transactions where category == 'subscriptions_and_memberships'.
    All other filter parameters work the same as the general transactions endpoint.
    
    Args:
    - `user_id`: Filter by user ID
    - `transaction_year`: Filter by transaction year
    - `limit`: Maximum number of results to return
    - `offset`: Number of results to skip (for pagination)
    - `order_by`: Field to order by (default: 'transaction_date')
    - `order_desc`: If True, order descending; if False, order ascending
        
    Returns:
        List[Dict[str, Any]]: List of matching subscription transactions aggregated by `merchant_name` and `category`
        
    Raises:
        HTTPException: If query fails
    """
    try:
        transactions = database_service.filter_banking_transactions(
            user_id=user_id,
            is_subscription=True,
            transaction_type='debit', # Only debit transactions are considered as subscriptions
            transaction_year=transaction_year,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )

        # Convert SQLModel objects to dictionaries for pandas DataFrame
        transactions_dict = [
            {
                'merchant_name': tx.merchant_name,
                'category': tx.category,
                'amount': float(tx.amount) if tx.amount else 0.0,
                'transaction_month': tx.transaction_month,
            }
            for tx in transactions
        ]
        transactions_df = pd.DataFrame(transactions_dict)
        aggregated_df = transactions_df.groupby(['merchant_name', 'category']).agg({
            'amount': 'sum',
            'transaction_month': 'nunique',
        }).reset_index()

        aggregated_df['average_monthly_amount'] = aggregated_df['amount'] / aggregated_df['transaction_month']
        aggregated_df.rename(columns={'transaction_month': 'no_months_subscribed'}, inplace=True)

        return aggregated_df.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query subscription transactions: {str(e)}"
        )