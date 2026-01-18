"""Subscription classification service using GPT-5 mini for detecting recurring transactions."""

import json
from datetime import date
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

try:
    from backend.config import settings
    from backend.models.banking_transaction import BankingTransaction
    from backend.services.db.postgres_connector import database_service
except ImportError:
    import sys
    from pathlib import Path
    apps_dir = Path(__file__).parent.parent.parent.parent
    if str(apps_dir) not in sys.path:
        sys.path.insert(0, str(apps_dir))
    from backend.config import settings
    from backend.models.banking_transaction import BankingTransaction
    from backend.services.db.postgres_connector import database_service


# Pydantic models for LLM response validation
class SubscriptionDecision(BaseModel):
    """Single subscription classification decision from LLM."""
    transaction_id: str = Field(..., description="The transaction ID being classified")
    subscription_status: str = Field(..., description="Classification status: predicted, rejected, or needs_review")
    is_subscription: bool = Field(..., description="Whether this is a subscription transaction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    merchant_key: Optional[str] = Field(None, description="Normalized merchant key for grouping")
    subscription_name: Optional[str] = Field(None, description="Display name for the subscription")
    reason_codes: List[str] = Field(default_factory=list, description="Short reason codes for the decision")

    @field_validator('subscription_status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {'predicted', 'rejected', 'needs_review'}
        if v not in allowed:
            raise ValueError(f"subscription_status must be one of {allowed}")
        return v

    @field_validator('is_subscription')
    @classmethod
    def validate_is_subscription_alignment(cls, v: bool, info) -> bool:
        """Ensure is_subscription aligns with subscription_status."""
        status = info.data.get('subscription_status')
        if status == 'predicted' and not v:
            raise ValueError("is_subscription must be True when subscription_status is 'predicted'")
        if status == 'rejected' and v:
            raise ValueError("is_subscription must be False when subscription_status is 'rejected'")
        return v


class ClassificationRange(BaseModel):
    """Date range for classification."""
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")


class LLMClassificationResponse(BaseModel):
    """Complete LLM response for subscription classification."""
    range: ClassificationRange
    decisions: List[SubscriptionDecision]


class ClassificationSummary(BaseModel):
    """Summary of classification results."""
    total_processed: int = 0
    predicted_count: int = 0
    rejected_count: int = 0
    needs_review_count: int = 0
    failed_batches: List[Dict[str, Any]] = Field(default_factory=list)
    start_date: date
    end_date: date


class SubscriptionClassifier:
    """Service for classifying transactions as subscriptions using GPT-5 mini."""

    # Configuration
    BATCH_SIZE = 300  # Transactions per LLM call
    MAX_RANGE_DAYS = 365  # Maximum date range allowed
    MODEL_NAME = "gpt-5-mini"

    def __init__(self):
        """Initialize the subscription classifier."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def classify_subscriptions_range(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> ClassificationSummary:
        """Classify transactions in a date range as subscriptions.

        Args:
            user_id: The user ID to classify transactions for
            start_date: Start date of the range (inclusive)
            end_date: End date of the range (inclusive)

        Returns:
            ClassificationSummary: Summary of classification results

        Raises:
            ValueError: If date range is invalid
        """
        # Validate date range
        self._validate_date_range(start_date, end_date)

        # Initialize summary
        summary = ClassificationSummary(
            start_date=start_date,
            end_date=end_date,
        )

        # Get candidate transactions
        candidates = database_service.get_subscription_candidates(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            exclude_confirmed_rejected=True,
        )

        if not candidates:
            return summary

        # Process in batches
        for batch_start in range(0, len(candidates), self.BATCH_SIZE):
            batch_end = min(batch_start + self.BATCH_SIZE, len(candidates))
            batch = candidates[batch_start:batch_end]

            try:
                decisions = self._classify_batch(batch, start_date, end_date)
                self._apply_decisions(decisions, summary)
            except Exception as e:
                summary.failed_batches.append({
                    "batch_start": batch_start,
                    "batch_end": batch_end,
                    "error": str(e),
                    "transaction_ids": [tx.id for tx in batch],
                })
                # Mark failed batch transactions as needs_review
                self._mark_batch_as_needs_review(batch, summary)

        return summary

    def _validate_date_range(self, start_date: date, end_date: date) -> None:
        """Validate the date range for classification.

        Args:
            start_date: Start date of the range
            end_date: End date of the range

        Raises:
            ValueError: If date range is invalid
        """
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")

        days_diff = (end_date - start_date).days
        if days_diff > self.MAX_RANGE_DAYS:
            raise ValueError(f"Date range cannot exceed {self.MAX_RANGE_DAYS} days")

    def _classify_batch(
        self,
        transactions: List[BankingTransaction],
        start_date: date,
        end_date: date,
    ) -> List[SubscriptionDecision]:
        """Classify a batch of transactions using GPT-5 mini.

        Args:
            transactions: List of transactions to classify
            start_date: Start date of the range
            end_date: End date of the range

        Returns:
            List[SubscriptionDecision]: Classification decisions for each transaction
        """
        # Build input payload
        input_payload = self._build_llm_input(transactions, start_date, end_date)

        # Call LLM
        response = self._call_llm(input_payload)

        # Parse and validate response
        decisions = self._parse_llm_response(response, transactions)

        return decisions

    def _build_llm_input(
        self,
        transactions: List[BankingTransaction],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Build the input payload for the LLM.

        Args:
            transactions: List of transactions to classify
            start_date: Start date of the range
            end_date: End date of the range

        Returns:
            Dict containing the input payload
        """
        tx_list = []
        for tx in transactions:
            tx_dict = {
                "id": tx.id,
                "transaction_date": tx.transaction_date.isoformat(),
                "description": tx.description,
                "merchant_name": tx.merchant_name,
                "amount": str(tx.amount),
                "currency": tx.currency,
                "category": tx.category,
            }
            tx_list.append(tx_dict)

        return {
            "range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "transactions": tx_list,
        }

    def _call_llm(self, input_payload: Dict[str, Any]) -> str:
        """Call GPT-5 mini with the classification prompt.

        Args:
            input_payload: The input payload for classification

        Returns:
            str: The LLM response content
        """
        system_prompt = self._get_system_prompt()
        user_prompt = json.dumps(input_payload, indent=2)

        response = self.client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content

    def _get_system_prompt(self) -> str:
        """Get the system prompt for subscription classification.

        Returns:
            str: The system prompt
        """
        return """You are a financial transaction classifier specializing in identifying subscription and recurring payment transactions.

				Your task is to analyze banking transactions and classify each one as either a subscription (recurring payment) or not.

				CLASSIFICATION RULES:
				1. Subscriptions are recurring payments that happen regularly (monthly, yearly, weekly).
				2. Common subscription indicators:
					- Streaming services (Netflix, Spotify, Apple Music, YouTube Premium, Disney+, OpenAI)
					- Software subscriptions (Adobe, Microsoft 365, Dropbox, iCloud)
					- Gym memberships and fitness apps
					- News/magazine subscriptions
					- Cloud services (AWS, Google Cloud, hosting)
					- Gaming subscriptions (Xbox Game Pass, PlayStation Plus, Steam)
					- Food delivery memberships (GrabFood, Foodpanda subscriptions)
					- Insurance premiums (if recurring)
					- Loan/mortgage payments (if recurring)
					- Utility bills (if consistent amounts)

				3. NOT subscriptions:
					- One-time purchases
					- Variable grocery shopping
					- Restaurant meals (unless membership)
					- ATM withdrawals
					- Fund transfers between accounts
					- Irregular payments

				4. If merchant_name is missing, infer from description if possible.
				5. If uncertain, use "needs_review" status with lower confidence.

				SUBSCRIPTION STATUS RULES:
				- "predicted": High confidence this IS a subscription (is_subscription must be true)
				- "rejected": High confidence this is NOT a subscription (is_subscription must be false)
				- "needs_review": Uncertain, needs manual review (is_subscription should be false)

				MERCHANT KEY RULES:
				- Normalize merchant names for grouping (e.g., "NETFLIX.COM" and "Netflix" -> "netflix")
				- Use lowercase, remove special characters
				- Keep it short and recognizable

				REASON CODES (use short codes):
				- "recurring_pattern": Transaction appears to recur regularly
				- "known_subscription": Known subscription service
				- "membership_keyword": Contains membership/subscription keywords
				- "fixed_amount": Same amount each period
				- "one_time": Appears to be one-time purchase
				- "variable_amount": Amount varies too much
				- "transfer": Fund transfer, not subscription
				- "uncertain": Cannot determine with confidence

				OUTPUT FORMAT:
				Return ONLY a valid JSON object with this exact structure:
				{
					"range": {
						"start_date": "YYYY-MM-DD",
						"end_date": "YYYY-MM-DD"
					},
					"decisions": [
						{
							"transaction_id": "string",
							"subscription_status": "predicted" | "rejected" | "needs_review",
							"is_subscription": boolean,
							"confidence": number (0.0 to 1.0),
							"merchant_key": "string or null",
							"subscription_name": "string or null",
							"reason_codes": ["string", ...]
						}
					]
				}

				IMPORTANT:
				- Return a decision for EVERY transaction in the input
				- Do not invent transaction IDs
				- Confidence should reflect your certainty (0.0 = no confidence, 1.0 = certain)
				- Never mark credit transactions as subscriptions (input should only contain debits)"""

    def _parse_llm_response(
        self,
        response_content: str,
        input_transactions: List[BankingTransaction],
    ) -> List[SubscriptionDecision]:
        """Parse and validate the LLM response.

        Args:
            response_content: The raw LLM response content
            input_transactions: The original input transactions for validation

        Returns:
            List[SubscriptionDecision]: Validated classification decisions
        """
        # Parse JSON
        try:
            response_data = json.loads(response_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        # Validate with Pydantic
        try:
            validated_response = LLMClassificationResponse(**response_data)
        except Exception as e:
            raise ValueError(f"LLM response validation failed: {e}")

        # Build set of valid transaction IDs
        valid_ids = {tx.id for tx in input_transactions}

        # Filter decisions to only include valid transaction IDs
        valid_decisions = []
        returned_ids = set()

        for decision in validated_response.decisions:
            if decision.transaction_id in valid_ids:
                valid_decisions.append(decision)
                returned_ids.add(decision.transaction_id)

        # Handle missing transactions - mark as needs_review
        missing_ids = valid_ids - returned_ids
        for missing_id in missing_ids:
            valid_decisions.append(SubscriptionDecision(
                transaction_id=missing_id,
                subscription_status="needs_review",
                is_subscription=False,
                confidence=0.0,
                merchant_key=None,
                subscription_name=None,
                reason_codes=["missing_from_response"],
            ))

        return valid_decisions

    def _apply_decisions(
        self,
        decisions: List[SubscriptionDecision],
        summary: ClassificationSummary,
    ) -> None:
        """Apply classification decisions to the database.

        Args:
            decisions: List of classification decisions
            summary: Summary to update with counts
        """
        updates = []
        for decision in decisions:
            update = {
                "transaction_id": decision.transaction_id,
                "is_subscription": decision.is_subscription,
                "subscription_status": decision.subscription_status,
                "subscription_confidence": decision.confidence,
                "subscription_merchant_key": decision.merchant_key,
                "subscription_name": decision.subscription_name,
                "subscription_reason_codes": decision.reason_codes,
            }
            updates.append(update)

            # Update summary counts
            summary.total_processed += 1
            if decision.subscription_status == "predicted":
                summary.predicted_count += 1
            elif decision.subscription_status == "rejected":
                summary.rejected_count += 1
            else:
                summary.needs_review_count += 1

        # Bulk update database
        database_service.bulk_update_subscription_classification(updates)

    def _mark_batch_as_needs_review(
        self,
        transactions: List[BankingTransaction],
        summary: ClassificationSummary,
    ) -> None:
        """Mark a failed batch as needs_review.

        Args:
            transactions: List of transactions in the failed batch
            summary: Summary to update with counts
        """
        updates = []
        for tx in transactions:
            update = {
                "transaction_id": tx.id,
                "is_subscription": False,
                "subscription_status": "needs_review",
                "subscription_confidence": 0.0,
                "subscription_merchant_key": None,
                "subscription_name": None,
                "subscription_reason_codes": ["batch_failed"],
            }
            updates.append(update)
            summary.total_processed += 1
            summary.needs_review_count += 1

        database_service.bulk_update_subscription_classification(updates)


# Singleton instance
subscription_classifier = SubscriptionClassifier()
