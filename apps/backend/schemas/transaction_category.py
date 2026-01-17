from enum import Enum
from typing import Literal

class FinancialTransactionCategory(str, Enum):
    """
    Categories for financial transactions.
    
    Usage:
        category = FinancialTransactionCategory.FOOD_AND_DINING_OUT
        category.value  # Returns "food_and_dining_out"
    """
    INCOME = "income"
    TRANSFER = "cash_transfer"
    HOUSING = "housing"
    TRANSPORTATION = "transportation"
    FOOD_AND_DINING_OUT = "food_and_dining_out"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    UTILITIES = "utilities"
    GROCERIES = "groceries"
    INVESTMENTS_AND_SAVINGS = "investments_and_savings"
    TECHNOLOGY_AND_ELECTRONICS = "technology_and_electronics"
    SPORT_AND_ACTIVITY = "sport_and_activity"
    OTHER = "other"


# Type alias for use in Pydantic models
TransactionCategoryLiteral = Literal[
    "income",
    "housing",
    "transportation",
    "food_and_dining_out",
    "entertainment",
    "healthcare",
    "education",
    "utilities",
    "groceries",
    "invenstments & savings",
    "technology_and_electronics",
    "sport_and_activity",
    "other"
]