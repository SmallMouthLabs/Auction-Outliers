"""Transparent opportunity ranking.

All weights are CONFIGURABLE HEURISTICS (Settings > ranking). Components are reported individually so the
score can be audited. Nothing here is a calibrated probability.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

TIERS = ("HIGH_CONFIDENCE", "SPECULATIVE_HIGH_UPSIDE", "NEEDS_RESEARCH", "LOW_VALUE")


@dataclass
class RankInputs:
    expected_profit: float | None
    optimistic_profit: float | None
    risk_adjusted_profit: float | None
    roi_pct: float | None
    identification_confidence: float | None  # 0..1 model-reported
    evidence_quality: str  # high|medium|low|none
    demand: str | None  # high|medium|low (from reference db / model indicator)
    liquidity: str | None
    num_bids: int | None
    risk_flags: int  # count of authenticity/condition concerns
    misidentification_signal: float | None  # 0..1 from discrepancy detection
    ends_at: datetime | None
    warrants_research: bool
    has_valuation: bool
    finance_complete: bool
    feedback_labels: list[str]
    status: str = "active"


def _sat(x: float | None, ref: float) -> float:
    """0..1 saturating transform; ref => ~0.63; negative => 0."""
    if x is None or x <= 0:
        return 0.0
    return 1.0 - math.exp(-x / ref)


LEVEL = {"high": 1.0, "medium": 0.6, "low": 0.3, "none": 0.0, None: 0.5}


def score(inp: RankInputs, cfg: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    w = cfg["weights"]
    comps: dict[str, float] = {}
    comps["expected_profit"] = _sat(inp.expected_profit, cfg["profit_reference_usd"])
    comps["risk_adjusted_profit"] = _sat(inp.risk_adjusted_profit, cfg["profit_reference_usd"])
    comps["roi"] = _sat(inp.roi_pct, cfg["roi_reference_pct"])
    comps["identification_confidence"] = inp.identification_confidence if inp.identification_confidence is not None else 0.3
    comps["evidence_quality"] = LEVEL.get(inp.evidence_quality, 0.0)
    comps["sell_likelihood"] = (LEVEL.get(inp.demand, 0.5) + LEVEL.get(inp.liquidity, 0.5)) / 2
    comps["time_to_sell"] = LEVEL.get(inp.liquidity, 0.5)
    nb = inp.num_bids or 0
    comps["competition"] = 1.0 / (1.0 + nb / 5.0)  # many bids => price discovery already happening
    comps["risk_flags"] = max(0.0, 1.0 - 0.25 * inp.risk_flags)
    comps["misidentification_signal"] = inp.misidentification_signal or 0.0

    base = sum(w[k] * comps[k] for k in w if k in comps)
    total_w = sum(w[k] for k in w if k in comps) or 1.0
    s = base / total_w

    # time remaining: items that have ended are not opportunities; items ending very soon get a nudge
    time_factor = 1.0
    hours_left = None
    if inp.ends_at is not None:
        ea = inp.ends_at if inp.ends_at.tzinfo else inp.ends_at.replace(tzinfo=UTC)
        hours_left = (ea - now).total_seconds() / 3600.0
        if hours_left <= 0:
            time_factor = 0.0
        elif hours_left < 6:
            time_factor = 1.05
    if inp.status == "ended":
        time_factor = 0.0

    adj = 0.0
    for label in inp.feedback_labels:
        adj += cfg.get("feedback_adjustments", {}).get(label, 0.0)
    final = max(0.0, min(1.0, (s + adj) * time_factor))

    tier = classify_tier(inp, cfg)
    if time_factor == 0.0:
        tier = "LOW_VALUE"
    return {
        "score": round(final * 100, 1),
        "tier": tier,
        "components": {k: round(v, 3) for k, v in comps.items()},
        "weights": w,
        "time_factor": time_factor,
        "hours_left": None if hours_left is None else round(hours_left, 1),
        "feedback_adjustment": adj,
        "label": "heuristic weights, uncalibrated",
    }


def classify_tier(inp: RankInputs, cfg: dict[str, Any]) -> str:
    thr = cfg.get("thresholds", {})
    min_profit = thr.get("min_profit_usd", 25.0)
    min_roi = thr.get("min_roi_pct", 50.0)
    conf = inp.identification_confidence or 0.0
    if not inp.has_valuation:
        return "NEEDS_RESEARCH" if (inp.warrants_research or conf >= 0.4) else "LOW_VALUE"
    econ_ok = (inp.expected_profit or 0) >= min_profit and (inp.roi_pct or 0) >= min_roi
    if econ_ok and inp.evidence_quality in ("high", "medium") and conf >= 0.65 and inp.risk_flags <= 1:
        return "HIGH_CONFIDENCE"
    if (inp.optimistic_profit or 0) >= max(2 * min_profit, 75.0) and (
        inp.evidence_quality in ("low", "none") or conf < 0.65 or inp.risk_flags > 1
    ):
        return "SPECULATIVE_HIGH_UPSIDE"
    if econ_ok:
        return "HIGH_CONFIDENCE" if inp.evidence_quality == "high" else "SPECULATIVE_HIGH_UPSIDE"
    if inp.warrants_research and (inp.expected_profit or 0) > 0:
        return "NEEDS_RESEARCH"
    return "LOW_VALUE"
