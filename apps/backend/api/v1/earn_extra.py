"""Earn extra plan endpoints for managing micro-plans."""

from decimal import Decimal
from typing import List, Optional, Literal, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.models.earn_extra_plan import EarnExtraPlan
from backend.services.ai_agent.earn_extra_generator import generate_earn_extra_plans
from backend.services.db.postgres_connector import database_service

router = APIRouter()

PlanStatus = Literal["generated", "active", "completed", "archived"]
ActionType = Literal["cut_spend", "shift_spend", "increase_income", "one_time_cleanup"]


class PlanAction(BaseModel):
    label: str
    type: ActionType
    weekly_frequency: Optional[int] = None
    estimated_value: Optional[Decimal] = None


class PlanProgressItem(BaseModel):
    is_done: bool = False
    notes: Optional[str] = None


class EarnExtraPlanResponse(BaseModel):
    id: str
    user_id: int
    file_id: Optional[str] = None
    status: PlanStatus
    target_amount: Decimal
    currency: str
    timeframe_days: int
    title: str
    summary: str
    actions: List[PlanAction]
    expected_amount: Optional[Decimal] = None
    confidence: Optional[str] = None
    saved_so_far: Decimal
    actions_progress: List[PlanProgressItem]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class EarnExtraGenerateRequest(BaseModel):
    file_id: Optional[str] = None
    target_amount: Optional[Decimal] = Field(default=Decimal("500.00"), ge=0)
    timeframe_days: Optional[int] = Field(default=30, ge=1, le=365)


class EarnExtraPlanUpdateRequest(BaseModel):
    saved_so_far: Optional[Decimal] = Field(default=None, ge=0)
    actions_progress: Optional[List[PlanProgressItem]] = None

    @field_validator("actions_progress")
    @classmethod
    def validate_progress_length(cls, value: Optional[List[PlanProgressItem]]):
        if value is None:
            return value
        if len(value) != 3:
            raise ValueError("actions_progress must have exactly 3 items")
        return value


def _normalize_actions_progress(raw: Optional[List[Dict[str, Any]]]) -> List[PlanProgressItem]:
    if not raw:
        return [PlanProgressItem(), PlanProgressItem(), PlanProgressItem()]
    items = [PlanProgressItem(**item) for item in raw]
    if len(items) != 3:
        # pad or truncate to 3 for safety
        items = (items + [PlanProgressItem(), PlanProgressItem(), PlanProgressItem()])[:3]
    return items


def _normalize_actions(raw: Optional[List[Dict[str, Any]]]) -> List[PlanAction]:
    if not raw:
        return []
    normalized: List[PlanAction] = []
    for item in raw:
        if isinstance(item, str):
            normalized.append(PlanAction(label=item, type="cut_spend"))
            continue
        if not isinstance(item, dict):
            continue

        label = item.get("label") or item.get("action") or item.get("description")
        if not label:
            steps = item.get("steps")
            if isinstance(steps, list) and steps:
                label = str(steps[0])
        action_type = item.get("type") or "cut_spend"

        normalized.append(
            PlanAction(
                label=str(label or "Action"),
                type=action_type,
                weekly_frequency=item.get("weekly_frequency"),
                estimated_value=item.get("estimated_value") or item.get("estimated_savings"),
            )
        )

    return normalized


def _to_response(plan: EarnExtraPlan) -> EarnExtraPlanResponse:
    return EarnExtraPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        file_id=plan.file_id,
        status=plan.status,
        target_amount=plan.target_amount,
        currency=plan.currency,
        timeframe_days=plan.timeframe_days,
        title=plan.title,
        summary=plan.summary,
        actions=_normalize_actions(plan.actions),
        expected_amount=plan.expected_amount,
        confidence=plan.confidence,
        saved_so_far=plan.saved_so_far,
        actions_progress=_normalize_actions_progress(plan.actions_progress),
        created_at=plan.created_at.isoformat() if plan.created_at else None,
        updated_at=plan.updated_at.isoformat() if plan.updated_at else None,
    )


@router.post("/plans/generate", response_model=List[EarnExtraPlanResponse], tags=["Earn Extra"])
async def generate_plans(
    payload: EarnExtraGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> List[EarnExtraPlanResponse]:
    user_id = current_user.id

    plans = await generate_earn_extra_plans(
        user_id=user_id,
        file_id=payload.file_id,
        target_amount=payload.target_amount or Decimal("500.00"),
        timeframe_days=payload.timeframe_days or 30,
    )

    return [_to_response(plan) for plan in plans]


@router.get("/plans", response_model=List[EarnExtraPlanResponse], tags=["Earn Extra"])
async def list_plans(
    current_user: User = Depends(get_current_user),
    status: Optional[PlanStatus] = Query(default=None),
    limit: Optional[int] = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="updated_at"),
    order_desc: bool = Query(default=True),
) -> List[EarnExtraPlanResponse]:
    user_id = current_user.id
    plans = database_service.get_user_earn_extra_plans(
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_desc=order_desc,
    )
    return [_to_response(plan) for plan in plans]


@router.post("/plans/{plan_id}/activate", response_model=EarnExtraPlanResponse, tags=["Earn Extra"])
async def activate_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
) -> EarnExtraPlanResponse:
    user_id = current_user.id
    plan = database_service.activate_earn_extra_plan(user_id=user_id, plan_id=plan_id)
    return _to_response(plan)


@router.patch("/plans/{plan_id}", response_model=EarnExtraPlanResponse, tags=["Earn Extra"])
async def update_plan(
    plan_id: str,
    payload: EarnExtraPlanUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> EarnExtraPlanResponse:
    user_id = current_user.id

    if payload.saved_so_far is not None and payload.saved_so_far < 0:
        raise HTTPException(status_code=400, detail="saved_so_far cannot be negative")

    actions_progress = None
    if payload.actions_progress is not None:
        actions_progress = [item.dict() for item in payload.actions_progress]

    plan = database_service.update_earn_extra_plan(
        user_id=user_id,
        plan_id=plan_id,
        saved_so_far=payload.saved_so_far,
        actions_progress=actions_progress,
    )
    return _to_response(plan)


@router.post("/plans/{plan_id}/complete", response_model=EarnExtraPlanResponse, tags=["Earn Extra"])
async def complete_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
) -> EarnExtraPlanResponse:
    user_id = current_user.id
    plan = database_service.complete_earn_extra_plan(user_id=user_id, plan_id=plan_id)
    return _to_response(plan)
