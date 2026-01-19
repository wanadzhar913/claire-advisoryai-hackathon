"""Tool for querying aggregated subscription transactions.

This tool allows the agent to query subscription and membership transactions
and get an aggregated view by merchant name, showing total spending and
average monthly amounts.
"""

import asyncio
from typing import Optional
import json

import pandas as pd
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.services.db.postgres_connector import database_service


class QuerySubscriptionsInput(BaseModel):
    """Input schema for querying subscription transactions."""
    
    user_id: Optional[int] = Field(
        default=1,
        description="Filter by user ID (default: 1)"
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Filter by file ID (user upload file ID)"
    )
    transaction_year: Optional[int] = Field(
        default=None,
        description="Filter by transaction year (e.g., 2024)"
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip (for pagination)"
    )


async def query_subscriptions_aggregated(
    user_id: Optional[int] = 1,
    file_id: Optional[str] = None,
    transaction_year: Optional[int] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> str:
    """Query aggregated subscription transactions grouped by merchant name.
    
    This function queries subscription transactions (debit transactions marked as subscriptions)
    and returns an aggregated view showing:
    - merchant_name: Name of the merchant/service
    - category: Transaction category
    - amount: Total amount spent across all months
    - no_months_subscribed: Number of unique months with transactions
    - average_monthly_amount: Average amount per month
    
    Args:
        user_id: Filter by user ID (default: 1)
        transaction_year: Filter by transaction year (e.g., 2024)
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)
        
    Returns:
        JSON string containing aggregated subscription data
    """
    try:
        # Query transactions from database (sync call wrapped in thread)
        transactions = await asyncio.to_thread(
            database_service.filter_banking_transactions,
            user_id=user_id,
            file_id=file_id,
            is_subscription=True,
            transaction_type='debit',  # Only debit transactions are subscriptions
            transaction_year=transaction_year,
            limit=limit,
            offset=offset,
            order_by="transaction_date",
            order_desc=True,
        )

        # Convert to dictionaries for pandas DataFrame
        transactions_dict = [
            {
                'merchant_name': tx.merchant_name,
                'category': tx.category,
                'amount': float(tx.amount) if tx.amount else 0.0,
                'transaction_month': tx.transaction_month,
            }
            for tx in transactions
        ]
        
        if not transactions_dict:
            return json.dumps({
                "message": "No subscription transactions found",
                "subscriptions": []
            })
        
        # Create DataFrame and aggregate (pandas operations are CPU-bound, run in thread)
        def aggregate_transactions():
            transactions_df = pd.DataFrame(transactions_dict)
            aggregated_df = transactions_df.groupby(['merchant_name', 'category']).agg({
                'amount': 'sum',
                'transaction_month': 'nunique',
            }).reset_index()

            aggregated_df['average_monthly_amount'] = aggregated_df['amount'] / aggregated_df['transaction_month']
            aggregated_df.rename(columns={'transaction_month': 'no_months_subscribed'}, inplace=True)
            return aggregated_df
        
        aggregated_df = await asyncio.to_thread(aggregate_transactions)

        # Convert to dictionary and format for JSON
        result = aggregated_df.to_dict(orient='records')
        
        return json.dumps({
            "subscriptions": result,
            "total_subscriptions": len(result),
            "total_amount": float(aggregated_df['amount'].sum()),
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({
            "error": f"Failed to query subscription transactions: {str(e)}"
        })


query_subscriptions_tool = StructuredTool.from_function(
    coroutine=query_subscriptions_aggregated,
    name="query_subscriptions_aggregated",
    description="""Query aggregated subscription and membership transactions grouped by merchant name.
    
    Use this tool when users ask about:
    - Their recurring subscriptions (Netflix, Spotify, gym memberships, etc.)
    - Monthly subscription costs
    - Which subscriptions they're paying for
    - Total spending on subscriptions
    - Average monthly subscription costs
    
    Returns aggregated data showing merchant name, total amount spent, number of months subscribed,
    and average monthly amount for each subscription service.""",
    args_schema=QuerySubscriptionsInput,
    handle_tool_error=True,
)
