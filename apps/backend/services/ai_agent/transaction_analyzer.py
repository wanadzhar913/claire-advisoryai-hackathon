"""LangGraph-based transaction analyzer agent for generating financial insights.

This module intentionally keeps *numbers deterministic* (computed from transactions)
and uses the LLM primarily for *wording and prioritization*.
"""

import uuid
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

try:
    from backend.config import settings
    from backend.models.financial_insight import FinancialInsight
    from backend.models.banking_transaction import BankingTransaction
    from backend.services.db.postgres_connector import database_service
    from backend.utils.formatting import detect_file_currency, format_money
except ImportError:
    import sys
    from pathlib import Path
    apps_dir = Path(__file__).parent.parent.parent.parent
    if str(apps_dir) not in sys.path:
        sys.path.insert(0, str(apps_dir))
    from backend.config import settings
    from backend.models.financial_insight import FinancialInsight
    from backend.models.banking_transaction import BankingTransaction
    from backend.services.db.postgres_connector import database_service
    from backend.utils.formatting import detect_file_currency, format_money


class AgentState(TypedDict):
    """State for the transaction analyzer agent."""
    user_id: int
    file_id: Optional[str]
    transactions: List[Dict[str, Any]]
    aggregated_data: Dict[str, Any]
    file_currency: str
    time_range: Dict[str, Optional[str]]
    observed_time_range: Dict[str, Optional[str]]
    candidates: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]]  # spending insights (final)
    alerts: List[Dict[str, Any]]  # alerts (final)
    recommendations: List[Dict[str, Any]]  # recommendations (final)
    insights: List[FinancialInsight]


# The small model must output ONLY valid JSON matching this schema.
# Enforcement is backed by a deterministic post-processing layer.
INSIGHTS_LLM_OUTPUT_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["spending_insights", "alerts", "recommendations"],
    "properties": {
        "spending_insights": {
            "type": "array",
            "minItems": 0,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "detail", "severity", "metric", "supporting_transaction_ids", "source_candidate_key"],
                "properties": {
                    "title": {"type": "string", "maxLength": 52},
                    "detail": {"type": "string", "maxLength": 140},
                    "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                    "metric": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["label", "value"],
                        "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
                    },
                    "supporting_transaction_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
                    "source_candidate_key": {"type": "string"},
                },
            },
        },
        "alerts": {
            "type": "array",
            "minItems": 0,
            "maxItems": 2,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "detail", "severity", "metric", "supporting_transaction_ids"],
                "properties": {
                    "title": {"type": "string", "maxLength": 52},
                    "detail": {"type": "string", "maxLength": 140},
                    "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                    "metric": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["label", "value"],
                        "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
                    },
                    "supporting_transaction_ids": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 3},
                },
            },
        },
        "recommendations": {
            "type": "array",
            "minItems": 0,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "detail", "linked_to_title"],
                "properties": {
                    "title": {"type": "string", "maxLength": 52},
                    "detail": {"type": "string", "maxLength": 140},
                    "linked_to_title": {"type": "string"},
                },
            },
        },
    },
}

INSIGHTS_SYSTEM_PROMPT = (
    "You generate concise, data-grounded financial insights.\n"
    "You never invent numbers. You never use '$'. You always use the provided currency code.\n"
    "Stay factual; do not infer lifestyle or psychology.\n"
    "Return ONLY valid JSON matching the provided JSON Schema.\n"
)


class TransactionAnalyzerAgent:
    """LangGraph agent for analyzing transactions and generating insights."""

    def __init__(self):
        """Initialize the transaction analyzer agent."""
        self.llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )
        self.graph = self._build_graph()

    @staticmethod
    def _normalize_severity(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        mapping = {
            "low": "info",
            "medium": "warning",
            "high": "critical",
            "info": "info",
            "warning": "warning",
            "critical": "critical",
        }
        return mapping.get(value.lower())

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze_transactions", self._analyze_transactions)
        workflow.add_node("generate_alerts", self._generate_alerts)
        workflow.add_node("finalize_insights", self._finalize_insights)
        workflow.add_node("save_insights", self._save_insights)

        # Define edges (linear flow)
        workflow.set_entry_point("analyze_transactions")
        workflow.add_edge("analyze_transactions", "generate_alerts")
        workflow.add_edge("generate_alerts", "finalize_insights")
        workflow.add_edge("finalize_insights", "save_insights")
        workflow.add_edge("save_insights", END)

        return workflow.compile()

    def _parse_date(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # expected: YYYY-MM-DD (from analyze())
                return datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return None
        return None

    def _normalize_key(self, value: Optional[str]) -> str:
        """Normalize merchant/category keys for grouping."""
        s = (value or "").strip().lower()
        if not s:
            return "unknown"
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "unknown"

    def _pct(self, numerator: Decimal, denominator: Decimal) -> float:
        if denominator <= 0:
            return 0.0
        return float((numerator / denominator) * Decimal("100"))

    def _analyze_transactions(self, state: AgentState) -> AgentState:
        """Aggregate transaction data + produce scored insight candidates (deterministic)."""
        transactions = state["transactions"]
        
        if not transactions:
            state["aggregated_data"] = {}
            state["file_currency"] = "MYR"
            state["time_range"] = {"start": None, "end": None}
            state["candidates"] = []
            return state

        # Aggregate by category
        category_totals = defaultdict(lambda: {"total": Decimal("0"), "count": 0, "txs": []})
        merchant_totals = defaultdict(lambda: {"total": Decimal("0"), "count": 0, "txs": []})
        weekday_spending = defaultdict(lambda: {"total": Decimal("0"), "count": 0})
        
        total_income = Decimal("0")
        total_expenses = Decimal("0")
        expense_amounts: List[Decimal] = []
        currencies: List[Optional[str]] = []
        date_values: List[datetime] = []

        for tx in transactions:
            amount = Decimal(str(tx.get("amount", 0)))
            category = tx.get("category") or "other"
            merchant = tx.get("merchant_name") or tx.get("description") or "Unknown"
            tx_type = tx.get("transaction_type", "debit")
            tx_date = tx.get("transaction_date")
            currencies.append(tx.get("currency"))

            dt = self._parse_date(tx_date)
            if dt is not None:
                date_values.append(dt)
            
            if tx_type == "credit":
                total_income += amount
            else:
                total_expenses += amount
                expense_amounts.append(amount)
                
                # Category aggregation
                category_totals[category]["total"] += amount
                category_totals[category]["count"] += 1
                category_totals[category]["txs"].append(tx)
                
                # Merchant aggregation
                if merchant:
                    merchant_totals[merchant]["total"] += amount
                    merchant_totals[merchant]["count"] += 1
                    merchant_totals[merchant]["txs"].append(tx)
                
                # Daily spending pattern
                if dt is not None:
                    weekday = dt.strftime("%A")
                    weekday_spending[weekday]["total"] += amount
                    weekday_spending[weekday]["count"] += 1

        file_currency = detect_file_currency(currencies, default="MYR", dominant_threshold=0.9)
        start_dt = min(date_values) if date_values else None
        end_dt = max(date_values) if date_values else None
        observed_time_range = {
            "start": start_dt.strftime("%Y-%m-%d") if start_dt else None,
            "end": end_dt.strftime("%Y-%m-%d") if end_dt else None,
        }
        requested_time_range = state.get("time_range") or {"start": None, "end": None}
        has_requested = bool(requested_time_range.get("start") and requested_time_range.get("end"))
        effective_time_range = requested_time_range if has_requested else observed_time_range

        # Candidate generation (deterministic)
        candidates: List[Dict[str, Any]] = []

        # 1) Category concentration (top categories by total spend)
        sorted_categories = sorted(
            category_totals.items(),
            key=lambda kv: kv[1]["total"],
            reverse=True,
        )
        for category, data in sorted_categories[:8]:
            if total_expenses <= 0:
                continue
            share = float(data["total"] / total_expenses)
            if share < 0.15:
                continue

            # supporting IDs: top 3 txs by amount for this category
            txs_sorted = sorted(
                data["txs"],
                key=lambda t: Decimal(str(t.get("amount", "0"))),
                reverse=True,
            )
            supporting_ids = [str(t.get("id")) for t in txs_sorted[:3] if t.get("id")]
            candidate_key = f"category_concentration:{self._normalize_key(category)}"

            metric_value = (
                f"{format_money(data['total'], file_currency)} ({self._pct(data['total'], total_expenses):.0f}%)"
                if file_currency != "MULTI"
                else f"{data['total']:,.2f} total (MULTI)"
            )
            candidates.append({
                "candidate_type": "category_concentration",
                "key": candidate_key,
                "metrics": {
                    "category": category,
                    "category_total": float(data["total"]),
                    "share_of_expenses": round(share, 4),
                    "count": int(data["count"]),
                    "metric_label": f"{category.replace('_', ' ').title()} spend",
                    "metric_value": metric_value,
                },
                "supporting_transaction_ids": supporting_ids,
                "severity_score": round(min(1.0, share), 4),
            })

        # 2) Merchant frequency / subscription-like creep (many txs)
        sorted_merchants = sorted(
            merchant_totals.items(),
            key=lambda kv: (kv[1]["count"], kv[1]["total"]),
            reverse=True,
        )
        for merchant, data in sorted_merchants[:10]:
            if data["count"] < 4:
                continue
            share = float(data["total"] / total_expenses) if total_expenses > 0 else 0.0
            txs_sorted = sorted(
                data["txs"],
                key=lambda t: Decimal(str(t.get("amount", "0"))),
                reverse=True,
            )
            supporting_ids = [str(t.get("id")) for t in txs_sorted[:3] if t.get("id")]
            candidate_key = f"merchant_frequency:{self._normalize_key(merchant)}"
            metric_value = (
                f"{data['count']} txs totaling {format_money(data['total'], file_currency)}"
                if file_currency != "MULTI"
                else f"{data['count']} txs totaling {data['total']:,.2f} (MULTI)"
            )
            severity = (min(1.0, (data["count"] / 12.0) * 0.6 + share * 0.4))
            candidates.append({
                "candidate_type": "merchant_frequency",
                "key": candidate_key,
                "metrics": {
                    "merchant": merchant,
                    "merchant_total": float(data["total"]),
                    "share_of_expenses": round(share, 4),
                    "count": int(data["count"]),
                    "metric_label": f"{merchant} spend frequency",
                    "metric_value": metric_value,
                },
                "supporting_transaction_ids": supporting_ids,
                "severity_score": round(severity, 4),
            })

        # 3) Outlier spikes: largest individual debits
        if expense_amounts:
            median_expense = sorted(expense_amounts)[len(expense_amounts) // 2]
            all_debits = [
                tx for tx in transactions
                if tx.get("transaction_type", "debit") != "credit"
            ]
            largest = sorted(
                all_debits,
                key=lambda t: Decimal(str(t.get("amount", "0"))),
                reverse=True,
            )[:5]
            for tx in largest:
                amt = Decimal(str(tx.get("amount", "0")))
                if median_expense > 0 and amt < median_expense * Decimal("3"):
                    continue
                tx_id = tx.get("id")
                if not tx_id:
                    continue
                ratio = float(amt / median_expense) if median_expense > 0 else 0.0
                share = float(amt / total_expenses) if total_expenses > 0 else 0.0
                candidate_key = f"outlier_spike:{tx_id}"
                metric_value = (
                    f"{format_money(amt, file_currency)} ({self._pct(amt, total_expenses):.0f}% of expenses)"
                    if file_currency != "MULTI"
                    else f"{amt:,.2f} (MULTI)"
                )
                candidates.append({
                    "candidate_type": "outlier_spike",
                    "key": candidate_key,
                    "metrics": {
                        "transaction_id": str(tx_id),
                        "amount": float(amt),
                        "outlier_ratio_vs_median": round(ratio, 2),
                        "share_of_expenses": round(share, 4),
                        "metric_label": "Largest transaction",
                        "metric_value": metric_value,
                    },
                    "supporting_transaction_ids": [str(tx_id)],
                    "severity_score": round(min(1.0, share * 2 + min(0.5, ratio / 10)), 4),
                })

        # Convert Decimals to floats for JSON serialization
        aggregated = {
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_flow": float(total_income - total_expenses),
            "category_breakdown": {
                k: {"total": float(v["total"]), "count": v["count"]}
                for k, v in category_totals.items()
            },
            "top_merchants": sorted(
                [{"name": k, "total": float(v["total"]), "count": v["count"]} 
                 for k, v in merchant_totals.items()],
                key=lambda x: x["total"],
                reverse=True
            )[:10],
            "weekday_spending": {
                k: {"total": float(v["total"]), "count": v["count"], 
                    "average": float(v["total"] / v["count"]) if v["count"] > 0 else 0}
                for k, v in weekday_spending.items()
            },
            "transaction_count": len(transactions),
            "time_range": effective_time_range,
            "observed_time_range": observed_time_range,
            "file_currency": file_currency,
        }

        state["aggregated_data"] = aggregated
        state["file_currency"] = file_currency
        state["observed_time_range"] = observed_time_range
        state["time_range"] = effective_time_range
        state["candidates"] = sorted(candidates, key=lambda c: c.get("severity_score", 0), reverse=True)
        return state

    def _generate_alerts(self, state: AgentState) -> AgentState:
        """Generate alerts for unusual spending or budget concerns."""
        aggregated = state.get("aggregated_data", {})
        file_currency = state.get("file_currency") or aggregated.get("file_currency") or "MYR"
        
        if not aggregated:
            state["alerts"] = []
            return state

        alerts = []
        
        # Check for negative cash flow
        net_flow = aggregated.get("net_flow", 0)
        if net_flow < 0:
            alerts.append({
                "title": "Negative Cash Flow",
                "description": (
                    f"Expenses exceeded income by {format_money(abs(net_flow), file_currency)} in this period"
                    if file_currency != "MULTI"
                    else "Expenses exceeded income in this period (multi-currency)"
                ),
                "severity": "critical",
                "icon": "TriangleAlert",
                "metric": {"label": "Net cash flow", "value": format_money(net_flow, file_currency) if file_currency != "MULTI" else "MULTI"},
                "supporting_transaction_ids": [],
            })

        # Check for high spending categories
        category_breakdown = aggregated.get("category_breakdown", {})
        total_expenses = aggregated.get("total_expenses", 1)
        
        for category, data in category_breakdown.items():
            percentage = (data["total"] / total_expenses * 100) if total_expenses > 0 else 0
            if percentage > 40 and category not in ["income", "housing"]:
                alerts.append({
                    "title": f"High {category.replace('_', ' ').title()} Spending",
                    "description": f"{category.replace('_', ' ').title()} accounts for {percentage:.0f}% of your expenses",
                    "severity": "warning",
                    "icon": "TriangleAlert",
                    "metric": {"label": "Share of expenses", "value": f"{percentage:.0f}%"},
                    "supporting_transaction_ids": [],
                })

        state["alerts"] = alerts[:2]  # MVP: limit to 2 alerts
        return state

    def _finalize_insights(self, state: AgentState) -> AgentState:
        """Use LLM to select + phrase final insights from deterministic candidates.

        Output shape is validated later by the post-processing layer.
        """
        import json

        candidates = state.get("candidates", []) or []
        alerts = state.get("alerts", []) or []
        file_currency = state.get("file_currency") or "MYR"
        time_range = state.get("time_range") or {"start": None, "end": None}

        # Pre-truncate candidates to keep the prompt small-model friendly
        top_candidates = candidates[:6]

        schema = INSIGHTS_LLM_OUTPUT_JSON_SCHEMA
        system_prompt = INSIGHTS_SYSTEM_PROMPT

        user_prompt = {
            "file_currency": file_currency,
            "time_range": time_range,
            "format_rules": {
                "currency": "Never use '$'. Use currency code formatting like 'MYR 5,659.68'.",
                "detail": "Exactly 1 sentence, <= 140 chars.",
                "spending_limit": "spending_insights length must be 0-3.",
                "alerts_limit": "alerts length must be 0-2.",
                "recommendations_limit": "recommendations length must be 0-3.",
                "evidence": "Copy supporting_transaction_ids from candidates; never create new IDs.",
            },
            "candidates": top_candidates,
            "alerts_candidates": alerts,
            "json_schema": schema,
        }

        candidate_by_key = {str(c.get("key")): c for c in top_candidates if c.get("key")}

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=json.dumps(user_prompt, ensure_ascii=False)),
            ])
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            result = json.loads(content.strip())
        except Exception as e:
            # Hard fallback: deterministically pick up to 3 candidate titles, no recommendations
            print(f"Error finalizing insights: {e}")
            spending = []
            for c in top_candidates[:3]:
                metrics = c.get("metrics", {}) or {}
                spending.append({
                    "title": (metrics.get("metric_label") or "Spending insight")[:52],
                    "detail": (metrics.get("metric_value") or "See statement details.")[:140],
                    "severity": "warning",
                    "metric": {"label": metrics.get("metric_label", "Metric"), "value": str(metrics.get("metric_value", ""))},
                    "supporting_transaction_ids": c.get("supporting_transaction_ids", [])[:3],
                    "source_candidate_key": c.get("key", ""),
                })
            result = {"spending_insights": spending, "alerts": [], "recommendations": []}

        result = self._validate_and_fix_output(
            llm_output=result,
            candidate_by_key=candidate_by_key,
            file_currency=file_currency,
        )

        state["patterns"] = result.get("spending_insights", []) or []
        state["alerts"] = result.get("alerts", []) or []
        state["recommendations"] = result.get("recommendations", []) or []
        return state

    def _validate_and_fix_output(
        self,
        *,
        llm_output: Any,
        candidate_by_key: Dict[str, Dict[str, Any]],
        file_currency: str,
    ) -> Dict[str, Any]:
        """Deterministically enforce constraints on LLM output.

        Notes:
        - We prefer fixing over dropping, but we never invent IDs or numbers.
        - Currency: never allow '$' in any output fields.
        """
        def ensure_list(value: Any) -> List[Any]:
            return value if isinstance(value, list) else []

        def scrub_dollar(s: Any) -> str:
            if not isinstance(s, str):
                s = "" if s is None else str(s)
            if "$" not in s:
                return s
            if file_currency and file_currency != "MULTI":
                # Replace "$123.45" / "$ 123.45" with "MYR 123.45"
                s = re.sub(r"\$\s*", f"{file_currency} ", s)
            else:
                # Multi-currency: remove $ symbol only (avoid incorrect mapping)
                s = s.replace("$", "")
            return s

        def clamp_str(s: Any, max_len: int) -> str:
            s2 = scrub_dollar(s).strip()
            if len(s2) <= max_len:
                return s2
            return s2[: max_len - 1].rstrip() + "…"

        def severity_rank(sev: str) -> int:
            normalized = self._normalize_severity(sev) or ""
            return {"critical": 0, "warning": 1, "info": 2}.get(normalized, 3)

        output: Dict[str, Any] = llm_output if isinstance(llm_output, dict) else {}
        spending = ensure_list(output.get("spending_insights"))
        alerts = ensure_list(output.get("alerts"))
        recs = ensure_list(output.get("recommendations"))

        fixed_spending: List[Dict[str, Any]] = []
        for item in spending:
            if not isinstance(item, dict):
                continue
            key = item.get("source_candidate_key")
            if not isinstance(key, str) or not key:
                continue

            candidate = candidate_by_key.get(key)
            if candidate is None:
                continue

            supporting_ids = item.get("supporting_transaction_ids")
            if not isinstance(supporting_ids, list) or len(supporting_ids) == 0:
                supporting_ids = candidate.get("supporting_transaction_ids", [])
            supporting_ids = [str(x) for x in supporting_ids if x]
            supporting_ids = supporting_ids[:3]
            if not supporting_ids:
                # Must have evidence for spending insights
                continue

            metric = item.get("metric") if isinstance(item.get("metric"), dict) else {}
            metric_label = clamp_str(metric.get("label", ""), 64)
            metric_value = clamp_str(metric.get("value", ""), 64)
            if not metric_label or not metric_value:
                # Fallback to deterministic metric label/value from candidate
                c_metrics = candidate.get("metrics", {}) or {}
                metric_label = metric_label or clamp_str(c_metrics.get("metric_label", "Metric"), 64)
                metric_value = metric_value or clamp_str(c_metrics.get("metric_value", ""), 64)

            fixed_spending.append({
                "title": clamp_str(item.get("title", ""), 52) or clamp_str(metric_label, 52) or "Spending insight",
                "detail": clamp_str(item.get("detail", ""), 140) or clamp_str(metric_value, 140) or "See statement details.",
                "severity": self._normalize_severity(item.get("severity")) or "warning",
                "metric": {"label": metric_label, "value": metric_value},
                "supporting_transaction_ids": supporting_ids,
                "source_candidate_key": key,
            })

        # Sort then truncate to max 3
        fixed_spending.sort(
            key=lambda x: (
                severity_rank(x.get("severity", "")),
                -float(candidate_by_key.get(x.get("source_candidate_key", ""), {}).get("severity_score", 0)),
            )
        )
        fixed_spending = fixed_spending[:3]

        fixed_alerts: List[Dict[str, Any]] = []
        for item in alerts:
            if not isinstance(item, dict):
                continue
            metric = item.get("metric") if isinstance(item.get("metric"), dict) else {"label": "", "value": ""}
            fixed_alerts.append({
                "title": clamp_str(item.get("title", ""), 52) or "Alert",
                "detail": clamp_str(item.get("detail", item.get("description", "")), 140),
                "severity": self._normalize_severity(item.get("severity")) or "warning",
                "metric": {"label": clamp_str(metric.get("label", ""), 64), "value": clamp_str(metric.get("value", ""), 64)},
                "supporting_transaction_ids": [str(x) for x in ensure_list(item.get("supporting_transaction_ids")) if x][:3],
            })
        fixed_alerts = fixed_alerts[:2]

        valid_titles = {i.get("title") for i in fixed_spending} | {a.get("title") for a in fixed_alerts}
        fixed_recs: List[Dict[str, Any]] = []
        for item in recs:
            if not isinstance(item, dict):
                continue
            linked = item.get("linked_to_title")
            if linked not in valid_titles:
                continue
            fixed_recs.append({
                "title": clamp_str(item.get("title", ""), 52) or "Recommendation",
                "detail": clamp_str(item.get("detail", item.get("description", "")), 140),
                "linked_to_title": linked,
            })
        fixed_recs = fixed_recs[:3]

        return {
            "spending_insights": fixed_spending,
            "alerts": fixed_alerts,
            "recommendations": fixed_recs,
        }

    def _save_insights(self, state: AgentState) -> AgentState:
        """Save all generated insights to the database."""
        user_id = state["user_id"]
        file_id = state.get("file_id")
        file_currency = state.get("file_currency") or "MYR"
        time_range = state.get("time_range") or {"start": None, "end": None}
        observed_time_range = state.get("observed_time_range") or {"start": None, "end": None}
        
        insights = []
        
        # Convert spending insights to 'pattern'
        for pattern in state.get("patterns", []):
            metric = pattern.get("metric") or {}
            insight = FinancialInsight(
                id=str(uuid.uuid4()),
                user_id=user_id,
                file_id=file_id,
                insight_type="pattern",
                title=pattern.get("title", "Spending Pattern"),
                description=pattern.get("detail", pattern.get("description", "")),
                icon="ChartBar",
                severity=self._normalize_severity(pattern.get("severity")),
                insight_metadata={
                    "source": "ai_analysis",
                    "time_range": time_range,
                    "observed_time_range": observed_time_range,
                    "file_currency": file_currency,
                    "metric": metric,
                    "supporting_transaction_ids": pattern.get("supporting_transaction_ids", []),
                    "source_candidate_key": pattern.get("source_candidate_key"),
                    "model": getattr(self.llm, "model_name", "unknown"),
                },
            )
            insights.append(insight)

        # Convert alerts to insights
        for alert in state.get("alerts", []):
            metric = alert.get("metric") or {}
            insight = FinancialInsight(
                id=str(uuid.uuid4()),
                user_id=user_id,
                file_id=file_id,
                insight_type="alert",
                title=alert.get("title", "Alert"),
                description=alert.get("detail", alert.get("description", "")),
                icon="TriangleAlert",
                severity=self._normalize_severity(alert.get("severity")) or "info",
                insight_metadata={
                    "source": "ai_analysis",
                    "time_range": time_range,
                    "observed_time_range": observed_time_range,
                    "file_currency": file_currency,
                    "metric": metric,
                    "supporting_transaction_ids": alert.get("supporting_transaction_ids", []),
                    "model": getattr(self.llm, "model_name", "unknown"),
                },
            )
            insights.append(insight)

        # Convert recommendations to insights
        for rec in state.get("recommendations", []):
            insight = FinancialInsight(
                id=str(uuid.uuid4()),
                user_id=user_id,
                file_id=file_id,
                insight_type="recommendation",
                title=rec.get("title", "Recommendation"),
                description=rec.get("detail", rec.get("description", "")),
                icon="Sparkles",
                severity=None,
                insight_metadata={
                    "source": "ai_analysis",
                    "time_range": time_range,
                    "observed_time_range": observed_time_range,
                    "file_currency": file_currency,
                    "linked_to_title": rec.get("linked_to_title"),
                    "model": getattr(self.llm, "model_name", "unknown"),
                },
            )
            insights.append(insight)

        # Delete existing insights for this file (if file_id provided) or user
        if file_id:
            # Statement mode: replace insights for that statement/file only.
            database_service.delete_user_ai_insights(user_id=user_id, file_id=file_id)
        else:
            # Range mode: replace prior AI insights for the user (Option C).
            database_service.delete_user_ai_insights(user_id=user_id, file_id=None)
        
        # Save new insights
        if insights:
            database_service.create_financial_insights_bulk(insights)

        state["insights"] = insights
        return state

    def analyze(
        self,
        user_id: int,
        file_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transactions: Optional[List[BankingTransaction]] = None,
    ) -> List[FinancialInsight]:
        """Run the transaction analysis pipeline.

        Args:
            user_id: The user ID to analyze transactions for
            file_id: Optional file ID to filter transactions
            start_date: Optional start date (inclusive) to filter transactions
            end_date: Optional end date (inclusive) to filter transactions
            transactions: Optional pre-loaded transactions (if None, will fetch from DB)

        Returns:
            List[FinancialInsight]: Generated insights
        """
        # Fetch transactions if not provided
        if transactions is None:
            transactions = database_service.filter_banking_transactions(
                user_id=user_id,
                file_id=file_id,
                start_date=start_date,
                end_date=end_date,
                limit=500,  # Limit for performance
                order_desc=True,
            )

        # Convert transactions to dictionaries
        tx_dicts = []
        for tx in transactions:
            tx_dict = {
                "id": tx.id,
                "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
                "description": tx.description,
                "merchant_name": tx.merchant_name,
                "amount": str(tx.amount),
                "transaction_type": tx.transaction_type,
                "category": tx.category,
                "currency": tx.currency,
            }
            tx_dicts.append(tx_dict)

        # Initialize state
        requested_time_range = {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        }
        initial_state: AgentState = {
            "user_id": user_id,
            "file_id": file_id,
            "transactions": tx_dicts,
            "aggregated_data": {},
            "file_currency": "MYR",
            "patterns": [],
            "alerts": [],
            "recommendations": [],
            "time_range": requested_time_range,
            "observed_time_range": {"start": None, "end": None},
            "candidates": [],
            "insights": [],
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return final_state.get("insights", [])

    # Helper methods for formatting
    def _format_category_breakdown(self, breakdown: Dict, currency: str = "MYR") -> str:
        if not breakdown:
            return "No category data available"
        lines = []
        for cat, data in sorted(breakdown.items(), key=lambda x: x[1]["total"], reverse=True):
            lines.append(
                f"- {cat.replace('_', ' ').title()}: {format_money(data['total'], currency)} ({data['count']} transactions)"
            )
        return "\n".join(lines[:8])

    def _format_top_merchants(self, merchants: List[Dict], currency: str = "MYR") -> str:
        if not merchants:
            return "No merchant data available"
        lines = []
        for m in merchants[:5]:
            lines.append(f"- {m['name']}: {format_money(m['total'], currency)} ({m['count']} transactions)")
        return "\n".join(lines)

    def _format_weekday_spending(self, weekday_data: Dict, currency: str = "MYR") -> str:
        if not weekday_data:
            return "No weekday data available"
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        lines = []
        for day in days_order:
            if day in weekday_data:
                data = weekday_data[day]
                lines.append(
                    f"- {day}: {format_money(data['total'], currency)} avg ({format_money(data['average'], currency)}/transaction)"
                )
        return "\n".join(lines)

    def _generate_fallback_patterns(self, aggregated: Dict) -> List[Dict]:
        """Generate basic patterns without LLM."""
        patterns = []
        currency = aggregated.get("file_currency") or "MYR"
        
        category_breakdown = aggregated.get("category_breakdown", {})
        if "food_and_dining_out" in category_breakdown:
            data = category_breakdown["food_and_dining_out"]
            if data["count"] > 3:
                patterns.append({
                    "title": "Dining Out Habit",
                    "description": f"You've spent {format_money(data['total'], currency)} on dining out across {data['count']} transactions",
                    "icon": "Utensils"
                })

        weekday_spending = aggregated.get("weekday_spending", {})
        weekend_total = sum(
            weekday_spending.get(day, {}).get("total", 0) 
            for day in ["Saturday", "Sunday"]
        )
        weekday_total = sum(
            weekday_spending.get(day, {}).get("total", 0) 
            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        )
        
        if weekend_total > weekday_total * 0.5:
            patterns.append({
                "title": "Weekend Spender",
                "description": "Your weekend spending is significant compared to weekdays",
                "icon": "Calendar"
            })

        return patterns

    def _generate_fallback_recommendations(self, aggregated: Dict) -> List[Dict]:
        """Generate basic recommendations without LLM."""
        recommendations = []
        currency = aggregated.get("file_currency") or "MYR"
        
        net_flow = aggregated.get("net_flow", 0)
        if net_flow < 0:
            recommendations.append({
                "title": "Track Your Spending",
                "description": "Consider setting a monthly budget to bring expenses in line with income",
                "icon": "Target"
            })
        else:
            recommendations.append({
                "title": "Build Emergency Fund",
                "description": f"You have positive cash flow of {format_money(net_flow, currency)}. Consider saving a portion automatically",
                "icon": "PiggyBank"
            })

        return recommendations


# Singleton instance
transaction_analyzer = TransactionAnalyzerAgent()
