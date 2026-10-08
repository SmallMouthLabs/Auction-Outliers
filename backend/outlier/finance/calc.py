"""Deterministic profitability & maximum-bid engine.

No AI here. Every number is traceable to an input or an explicitly labeled assumption.
Unknown critical costs are surfaced in `unknown_costs` and `assumed_costs`, never silently zeroed.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PlatformFees:
    name: str = "ebay"
    final_value_fee_pct: float = 13.25
    per_order_fee: float = 0.40
    payment_processing_pct: float = 0.0
    payment_processing_fixed: float = 0.0
    listing_fee: float = 0.0
    seller_pays_shipping: bool = True

    @classmethod
    def from_config(cls, name: str, cfg: dict[str, Any]) -> PlatformFees:
        return cls(
            name=name,
            final_value_fee_pct=float(cfg.get("final_value_fee_pct", 0.0)),
            per_order_fee=float(cfg.get("per_order_fee", 0.0)),
            payment_processing_pct=float(cfg.get("payment_processing_pct", 0.0)),
            payment_processing_fixed=float(cfg.get("payment_processing_fixed", 0.0)),
            listing_fee=float(cfg.get("listing_fee", 0.0)),
            seller_pays_shipping=bool(cfg.get("seller_pays_shipping", True)),
        )


@dataclass
class AcquisitionInputs:
    bid: float
    buyer_premium_pct: float = 0.0
    sales_tax_pct: float = 0.0
    incoming_shipping: float | None = None
    handling_fee: float | None = None
    other_costs: dict[str, float] = field(default_factory=dict)


@dataclass
class ResaleInputs:
    resale_price: float | None
    outgoing_shipping: float | None = None  # cost to ship to the buyer (if seller pays)
    packaging_cost: float = 0.0
    cleaning_repair_cost: float = 0.0
    other_costs: dict[str, float] = field(default_factory=dict)


@dataclass
class Thresholds:
    min_profit_usd: float = 25.0
    min_roi_pct: float = 50.0
    max_capital_at_risk_usd: float | None = 250.0
    bid_increment: float = 1.0


@dataclass
class FinanceResult:
    bid: float
    acquisition_total: float
    acquisition_breakdown: dict[str, float]
    resale_price: float | None
    selling_fees: float | None
    resale_costs: float | None
    net_proceeds: float | None
    profit: float | None
    roi_pct: float | None
    gross_margin_pct: float | None
    net_margin_pct: float | None
    break_even_bid: float | None
    max_bid: float | None
    max_bid_binding_constraint: str | None
    unknown_costs: list[str]
    assumed_costs: dict[str, float]
    complete: bool
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _r(x: float | None) -> float | None:
    return None if x is None else round(x + 1e-9, 2)


def acquisition_cost(a: AcquisitionInputs, assumed: dict[str, float], unknown: list[str]) -> tuple[float, dict[str, float]]:
    premium = a.bid * a.buyer_premium_pct / 100.0
    taxable = a.bid + premium
    tax = taxable * a.sales_tax_pct / 100.0
    incoming = a.incoming_shipping
    if incoming is None:
        if "incoming_shipping" in assumed:
            incoming = assumed["incoming_shipping"]
        else:
            unknown.append("incoming_shipping")
            incoming = 0.0
    handling = a.handling_fee
    if handling is None:
        if "handling_fee" in assumed:
            handling = assumed["handling_fee"]
        else:
            # handling is non-critical; treat unknown as 0 but report it
            unknown.append("handling_fee")
            handling = 0.0
    other = sum(float(v) for v in a.other_costs.values())
    breakdown = {
        "bid": a.bid,
        "buyer_premium": premium,
        "sales_tax": tax,
        "incoming_shipping": incoming,
        "handling_fee": handling,
        "other": other,
    }
    total = sum(breakdown.values())
    return total, {k: _r(v) for k, v in breakdown.items()}


def _acq_linear_coeffs(a: AcquisitionInputs, assumed: dict[str, float]) -> tuple[float, float]:
    """acquisition_total = k * bid + fixed."""
    k = (1 + a.buyer_premium_pct / 100.0) * (1 + a.sales_tax_pct / 100.0)
    incoming = a.incoming_shipping if a.incoming_shipping is not None else assumed.get("incoming_shipping", 0.0)
    handling = a.handling_fee if a.handling_fee is not None else assumed.get("handling_fee", 0.0)
    fixed = incoming + handling + sum(float(v) for v in a.other_costs.values())
    return k, fixed


def selling_fees(resale_price: float, fees: PlatformFees) -> float:
    return (
        resale_price * fees.final_value_fee_pct / 100.0
        + fees.per_order_fee
        + resale_price * fees.payment_processing_pct / 100.0
        + fees.payment_processing_fixed
        + fees.listing_fee
    )


def net_proceeds(r: ResaleInputs, fees: PlatformFees, assumed: dict[str, float], unknown: list[str]) -> tuple[float, float, float] | None:
    if r.resale_price is None:
        return None
    sf = selling_fees(r.resale_price, fees)
    shipping = 0.0
    if fees.seller_pays_shipping:
        if r.outgoing_shipping is not None:
            shipping = r.outgoing_shipping
        elif "outgoing_shipping" in assumed:
            shipping = assumed["outgoing_shipping"]
        else:
            unknown.append("outgoing_shipping")
    costs = shipping + r.packaging_cost + r.cleaning_repair_cost + sum(float(v) for v in r.other_costs.values())
    return r.resale_price - sf - costs, sf, costs


def _floor_to_increment(x: float, inc: float) -> float:
    if inc <= 0:
        return math.floor(x * 100) / 100
    return math.floor(x / inc + 1e-9) * inc


def compute(
    a: AcquisitionInputs,
    r: ResaleInputs,
    fees: PlatformFees,
    thresholds: Thresholds,
    assumed: dict[str, float] | None = None,
) -> FinanceResult:
    """Full deterministic calculation for one bid / one resale scenario.

    `assumed` holds default estimates from Settings for costs the listing does not disclose.
    They are reported back in `assumed_costs` so the UI can show them as assumptions.
    """
    assumed = dict(assumed or {})
    unknown: list[str] = []
    notes: list[str] = []
    acq_total, breakdown = acquisition_cost(a, assumed, unknown)
    used_assumed = {k: v for k, v in assumed.items() if (
        (k == "incoming_shipping" and a.incoming_shipping is None)
        or (k == "handling_fee" and a.handling_fee is None)
        or (k == "outgoing_shipping" and r.outgoing_shipping is None and fees.seller_pays_shipping)
    )}

    np_ = net_proceeds(r, fees, assumed, unknown)
    if np_ is None:
        notes.append("No resale value available: profit, ROI and max bid cannot be computed.")
        return FinanceResult(
            bid=a.bid, acquisition_total=_r(acq_total), acquisition_breakdown=breakdown,
            resale_price=None, selling_fees=None, resale_costs=None, net_proceeds=None,
            profit=None, roi_pct=None, gross_margin_pct=None, net_margin_pct=None,
            break_even_bid=None, max_bid=None, max_bid_binding_constraint=None,
            unknown_costs=sorted(set(unknown)), assumed_costs=used_assumed, complete=False, notes=notes,
        )
    net, sf, resale_costs = np_
    profit = net - acq_total
    roi = (profit / acq_total * 100.0) if acq_total > 0 else None
    gross_margin = ((r.resale_price - acq_total) / r.resale_price * 100.0) if r.resale_price else None
    net_margin = (profit / r.resale_price * 100.0) if r.resale_price else None

    k, fixed = _acq_linear_coeffs(a, assumed)
    # break-even: k*bid + fixed = net
    be = (net - fixed) / k if k > 0 else None
    # constraints on bid
    candidates: dict[str, float] = {}
    candidates["min_profit"] = (net - fixed - thresholds.min_profit_usd) / k
    if thresholds.min_roi_pct is not None:
        candidates["min_roi"] = (net / (1 + thresholds.min_roi_pct / 100.0) - fixed) / k
    if thresholds.max_capital_at_risk_usd is not None:
        candidates["max_capital_at_risk"] = (thresholds.max_capital_at_risk_usd - fixed) / k
    binding = min(candidates, key=candidates.get)
    max_bid = candidates[binding]
    if max_bid < 0:
        max_bid = 0.0
        notes.append("No bid satisfies the configured profit/ROI thresholds at this resale value.")
    max_bid = _floor_to_increment(max_bid, thresholds.bid_increment)
    if unknown:
        notes.append(
            "Unknown costs treated as $0 in this calculation: " + ", ".join(sorted(set(unknown)))
            + ". Enter them (or set defaults in Settings) for an accurate maximum bid."
        )
    critical_unknown = [u for u in unknown if u in ("incoming_shipping", "outgoing_shipping")]
    return FinanceResult(
        bid=a.bid,
        acquisition_total=_r(acq_total),
        acquisition_breakdown=breakdown,
        resale_price=_r(r.resale_price),
        selling_fees=_r(sf),
        resale_costs=_r(resale_costs),
        net_proceeds=_r(net),
        profit=_r(profit),
        roi_pct=_r(roi),
        gross_margin_pct=_r(gross_margin),
        net_margin_pct=_r(net_margin),
        break_even_bid=_r(max(be, 0.0)) if be is not None else None,
        max_bid=_r(max_bid),
        max_bid_binding_constraint=binding,
        unknown_costs=sorted(set(unknown)),
        assumed_costs={k: _r(v) for k, v in used_assumed.items()},
        complete=not critical_unknown,
        notes=notes,
    )


def risk_adjusted_value(
    conservative: float | None,
    expected: float | None,
    optimistic: float | None,
    evidence_quality: str,
    identification_confidence: float | None,
    weights_by_evidence: dict[str, list[float]],
    confidence_haircut: float = 0.5,
) -> tuple[float | None, dict[str, Any]]:
    """HEURISTIC risk-adjusted resale value (uncalibrated; see Settings > risk)."""
    if expected is None:
        return None, {"reason": "no_valuation"}
    cons = conservative if conservative is not None else expected
    opt = optimistic if optimistic is not None else expected
    w = weights_by_evidence.get(evidence_quality, weights_by_evidence.get("none", [0.8, 0.2, 0.0]))
    blended = w[0] * cons + w[1] * expected + w[2] * opt
    conf = identification_confidence if identification_confidence is not None else 0.5
    haircut = (1.0 - conf) * confidence_haircut
    value = blended * (1.0 - haircut)
    return round(value, 2), {
        "scenario_weights": w,
        "evidence_quality": evidence_quality,
        "identification_confidence": conf,
        "confidence_haircut_pct": round(haircut * 100, 1),
        "label": "heuristic, uncalibrated",
    }


def sensitivity(
    a: AcquisitionInputs,
    r: ResaleInputs,
    fees: PlatformFees,
    thresholds: Thresholds,
    assumed: dict[str, float] | None,
    resale_values: list[float],
    shipping_values: list[float],
) -> list[dict[str, Any]]:
    """Grid of (resale, incoming shipping) -> profit, max bid. Used by the what-if UI."""
    rows = []
    for rv in resale_values:
        for sv in shipping_values:
            a2 = AcquisitionInputs(**{**asdict(a), "incoming_shipping": sv})
            r2 = ResaleInputs(**{**asdict(r), "resale_price": rv})
            res = compute(a2, r2, fees, thresholds, assumed)
            rows.append({"resale_price": rv, "incoming_shipping": sv, "profit": res.profit, "max_bid": res.max_bid, "roi_pct": res.roi_pct})
    return rows
