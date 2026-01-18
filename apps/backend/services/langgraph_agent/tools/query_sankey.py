"""Tool for querying transactions in sankey diagram format.

This tool allows the agent to query transactions and format them for visualization
as a sankey diagram, showing the flow of money from income sources to spending categories.
"""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Optional
import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.services.db.postgres_connector import database_service
from backend.utils.sankey import to_sankey


class QuerySankeyInput(BaseModel):
    """Input schema for querying transactions for sankey diagram."""
    
    user_id: Optional[int] = Field(
        default=1,
        description="Filter by user ID (default: 1)"
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Filter by file ID (user upload file ID)"
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Filter transactions from this date onwards (YYYY-MM-DD format, inclusive)"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Filter transactions up to this date (YYYY-MM-DD format, inclusive)"
    )
    merchant_name: Optional[str] = Field(
        default=None,
        description="Filter by merchant name (partial match, case-insensitive)"
    )
    transaction_type: Optional[str] = Field(
        default=None,
        pattern="^(debit|credit)$",
        description="Filter by transaction type ('debit' or 'credit')"
    )
    category: Optional[str] = Field(
        default=None,
        description="Filter by transaction category"
    )
    min_amount: Optional[float] = Field(
        default=None,
        description="Minimum transaction amount (inclusive)"
    )
    max_amount: Optional[float] = Field(
        default=None,
        description="Maximum transaction amount (inclusive)"
    )
    is_subscription: Optional[bool] = Field(
        default=None,
        description="Filter by subscription status (likely to recur monthly)"
    )
    transaction_year: Optional[int] = Field(
        default=None,
        description="Filter by transaction year (e.g., 2024)"
    )
    transaction_month: Optional[int] = Field(
        default=None,
        ge=1,
        le=12,
        description="Filter by transaction month (1-12)"
    )
    currency: Optional[str] = Field(
        default=None,
        description="Filter by currency code (e.g., 'MYR')"
    )
    description: Optional[str] = Field(
        default=None,
        description="Filter by description (partial match, case-insensitive)"
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )


async def query_transactions_sankey(
    user_id: Optional[int] = 1,
    file_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    merchant_name: Optional[str] = None,
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    is_subscription: Optional[bool] = None,
    transaction_year: Optional[int] = None,
    transaction_month: Optional[int] = None,
    currency: Optional[str] = None,
    description: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """Query transactions and format them for sankey diagram visualization.
    
    This function queries banking transactions based on various filters and returns
    data formatted for sankey diagram visualization, showing:
    - Income sources (credits) flowing into the main account
    - Spending categories (debits) flowing out of the main account
    
    Args:
        user_id: Filter by user ID (default: 1)
        file_id: Filter by file ID (user upload file ID)
        start_date: Filter transactions from this date onwards (YYYY-MM-DD format)
        end_date: Filter transactions up to this date (YYYY-MM-DD format)
        merchant_name: Filter by merchant name (partial match)
        transaction_type: Filter by transaction type ('debit' or 'credit')
        category: Filter by transaction category
        min_amount: Minimum transaction amount
        max_amount: Maximum transaction amount
        is_subscription: Filter by subscription status
        transaction_year: Filter by transaction year
        transaction_month: Filter by transaction month (1-12)
        currency: Filter by currency code
        description: Filter by description (partial match)
        limit: Maximum number of results to return
        
    Returns:
        JSON string containing sankey diagram data with nodes and links
    """
    try:
        # Parse date strings to date objects if provided
        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = date.fromisoformat(start_date)
        if end_date:
            end_date_obj = date.fromisoformat(end_date)
        
        # Convert float amounts to Decimal if provided
        min_amount_decimal = Decimal(str(min_amount)) if min_amount is not None else None
        max_amount_decimal = Decimal(str(max_amount)) if max_amount is not None else None
        
        # Query transactions from database (sync call wrapped in thread)
        transactions = await asyncio.to_thread(
            database_service.filter_banking_transactions,
            user_id=user_id,
            file_id=file_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            merchant_name=merchant_name,
            transaction_type=transaction_type,
            category=category,
            min_amount=min_amount_decimal,
            max_amount=max_amount_decimal,
            is_subscription=is_subscription,
            transaction_year=transaction_year,
            transaction_month=transaction_month,
            currency=currency,
            description=description,
            limit=limit,
            offset=0,
            order_by="transaction_date",
            order_desc=True,
        )

        # Convert SQLModel objects to dictionaries for sankey diagram
        transactions_dict = [
            {
                'amount': float(tx.amount) if tx.amount else 0.0,
                'transaction_type': tx.transaction_type,
                'merchant_name': tx.merchant_name or 'Unknown',
                'category': tx.category or 'other',
            }
            for tx in transactions
        ]

        # Format to sankey diagram appropriate format (to_sankey uses pandas, run in thread)
        sankey_data = await asyncio.to_thread(to_sankey, transactions_dict)
        
        return json.dumps(sankey_data, indent=2, default=str)
    except Exception as e:
        return json.dumps({
            "error": f"Failed to query transactions for sankey diagram: {str(e)}"
        })


query_sankey_tool = StructuredTool.from_function(
    coroutine=query_transactions_sankey,
    name="query_transactions_sankey",
    description="""Query transactions and format them for sankey diagram visualization.
    
    Use this tool when users ask about:
    - Visualizing their income and spending flow
    - Understanding where their money comes from and where it goes
    - Spending patterns by category
    - Income sources
    - Overall financial flow visualization
    
    Returns data formatted for sankey diagram showing:
    - Nodes: Income sources, main account, and spending categories
    - Links: Flow of money from sources to account, and from account to categories
    - Values: Amounts for each flow
    
    The sankey diagram helps visualize the complete financial picture.""",
    args_schema=QuerySankeyInput,
    handle_tool_error=True,
)
