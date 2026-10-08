"""Recompute valuation -> finance -> ranking for a listing and persist the Opportunity row."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..finance.calc import (
    AcquisitionInputs,
    PlatformFees,
    ResaleInputs,
    Thresholds,
    compute,
    risk_adjusted_value,
    sensitivity,
)
from ..finance.overrides import validate_overrides
from ..models import Comparable, Feedback, Listing, Opportunity, Valuation
from ..ranking.score import RankInputs, score
from ..settings_store import get_all_settings
from ..valuation.engine import CompInput, valuate


def current_identification(l: Listing):
    cur = [i for i in l.identifications if i.is_current]
    if not cur:
        return None
    # user corrections win; else most recent
    cur.sort(key=lambda i: (i.origin != "user", -(i.id or 0)))
    return cur[0]


def current_valuation(l: Listing) -> Valuation | None:
    cur = [v for v in l.valuations if v.is_current]
    return max(cur, key=lambda v: v.id) if cur else None


def _comp_inputs(comps: list[Comparable]) -> list[CompInput]:
    return [
        CompInput(id=c.id, title=c.title, price=c.price, is_sold=c.is_sold, comp_type=c.comp_type, similarity=c.similarity,
                  evidence_quality=c.evidence_quality, sold_date=c.sold_date, shipping_included=c.shipping_included,
                  shipping_amount=c.shipping_amount, marketplace=c.marketplace, url=c.url, accepted_offer=c.accepted_offer,
                  differences=c.differences)
        for c in comps
    ]


def recompute_valuation(db: Session, l: Listing) -> Valuation:
    """Recompute from sold comps unless a user override is current."""
    cur = current_valuation(l)
    if cur and cur.method == "user_override":
        return cur
    res = valuate(_comp_inputs(l.comparables))
    for v in l.valuations:
        v.is_current = False
    val = Valuation(listing_id=l.id, method=res.method, conservative=res.conservative, expected=res.expected,
                    optimistic=res.optimistic, is_speculative=res.is_speculative, evidence_quality=res.evidence_quality,
                    n_sold_comps=res.n_sold_comps, detail=res.to_dict(), is_current=True)
    db.add(val)
    l.valuations.append(val)
    db.flush()
    return val


def set_valuation_override(db: Session, l: Listing, conservative: float | None, expected: float, optimistic: float | None, note: str) -> Valuation:
    for v in l.valuations:
        v.is_current = False
    val = Valuation(listing_id=l.id, method="user_override", conservative=conservative, expected=expected, optimistic=optimistic,
                    is_speculative=True, evidence_quality="low", n_sold_comps=0,
                    detail={"notes": [f"User-entered estimate: {note}", "Marked speculative: not backed by sold comparables in the system."]},
                    is_current=True)
    db.add(val)
    l.valuations.append(val)
    db.flush()
    return val


def clear_valuation_override(db: Session, l: Listing) -> Valuation:
    for v in l.valuations:
        if v.method == "user_override":
            v.is_current = False
    return recompute_valuation(db, l)


def finance_inputs(l: Listing, settings: dict[str, Any], *, bid: float | None = None, platform: str | None = None,
                   overrides: dict[str, Any] | None = None) -> tuple[AcquisitionInputs, ResaleInputs, PlatformFees, Thresholds, dict[str, float]]:
    ov = {**validate_overrides(l.assumptions), **validate_overrides(overrides)}
    acq_cfg = settings["acquisition"]
    res_cfg = settings["resale"]
    thr_cfg = settings["thresholds"]
    plat = platform or ov.get("platform") or settings["default_platform"]
    if plat not in settings["platforms"]:
        raise ValueError(f"unknown platform '{plat}'; configured: {sorted(settings['platforms'])}")
    fees = PlatformFees.from_config(plat, settings["platforms"][plat])
    a = AcquisitionInputs(
        bid=float(bid if bid is not None else (l.current_bid or 0.0)),
        buyer_premium_pct=float(ov.get("buyer_premium_pct", acq_cfg["buyer_premium_pct"])),
        sales_tax_pct=float(ov.get("sales_tax_pct", acq_cfg["sales_tax_pct"])),
        incoming_shipping=ov.get("incoming_shipping", l.shipping_cost),
        handling_fee=ov.get("handling_fee", l.handling_fee),
        other_costs={**(l.other_costs or {}), **(ov.get("other_acquisition_costs") or {})},
    )
    domain_ship = res_cfg["jewelry_outgoing_shipping"] if l.domain == "jewelry" else res_cfg["clothing_outgoing_shipping"]
    r = ResaleInputs(
        resale_price=None,
        outgoing_shipping=ov.get("outgoing_shipping"),
        packaging_cost=float(ov.get("packaging_cost", res_cfg["packaging_cost"])),
        cleaning_repair_cost=float(ov.get("cleaning_repair_cost", res_cfg["default_cleaning_cost"])),
        other_costs=ov.get("other_resale_costs") or {},
    )
    thr = Thresholds(
        min_profit_usd=float(ov.get("min_profit_usd", thr_cfg["min_profit_usd"])),
        min_roi_pct=float(ov.get("min_roi_pct", thr_cfg["min_roi_pct"])),
        max_capital_at_risk_usd=ov.get("max_capital_at_risk_usd", thr_cfg["max_capital_at_risk_usd"]),
        bid_increment=float(acq_cfg.get("bid_increment", 1.0)),
    )
    assumed: dict[str, float] = {"outgoing_shipping": float(domain_ship)}
    if acq_cfg.get("default_incoming_shipping") is not None:
        assumed["incoming_shipping"] = float(acq_cfg["default_incoming_shipping"])
    if acq_cfg.get("default_handling_fee") is not None:
        assumed["handling_fee"] = float(acq_cfg["default_handling_fee"])
    return a, r, fees, thr, assumed


def compute_finance(db: Session, l: Listing, *, bid: float | None = None, platform: str | None = None,
                    resale_override: float | None = None, overrides: dict[str, Any] | None = None,
                    with_sensitivity: bool = False) -> dict[str, Any]:
    settings = get_all_settings(db)
    val = current_valuation(l)
    ident = current_identification(l)
    a, r, fees, thr, assumed = finance_inputs(l, settings, bid=bid, platform=platform, overrides=overrides)
    scenarios: dict[str, Any] = {}
    values = {
        "conservative": val.conservative if val else None,
        "expected": resale_override if resale_override is not None else (val.expected if val else None),
        "optimistic": val.optimistic if val else None,
    }
    for name, rv in values.items():
        r2 = ResaleInputs(**{**r.__dict__, "resale_price": rv})
        scenarios[name] = compute(a, r2, fees, thr, assumed).to_dict()
    eq = val.evidence_quality if val else "none"
    ra_value, ra_meta = risk_adjusted_value(
        values["conservative"], values["expected"], values["optimistic"], eq,
        ident.confidence if ident else None, settings["risk"]["scenario_weights_by_evidence"],
        settings["risk"]["identification_confidence_haircut"],
    )
    ra = None
    if ra_value is not None:
        liq = (ident.data.get("liquidity_indicator") if ident and ident.data else None) or "medium"
        months = settings["risk"]["estimated_months_to_sell"].get(liq, 2.5)
        holding = settings["resale"]["holding_cost_per_month"] * months
        r3 = ResaleInputs(**{**r.__dict__, "resale_price": ra_value, "other_costs": {**r.other_costs, "holding_cost": holding}})
        ra = compute(a, r3, fees, thr, assumed).to_dict()
        ra["meta"] = {**ra_meta, "estimated_months_to_sell": months, "holding_cost": holding}
    out = {
        "platform": fees.name,
        "bid_used": a.bid,
        "valuation": {
            "method": val.method if val else None, "is_speculative": val.is_speculative if val else True,
            "evidence_quality": eq, "n_sold_comps": val.n_sold_comps if val else 0, **values,
            "notes": (val.detail or {}).get("notes", []) if val else ["No valuation yet."],
        },
        "scenarios": scenarios,
        "risk_adjusted": ra,
        "thresholds": thr.__dict__,
        "assumptions_used": {"assumed_costs": assumed, "listing_overrides": l.assumptions or {}, "request_overrides": overrides or {}},
    }
    if with_sensitivity and values["expected"]:
        ev = values["expected"]
        ship_base = a.incoming_shipping if a.incoming_shipping is not None else assumed.get("incoming_shipping", 10.0)
        out["sensitivity"] = sensitivity(a, ResaleInputs(**{**r.__dict__, "resale_price": ev}), fees, thr, assumed,
                                         [round(ev * f, 2) for f in (0.6, 0.8, 1.0, 1.2, 1.5)],
                                         [round(max(ship_base + d, 0), 2) for d in (-5, 0, 5, 15, 30)])
    return out


def recompute_opportunity(db: Session, l: Listing) -> Opportunity:
    settings = get_all_settings(db)
    recompute_valuation(db, l)
    fin = compute_finance(db, l)
    ident = current_identification(l)
    val = current_valuation(l)
    exp = fin["scenarios"]["expected"]
    opt = fin["scenarios"]["optimistic"]
    ra = fin["risk_adjusted"]
    data = (ident.data if ident else {}) or {}
    refs = data.get("reference_matches") or []
    demand = data.get("demand_indicator")
    liquidity = data.get("liquidity_indicator")
    if refs:
        demand = demand if demand not in (None, "unknown") else refs[0].get("demand")
        liquidity = liquidity if liquidity not in (None, "unknown") else refs[0].get("liquidity")
    labels = [f.label for f in db.query(Feedback).filter(Feedback.listing_id == l.id).all()]
    inp = RankInputs(
        expected_profit=exp.get("profit"), optimistic_profit=opt.get("profit"),
        risk_adjusted_profit=ra.get("profit") if ra else None, roi_pct=exp.get("roi_pct"),
        identification_confidence=ident.confidence if ident else None,
        evidence_quality=val.evidence_quality if val else "none",
        demand=None if demand == "unknown" else demand, liquidity=None if liquidity == "unknown" else liquidity,
        num_bids=l.num_bids, risk_flags=len(data.get("risk_flags") or []),
        misidentification_signal=(ident.discrepancy or {}).get("signal") if ident else None,
        ends_at=l.ends_at, warrants_research=bool(ident.warrants_research) if ident else False,
        has_valuation=bool(val and val.expected is not None), finance_complete=bool(exp.get("complete")),
        feedback_labels=labels, status=l.status,
    )
    cfg = {**settings["ranking"], "thresholds": settings["thresholds"]}
    sc = score(inp, cfg)
    opp = l.opportunity
    if opp is None:
        opp = Opportunity(listing_id=l.id)
        db.add(opp)
        l.opportunity = opp
    opp.score = sc["score"]
    opp.tier = sc["tier"]
    opp.components = sc
    opp.finance = {
        "expected_profit": exp.get("profit"), "expected_roi_pct": exp.get("roi_pct"), "max_bid": exp.get("max_bid"),
        "break_even_bid": exp.get("break_even_bid"), "risk_adjusted_profit": ra.get("profit") if ra else None,
        "complete": exp.get("complete"), "unknown_costs": exp.get("unknown_costs"),
        "resale_low": fin["valuation"]["conservative"], "resale_expected": fin["valuation"]["expected"],
        "resale_high": fin["valuation"]["optimistic"], "evidence_quality": fin["valuation"]["evidence_quality"],
        "is_speculative": fin["valuation"]["is_speculative"], "platform": fin["platform"],
        "over_max_bid": (l.current_bid is not None and exp.get("max_bid") is not None and l.current_bid > exp["max_bid"]),
    }
    opp.computed_at = datetime.now(UTC)
    db.flush()
    return opp


def recompute_all(db: Session) -> int:
    n = 0
    for l in db.query(Listing).filter(Listing.archived == False).all():
        recompute_opportunity(db, l)
        n += 1
    return n
