"""Validation model for user settings (nested keys)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

NonNeg = Field(ge=0)


class PlatformCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = "Custom"
    final_value_fee_pct: float = Field(0, ge=0, le=100)
    per_order_fee: float = Field(0, ge=0)
    payment_processing_pct: float = Field(0, ge=0, le=100)
    payment_processing_fixed: float = Field(0, ge=0)
    listing_fee: float = Field(0, ge=0)
    seller_pays_shipping: bool = True
    note: str = ""


class AcquisitionCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    buyer_premium_pct: float = Field(0, ge=0, le=100)
    sales_tax_pct: float = Field(0, ge=0, le=100)
    default_incoming_shipping: float | None = Field(None, ge=0)
    default_handling_fee: float | None = Field(None, ge=0)
    bid_increment: float = Field(1.0, gt=0)


class ResaleCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clothing_outgoing_shipping: float = Field(9.5, ge=0)
    jewelry_outgoing_shipping: float = Field(5.0, ge=0)
    packaging_cost: float = Field(1.0, ge=0)
    default_cleaning_cost: float = Field(0, ge=0)
    holding_cost_per_month: float = Field(0, ge=0)


class ThresholdsCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_profit_usd: float = Field(25, ge=0)
    min_roi_pct: float = Field(50, ge=0)
    max_capital_at_risk_usd: float | None = Field(250, ge=0)


class RiskCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_weights_by_evidence: dict[str, list[float]]
    identification_confidence_haircut: float = Field(0.5, ge=0, le=1)
    estimated_months_to_sell: dict[str, float]

    @field_validator("scenario_weights_by_evidence")
    @classmethod
    def _w(cls, v):
        for k, w in v.items():
            if len(w) != 3 or any(x < 0 for x in w) or abs(sum(w) - 1) > 0.01:
                raise ValueError(f"scenario weights for '{k}' must be three non-negative numbers summing to 1")
        return v


class RankingCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weights: dict[str, float]
    profit_reference_usd: float = Field(100, gt=0)
    roi_reference_pct: float = Field(100, gt=0)
    feedback_adjustments: dict[str, float]

    @field_validator("weights")
    @classmethod
    def _w(cls, v):
        if any(x < 0 for x in v.values()) or sum(v.values()) <= 0:
            raise ValueError("ranking weights must be non-negative and not all zero")
        return v


class AnalysisCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    auto_escalate_min_triage_interest: int = Field(55, ge=0, le=100)
    exclude_keywords: list[str]
    boost_keywords: list[str]
    min_current_bid: float = Field(0, ge=0)
    max_current_bid: float | None = Field(500, ge=0)


class NotificationsCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reminder_minutes_before_end: int = Field(30, ge=0)
    enable_console_reminders: bool = True


class SettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    platforms: dict[str, PlatformCfg]
    default_platform: str
    acquisition: AcquisitionCfg
    resale: ResaleCfg
    thresholds: ThresholdsCfg
    risk: RiskCfg
    ranking: RankingCfg
    analysis: AnalysisCfg
    notifications: NotificationsCfg
    model_pricing_usd_per_1m: dict[str, list[float]]

    @field_validator("model_pricing_usd_per_1m")
    @classmethod
    def _p(cls, v):
        for k, pr in v.items():
            if len(pr) != 2 or any(x < 0 for x in pr):
                raise ValueError(f"pricing for '{k}' must be [input, output] >= 0")
        return v

    def check(self) -> None:
        if self.default_platform not in self.platforms:
            raise ValueError(f"default_platform '{self.default_platform}' is not a configured platform")
