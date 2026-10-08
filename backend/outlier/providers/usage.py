"""API usage tracking and spending limits."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ApiUsage
from .base import BudgetExceeded, ProviderResult


def spent_today(db: Session) -> float:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    v = db.query(func.coalesce(func.sum(ApiUsage.est_cost_usd), 0.0)).filter(ApiUsage.created_at >= start).scalar()
    return float(v or 0.0)


def spent_on_listing(db: Session, listing_id: int) -> float:
    v = db.query(func.coalesce(func.sum(ApiUsage.est_cost_usd), 0.0)).filter(ApiUsage.listing_id == listing_id).scalar()
    return float(v or 0.0)


def check_budget(db: Session, listing_id: int | None, est_next_call_usd: float = 0.05) -> None:
    s = get_settings()
    today = spent_today(db)
    if today + est_next_call_usd > s.daily_budget_usd:
        raise BudgetExceeded(
            f"Daily AI budget reached (${today:.2f} of ${s.daily_budget_usd:.2f}). Raise OUTLIER_DAILY_BUDGET_USD or wait until tomorrow."
        )
    if listing_id is not None:
        per = spent_on_listing(db, listing_id)
        if per + est_next_call_usd > s.per_listing_budget_usd:
            raise BudgetExceeded(
                f"Per-listing AI budget reached (${per:.2f} of ${s.per_listing_budget_usd:.2f}) for listing {listing_id}."
            )


def record_usage(db: Session, *, provider: str, model: str | None, stage: str, listing_id: int | None,
                 result: ProviderResult | None = None, duration_ms: int = 0, error: str | None = None) -> ApiUsage:
    row = ApiUsage(
        provider=provider, model=model, stage=stage, listing_id=listing_id,
        tokens_in=result.tokens_in if result else 0, tokens_out=result.tokens_out if result else 0,
        est_cost_usd=result.est_cost_usd if result else 0.0,
        duration_ms=result.duration_ms if result else duration_ms, success=error is None, error=(error or None) and error[:300],
    )
    db.add(row)
    db.flush()
    return row


def usage_summary(db: Session, days: int = 30) -> dict:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = db.query(
        ApiUsage.provider, ApiUsage.model, ApiUsage.stage,
        func.count(ApiUsage.id), func.sum(ApiUsage.tokens_in), func.sum(ApiUsage.tokens_out),
        func.sum(ApiUsage.est_cost_usd), func.avg(ApiUsage.duration_ms),
        func.sum(func.cast(ApiUsage.success == False, type_=__import__("sqlalchemy").Integer)),
    ).filter(ApiUsage.created_at >= since).group_by(ApiUsage.provider, ApiUsage.model, ApiUsage.stage).all()
    return {
        "days": days,
        "spent_today_usd": round(spent_today(db), 4),
        "daily_budget_usd": get_settings().daily_budget_usd,
        "by_model": [
            {"provider": p, "model": m, "stage": st, "calls": c, "tokens_in": int(ti or 0), "tokens_out": int(to or 0),
             "est_cost_usd": round(float(cost or 0), 4), "avg_duration_ms": int(dur or 0), "errors": int(err or 0)}
            for p, m, st, c, ti, to, cost, dur, err in rows
        ],
    }
