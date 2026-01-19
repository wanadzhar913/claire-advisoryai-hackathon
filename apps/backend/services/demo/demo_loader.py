"""Helpers for loading demo transactions."""

import json
from datetime import date, datetime as dt
from decimal import Decimal
from pathlib import Path
from typing import List, Tuple

from backend.models.banking_transaction import BankingTransaction


def _demo_data_path() -> Path:
    local = Path(__file__).resolve().with_name("demo_data.json")
    if local.exists():
        return local
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "demo_data.json"
        if candidate.exists():
            return candidate
    candidate = Path.cwd() / "demo_data.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError("demo_data.json not found")


def load_demo_transactions(user_id: int, file_id: str) -> Tuple[List[BankingTransaction], dict]:
    path = _demo_data_path()
    raw = json.loads(path.read_text(encoding="utf-8"))

    transactions: List[BankingTransaction] = []
    dates: List[date] = []

    for idx, tx in enumerate(raw):
        raw_status = tx.get("subscription_status")
        if raw_status == "active":
            subscription_status = "confirmed"
        elif raw_status in {"predicted", "confirmed", "rejected", "needs_review"}:
            subscription_status = raw_status
        else:
            subscription_status = None

        tx_date = dt.strptime(tx["transaction_date"], "%Y-%m-%d").date()
        dates.append(tx_date)

        transactions.append(
            BankingTransaction(
                id=f"{file_id}_{idx}",
                user_id=user_id,
                file_id=file_id,
                transaction_date=tx_date,
                transaction_year=tx["transaction_year"],
                transaction_month=tx["transaction_month"],
                transaction_day=tx["transaction_day"],
                description=tx["description"],
                merchant_name=tx.get("merchant_name"),
                amount=Decimal(str(tx["amount"])),
                transaction_type=tx["transaction_type"],
                is_subscription=tx.get("is_subscription", False),
                balance=(
                    Decimal(str(tx["balance"]))
                    if tx.get("balance") is not None
                    else None
                ),
                reference_number=tx.get("reference_number"),
                transaction_code=tx.get("transaction_code"),
                category=tx.get("category"),
                currency=tx.get("currency", "MYR"),
                subscription_status=subscription_status,
                subscription_confidence=tx.get("subscription_confidence"),
                subscription_merchant_key=tx.get("subscription_merchant_key"),
                subscription_name=tx.get("subscription_name"),
                subscription_reason_codes=tx.get("subscription_reason_codes"),
                subscription_updated_at=(
                    dt.fromisoformat(tx["subscription_updated_at"])
                    if tx.get("subscription_updated_at")
                    else None
                ),
            )
        )

    latest_date = max(dates) if dates else date.today()
    metadata = {
        "file_size": path.stat().st_size,
        "latest_date": latest_date,
    }

    return transactions, metadata
