"""Typed finance overrides / per-listing assumptions (validated before reaching the calculator)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FinanceOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str | None = None
    buyer_premium_pct: float | None = Field(default=None, ge=0, le=100)
    sales_tax_pct: float | None = Field(default=None, ge=0, le=100)
    incoming_shipping: float | None = Field(default=None, ge=0)
    handling_fee: float | None = Field(default=None, ge=0)
    outgoing_shipping: float | None = Field(default=None, ge=0)
    packaging_cost: float | None = Field(default=None, ge=0)
    cleaning_repair_cost: float | None = Field(default=None, ge=0)
    other_acquisition_costs: dict[str, float] | None = None
    other_resale_costs: dict[str, float] | None = None
    min_profit_usd: float | None = Field(default=None, ge=0)
    min_roi_pct: float | None = Field(default=None, ge=0)
    max_capital_at_risk_usd: float | None = Field(default=None, ge=0)

    @field_validator("other_acquisition_costs", "other_resale_costs")
    @classmethod
    def _nonneg(cls, v):
        if v:
            for k, x in v.items():
                if x < 0:
                    raise ValueError(f"cost '{k}' must be >= 0")
        return v


def validate_overrides(raw: dict | None) -> dict:
    """Return a cleaned dict (unset keys removed). Raises ValueError on bad input."""
    if not raw:
        return {}
    try:
        return FinanceOverrides.model_validate(raw).model_dump(exclude_none=True)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"invalid finance overrides: {e}") from e
