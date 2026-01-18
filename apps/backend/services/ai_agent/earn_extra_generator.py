"""Generate earn-extra plans based on user transactions."""

import json
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.config import settings
from backend.models.earn_extra_plan import EarnExtraPlan
from backend.models.banking_transaction import BankingTransaction
from backend.services.db.postgres_connector import database_service


SYSTEM_PROMPT = """
You are an expert financial planning assistant for Malaysian users.
Return ONLY valid JSON that matches the provided schema.
Do not include markdown, comments, or additional keys.
All amounts are in MYR; UI will display as RM.
Be practical, non-judgmental, and realistic.
"""

def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _normalize_key(value: Optional[str]) -> str:
    s = (value or "").strip().lower()
    if not s:
        return "other"
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "other"


def _build_spend_profile(transactions: List[BankingTransaction]) -> Dict[str, Any]:
    if not transactions:
        return {
            "currency": "MYR",
            "period_start": None,
            "period_end": None,
            "monthly_income_est": 0,
            "monthly_spend_est": 0,
            "category_breakdown": {},
            "top_merchants": [],
            "opportunity_flags": [],
        }

    income_total = Decimal("0")
    spend_total = Decimal("0")
    category_totals: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    merchant_totals: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"amount": Decimal("0"), "count": 0})

    dates: List[datetime] = []
    currency = "MYR"

    for tx in transactions:
        amount = _to_decimal(tx.amount)
        currency = tx.currency or currency
        if tx.transaction_date:
            dates.append(datetime.combine(tx.transaction_date, datetime.min.time()))

        if tx.transaction_type == "credit":
            income_total += amount
            continue

        spend_total += amount
        category_key = _normalize_key(tx.category or "other")
        category_totals[category_key] += amount

        merchant = tx.merchant_name or tx.description or "Unknown"
        merchant_key = merchant.strip()
        merchant_totals[merchant_key]["amount"] += amount
        merchant_totals[merchant_key]["count"] += 1

    top_merchants = sorted(
        (
            {"merchant": k, "amount": float(v["amount"]), "count": v["count"]}
            for k, v in merchant_totals.items()
        ),
        key=lambda item: item["amount"],
        reverse=True,
    )[:10]

    period_start = min(dates).strftime("%Y-%m-%d") if dates else None
    period_end = max(dates).strftime("%Y-%m-%d") if dates else None

    # Heuristic opportunity flags
    opportunity_flags: List[str] = []
    eating_out = category_totals.get("eating_out", Decimal("0")) + category_totals.get("food", Decimal("0"))
    ride_hailing = category_totals.get("ride_hailing", Decimal("0")) + category_totals.get("transport", Decimal("0"))
    subscriptions = category_totals.get("subscriptions", Decimal("0"))
    coffee = category_totals.get("coffee", Decimal("0"))

    if eating_out >= Decimal("200"):
        opportunity_flags.append("eating_out_high")
    if ride_hailing >= Decimal("150"):
        opportunity_flags.append("ride_hailing_frequent")
    if subscriptions >= Decimal("80"):
        opportunity_flags.append("subscriptions_many")
    if coffee >= Decimal("80"):
        opportunity_flags.append("coffee_frequent")

    return {
        "currency": currency or "MYR",
        "period_start": period_start,
        "period_end": period_end,
        "monthly_income_est": float(income_total),
        "monthly_spend_est": float(spend_total),
        "category_breakdown": {k: float(v) for k, v in category_totals.items()},
        "top_merchants": top_merchants,
        "opportunity_flags": opportunity_flags,
    }


def _default_plans(target_amount: Decimal, timeframe_days: int) -> List[Dict[str, Any]]:
    target = float(target_amount)
    return [
        {
            "title": "Trim discretionary spend",
            "summary": "Reduce small discretionary spends to hit your target steadily.",
            "expected_amount": target,
            "confidence": "med",
            "actions": [
                {
                    "label": "Skip eating out 3 times per week and cook at home",
                    "type": "cut_spend",
                    "weekly_frequency": 3,
                    "estimated_value": target * 0.4,
                },
                {
                    "label": "Pause 1 non-essential subscription for the month",
                    "type": "cut_spend",
                    "weekly_frequency": 1,
                    "estimated_value": target * 0.2,
                },
                {
                    "label": "Set a weekly cash cap for discretionary purchases",
                    "type": "shift_spend",
                    "weekly_frequency": 1,
                    "estimated_value": target * 0.4,
                },
            ],
        },
        {
            "title": "Smart swaps",
            "summary": "Swap higher-cost habits for cheaper alternatives each week.",
            "expected_amount": target,
            "confidence": "med",
            "actions": [
                {
                    "label": "Replace 2 ride-hailing trips with public transport",
                    "type": "shift_spend",
                    "weekly_frequency": 2,
                    "estimated_value": target * 0.35,
                },
                {
                    "label": "Make coffee at home 4 days per week",
                    "type": "cut_spend",
                    "weekly_frequency": 4,
                    "estimated_value": target * 0.25,
                },
                {
                    "label": "Bundle grocery runs to avoid impulse buys",
                    "type": "shift_spend",
                    "weekly_frequency": 1,
                    "estimated_value": target * 0.4,
                },
            ],
        },
        {
            "title": "Boost and clean up",
            "summary": "Combine a one-time clean-up with a small income boost.",
            "expected_amount": target,
            "confidence": "low",
            "actions": [
                {
                    "label": "Sell 3 unused items online",
                    "type": "one_time_cleanup",
                    "weekly_frequency": 1,
                    "estimated_value": target * 0.4,
                },
                {
                    "label": "Take 1 extra paid shift or gig task",
                    "type": "increase_income",
                    "weekly_frequency": 1,
                    "estimated_value": target * 0.35,
                },
                {
                    "label": "Review fees and waive/avoid one bank charge",
                    "type": "cut_spend",
                    "weekly_frequency": 1,
                    "estimated_value": target * 0.25,
                },
            ],
        },
    ]


def _validate_llm_output(data: Dict[str, Any]) -> bool:
    try:
        plans = data.get("plans")
        if not isinstance(plans, list) or len(plans) != 3:
            return False
        for plan in plans:
            if not isinstance(plan, dict):
                return False
            actions = plan.get("actions")
            if not isinstance(actions, list) or len(actions) != 3:
                return False
        return True
    except Exception:
        return False


def _sanitize_llm_plans(data: Dict[str, Any], target_amount: Decimal, timeframe_days: int) -> Tuple[int, Decimal, List[Dict[str, Any]]]:
    timeframe = int(data.get("timeframe_days") or timeframe_days)
    target = _to_decimal(data.get("target_amount") or target_amount)
    plans = data.get("plans") or []
    return timeframe, target, plans


async def _call_llm(spend_profile: Dict[str, Any], target_amount: Decimal, timeframe_days: int) -> Dict[str, Any]:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        api_key=settings.OPENAI_API_KEY,
    )

    payload = {
        "task": "Generate 3 realistic plans to help the user reach RM500 extra within 30 days using only changes inferred from their transaction patterns.",
        "constraints": {
            "currency": "MYR",
            "target_amount": float(target_amount),
            "timeframe_days": timeframe_days,
            "num_plans": 3,
            "actions_per_plan": 3,
            "tone": "practical, non-judgmental",
            "no_long_text": True,
        },
        "user_spend_profile": spend_profile,
    }

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ])

    content = response.content.strip() if response and response.content else ""
    return json.loads(content)


def _build_progress_list() -> List[Dict[str, Any]]:
    return [
        {"is_done": False, "notes": None},
        {"is_done": False, "notes": None},
        {"is_done": False, "notes": None},
    ]


async def generate_earn_extra_plans(
    user_id: int,
    file_id: Optional[str],
    target_amount: Decimal,
    timeframe_days: int,
) -> List[EarnExtraPlan]:
    # Resolve file_id to latest if missing
    resolved_file_id = file_id
    if not resolved_file_id:
        uploads = database_service.get_user_uploads(user_id=user_id, limit=1, order_by="created_at", order_desc=True)
        if uploads:
            resolved_file_id = uploads[0].file_id

    transactions = []
    if resolved_file_id:
        transactions = database_service.filter_banking_transactions(user_id=user_id, file_id=resolved_file_id)

    spend_profile = _build_spend_profile(transactions)

    plans_payload: Optional[Dict[str, Any]] = None
    try:
        plans_payload = await _call_llm(spend_profile, target_amount, timeframe_days)
    except Exception:
        plans_payload = None

    if not plans_payload or not _validate_llm_output(plans_payload):
        plans_data = _default_plans(target_amount, timeframe_days)
        timeframe = timeframe_days
        target = target_amount
    else:
        timeframe, target, plans_data = _sanitize_llm_plans(plans_payload, target_amount, timeframe_days)

    plans: List[EarnExtraPlan] = []
    for plan in plans_data[:3]:
        actions = plan.get("actions") or []
        if len(actions) != 3:
            actions = (actions + _default_plans(target_amount, timeframe_days)[0]["actions"])[:3]

        plans.append(
            EarnExtraPlan(
                user_id=user_id,
                file_id=resolved_file_id,
                status="generated",
                target_amount=target,
                currency="MYR",
                timeframe_days=timeframe,
                title=str(plan.get("title") or "Earn extra plan"),
                summary=str(plan.get("summary") or "A practical plan to reach your target."),
                actions=actions,
                expected_amount=_to_decimal(plan.get("expected_amount") or target),
                confidence=plan.get("confidence") or "med",
                saved_so_far=Decimal("0"),
                actions_progress=_build_progress_list(),
                updated_at=datetime.utcnow(),
            )
        )

    return database_service.create_earn_extra_plans(plans)
