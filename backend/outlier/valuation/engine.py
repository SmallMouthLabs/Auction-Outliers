"""Comparable-sales valuation engine.

NON-NEGOTIABLE RULES (from the spec):
- Only ACTUAL SOLD prices feed the valuation. Active asking prices are reported separately as context
  and never substituted for completed transactions.
- Accepted offers count only when the accepted price is known (price field holds the accepted price).
- If credible sold comparisons are unavailable, the valuation is marked speculative / unsupported.
- No prices are invented.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

COMP_TYPES = ("exact", "same_maker", "category", "active", "unsupported")
EVIDENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
TYPE_WEIGHT = {"exact": 1.0, "same_maker": 0.75, "category": 0.4}


@dataclass
class CompInput:
    id: int | None
    title: str
    price: float | None
    is_sold: bool
    comp_type: str
    similarity: float = 0.5
    evidence_quality: str = "medium"
    sold_date: datetime | None = None
    shipping_included: bool | None = None
    shipping_amount: float | None = None
    marketplace: str = "ebay"
    url: str | None = None
    accepted_offer: bool = False
    differences: str | None = None


@dataclass
class ValuationResult:
    method: str
    conservative: float | None
    expected: float | None
    optimistic: float | None
    is_speculative: bool
    evidence_quality: str  # high|medium|low|none
    n_sold_comps: int
    used_comp_ids: list[int] = field(default_factory=list)
    excluded: list[dict[str, Any]] = field(default_factory=list)
    active_listing_context: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "conservative": self.conservative,
            "expected": self.expected,
            "optimistic": self.optimistic,
            "is_speculative": self.is_speculative,
            "evidence_quality": self.evidence_quality,
            "n_sold_comps": self.n_sold_comps,
            "used_comp_ids": self.used_comp_ids,
            "excluded": self.excluded,
            "active_listing_context": self.active_listing_context,
            "notes": self.notes,
            "stats": self.stats,
        }


def classify_comp(comp: CompInput) -> str:
    """Guard: a comp that is not sold is always 'active', regardless of what was entered."""
    if not comp.is_sold or comp.price is None:
        return "active" if not comp.is_sold else "unsupported"
    if comp.comp_type in ("exact", "same_maker", "category"):
        return comp.comp_type
    return "category"


def _item_price(comp: CompInput) -> float:
    """Price the buyer paid for the item itself (excluding shipping where separable)."""
    p = float(comp.price or 0.0)
    if comp.shipping_included and comp.shipping_amount:
        p = max(p - comp.shipping_amount, 0.0)
    return p


def _recency_weight(sold_date: datetime | None, now: datetime) -> float:
    if sold_date is None:
        return 0.8
    if sold_date.tzinfo is None:
        sold_date = sold_date.replace(tzinfo=UTC)
    days = max((now - sold_date).days, 0)
    # ~1.0 within 90 days, ~0.6 at a year, floor 0.4
    return max(0.4, math.exp(-days / 540.0))


def _weighted_quantile(values: list[float], weights: list[float], q: float) -> float:
    pairs = sorted(zip(values, weights))
    total = sum(weights)
    if total <= 0:
        return statistics.median(values)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc / total >= q:
            return v
    return pairs[-1][0]


def valuate(comps: list[CompInput], now: datetime | None = None) -> ValuationResult:
    now = now or datetime.now(UTC)
    notes: list[str] = []
    excluded: list[dict[str, Any]] = []

    sold: list[CompInput] = []
    active: list[CompInput] = []
    for c in comps:
        t = classify_comp(c)
        if t == "active":
            active.append(c)
        elif t == "unsupported":
            excluded.append({"id": c.id, "title": c.title, "reason": "no transaction price"})
        else:
            c.comp_type = t
            sold.append(c)

    active_ctx: dict[str, Any] = {}
    if active:
        ap = [float(c.price) for c in active if c.price is not None]
        if ap:
            active_ctx = {
                "n": len(ap),
                "min_asking": round(min(ap), 2),
                "median_asking": round(statistics.median(ap), 2),
                "max_asking": round(max(ap), 2),
                "note": "Asking prices only. Not used in the valuation.",
            }

    if not sold:
        notes.append("No sold comparables. Valuation is UNSUPPORTED until sold evidence is entered.")
        return ValuationResult(
            method="unsupported", conservative=None, expected=None, optimistic=None,
            is_speculative=True, evidence_quality="none", n_sold_comps=0, excluded=excluded,
            active_listing_context=active_ctx, notes=notes,
        )

    # Prefer the best tier that has enough evidence; fall back to broader tiers.
    tier_groups = {t: [c for c in sold if c.comp_type == t] for t in ("exact", "same_maker", "category")}
    use: list[CompInput] = []
    tier_used = "category"
    for t in ("exact", "same_maker"):
        if len(tier_groups[t]) >= 2:
            use = tier_groups[t] + (tier_groups["exact"] if t == "same_maker" else [])
            tier_used = t
            break
    if not use:
        # pool everything with type weights when the best tiers are thin
        use = sold
        tier_used = "pooled" if len({c.comp_type for c in sold}) > 1 else sold[0].comp_type
    use = list({id(c): c for c in use}.values())

    prices = [_item_price(c) for c in use]
    weights = [
        max(0.05, c.similarity) * EVIDENCE_WEIGHT.get(c.evidence_quality, 0.5) * TYPE_WEIGHT.get(c.comp_type, 0.4)
        * _recency_weight(c.sold_date, now)
        for c in use
    ]

    # Robust outlier exclusion (only with enough data): drop > 3x or < 1/3 of the median.
    if len(prices) >= 4:
        med = statistics.median(prices)
        keep_idx = [i for i, p in enumerate(prices) if (p <= 3 * med and p >= med / 3)]
        for i, c in enumerate(use):
            if i not in keep_idx:
                excluded.append({"id": c.id, "title": c.title, "reason": f"price outlier vs median ${med:.2f}"})
        use = [use[i] for i in keep_idx]
        prices = [prices[i] for i in keep_idx]
        weights = [weights[i] for i in keep_idx]

    n = len(prices)
    if n >= 3:
        cons = _weighted_quantile(prices, weights, 0.25)
        exp = _weighted_quantile(prices, weights, 0.50)
        opt = _weighted_quantile(prices, weights, 0.75)
    elif n == 2:
        cons, opt = min(prices), max(prices)
        exp = sum(p * w for p, w in zip(prices, weights)) / sum(weights)
        notes.append("Only two sold comparables: range is min/max, not a distribution.")
    else:
        exp = prices[0]
        cons = round(exp * 0.75, 2)
        opt = exp
        notes.append("Single sold comparable: conservative scenario is a 25% haircut (heuristic).")

    # Evidence quality grade (heuristic, transparent)
    avg_sim = sum(c.similarity for c in use) / n
    best_type = min((c.comp_type for c in use), key=lambda t: ["exact", "same_maker", "category"].index(t))
    high_q = sum(1 for c in use if c.evidence_quality == "high")
    if n >= 3 and best_type in ("exact", "same_maker") and avg_sim >= 0.7 and high_q >= 2:
        eq = "high"
    elif n >= 2 and best_type in ("exact", "same_maker") and avg_sim >= 0.5:
        eq = "medium"
    else:
        eq = "low"
    speculative = eq == "low" or tier_used in ("category", "pooled")
    if tier_used == "category":
        notes.append("Only category-level comparables: treat as speculative.")
    spread = (opt - cons) / exp if exp else 0
    if spread > 1.0:
        notes.append("Wide dispersion among comparables; check whether they are truly similar.")

    return ValuationResult(
        method="sold_comps",
        conservative=round(cons, 2), expected=round(exp, 2), optimistic=round(opt, 2),
        is_speculative=speculative, evidence_quality=eq, n_sold_comps=n,
        used_comp_ids=[c.id for c in use if c.id is not None], excluded=excluded,
        active_listing_context=active_ctx, notes=notes,
        stats={
            "tier_used": tier_used,
            "avg_similarity": round(avg_sim, 2),
            "weighted_median": round(exp, 2),
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "spread_ratio": round(spread, 2),
        },
    )
