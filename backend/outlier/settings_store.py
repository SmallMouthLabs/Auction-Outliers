"""User-editable, non-secret settings with defaults.

All numbers below are CONFIGURABLE HEURISTICS / DEFAULT ASSUMPTIONS, not facts.
Marketplace fee schedules change; verify them in Settings before relying on them.
"""
from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

from .models import Setting

DEFAULT_SETTINGS: dict[str, Any] = {
    # ---- selling platform fee configurations (verify against each marketplace's current schedule) ----
    "platforms": {
        "ebay": {
            "label": "eBay",
            "final_value_fee_pct": 13.25,  # typical clothing/jewelry FVF; category-dependent
            "per_order_fee": 0.40,  # per-order fixed fee (US)
            "payment_processing_pct": 0.0,  # included in FVF on managed payments
            "payment_processing_fixed": 0.0,
            "listing_fee": 0.0,
            "seller_pays_shipping": True,
            "note": "Final value fee varies by category and store level; promoted listings add more.",
        },
        "etsy": {
            "label": "Etsy",
            "final_value_fee_pct": 6.5,
            "per_order_fee": 0.0,
            "payment_processing_pct": 3.0,
            "payment_processing_fixed": 0.25,
            "listing_fee": 0.20,
            "seller_pays_shipping": True,
            "note": "Offsite-ads fees (12-15%) apply when a sale is attributed to Etsy ads.",
        },
        "depop": {
            "label": "Depop",
            "final_value_fee_pct": 0.0,  # US selling fee removed July 2024; verify for your region
            "per_order_fee": 0.0,
            "payment_processing_pct": 3.3,
            "payment_processing_fixed": 0.45,
            "listing_fee": 0.0,
            "seller_pays_shipping": False,
            "note": "US: buyer pays a marketplace fee instead of the seller. Non-US sellers still pay 10%.",
        },
        "grailed": {
            "label": "Grailed",
            "final_value_fee_pct": 9.0,
            "per_order_fee": 0.0,
            "payment_processing_pct": 3.49,
            "payment_processing_fixed": 0.49,
            "listing_fee": 0.0,
            "seller_pays_shipping": True,
            "note": "Commission 9% + payment processing.",
        },
        "local": {
            "label": "Local sale",
            "final_value_fee_pct": 0.0,
            "per_order_fee": 0.0,
            "payment_processing_pct": 0.0,
            "payment_processing_fixed": 0.0,
            "listing_fee": 0.0,
            "seller_pays_shipping": False,
            "note": "Cash / in-person.",
        },
        "custom": {
            "label": "Custom",
            "final_value_fee_pct": 10.0,
            "per_order_fee": 0.0,
            "payment_processing_pct": 3.0,
            "payment_processing_fixed": 0.30,
            "listing_fee": 0.0,
            "seller_pays_shipping": True,
            "note": "Edit to match any other channel.",
        },
    },
    "default_platform": "ebay",
    # ---- acquisition assumptions ----
    "acquisition": {
        "buyer_premium_pct": 0.0,  # ShopGoodwill has no buyer premium
        "sales_tax_pct": 0.0,  # depends on your state and the seller; set in Settings
        "default_incoming_shipping": None,  # None => unknown; UI will flag it
        "default_handling_fee": None,
        "bid_increment": 1.0,
    },
    # ---- resale cost assumptions ----
    "resale": {
        "clothing_outgoing_shipping": 9.50,
        "jewelry_outgoing_shipping": 5.00,
        "packaging_cost": 1.00,
        "default_cleaning_cost": 0.0,
        "holding_cost_per_month": 0.0,
    },
    # ---- decision thresholds ----
    "thresholds": {
        "min_profit_usd": 25.0,
        "min_roi_pct": 50.0,
        "max_capital_at_risk_usd": 250.0,
    },
    # ---- risk adjustment heuristics (labeled: heuristics, uncalibrated) ----
    "risk": {
        "scenario_weights_by_evidence": {
            # weights on (conservative, expected, optimistic) used for the risk-adjusted value
            "high": [0.25, 0.60, 0.15],
            "medium": [0.40, 0.50, 0.10],
            "low": [0.60, 0.35, 0.05],
            "none": [0.80, 0.20, 0.00],
        },
        "identification_confidence_haircut": 0.5,  # fraction of (1-confidence) applied as a discount
        "estimated_months_to_sell": {"high": 1.0, "medium": 2.5, "low": 5.0},
    },
    # ---- ranking weights (heuristic, configurable; see ranking/score.py) ----
    "ranking": {
        "weights": {
            "expected_profit": 0.22,
            "risk_adjusted_profit": 0.18,
            "roi": 0.10,
            "identification_confidence": 0.12,
            "evidence_quality": 0.12,
            "sell_likelihood": 0.08,
            "time_to_sell": 0.04,
            "competition": 0.04,
            "risk_flags": 0.05,
            "misidentification_signal": 0.05,
        },
        "profit_reference_usd": 100.0,  # profit at which the profit component reaches ~0.73
        "roi_reference_pct": 100.0,
        "feedback_adjustments": {
            "excellent_find": 0.15,
            "worth_investigating": 0.05,
            "not_worth_buying": -0.5,
            "incorrect_identification": -0.2,
            "incorrect_valuation": -0.2,
            "too_risky": -0.3,
            "too_slow_to_resell": -0.2,
        },
    },
    # ---- analysis / budget ----
    "analysis": {
        "auto_escalate_min_triage_interest": 55,  # 0-100 triage interest needed to run deep stage automatically
        "exclude_keywords": ["reproduction", "replica", "costume lot", "craft lot", "fabric scraps"],
        "boost_keywords": [
            "mohair", "cashmere", "selvedge", "selvage", "redline", "big e", "union made", "talon zipper",
            "sterling", "925", "14k", "18k", "taxco", "modernist", "signed", "hallmark", "hallmarked",
            "deadstock", "nos", "single stitch", "made in usa", "made in italy", "made in france",
            "made in england", "harris tweed", "pendleton", "woolrich", "lee", "levi", "wrangler",
            "carhartt", "schott", "navajo", "georg jensen", "kalo", "ed levin", "spratling", "margot",
        ],
        "min_current_bid": 0.0,
        "max_current_bid": 500.0,
    },
    "notifications": {"reminder_minutes_before_end": 30, "enable_console_reminders": True},
    "model_pricing_usd_per_1m": {
        # (input, output). Editable. Defaults from provider price lists as of 2026-10; verify.
        "claude-haiku-5-5": [0.10, 0.50],
        "claude-sonnet-5-5": [2.00, 10.00],
        "claude-opus-5-5": [4.00, 20.00],
        "gemini-2.5-flash": [0.30, 2.50],
        "gemini-2.5-flash-lite": [0.10, 0.40],
        "gemini-2.5-pro": [1.25, 10.00],
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_all_settings(db: Session) -> dict[str, Any]:
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    for row in db.query(Setting).all():
        if isinstance(row.value, dict) and isinstance(merged.get(row.key), dict):
            merged[row.key] = _deep_merge(merged[row.key], row.value)
        else:
            merged[row.key] = row.value
    return merged


def get_setting(db: Session, key: str) -> Any:
    return get_all_settings(db).get(key)


def validate_merged(merged: dict[str, Any]) -> None:
    from .settings_schema import SettingsModel

    try:
        SettingsModel.model_validate(merged).check()
    except ValueError as e:
        raise ValueError(f"invalid settings: {e}") from e


def update_settings(db: Session, patch: dict[str, Any]) -> dict[str, Any]:
    for key in patch:
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f"Unknown settings key: {key}")
    # validate the result of applying the patch before persisting anything
    current = get_all_settings(db)
    candidate = copy.deepcopy(current)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(candidate.get(key), dict):
            candidate[key] = _deep_merge(candidate[key], value)
        else:
            candidate[key] = value
    validate_merged(candidate)
    for key, value in patch.items():
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=value)
            db.add(row)
        else:
            if isinstance(value, dict) and isinstance(row.value, dict):
                row.value = _deep_merge(row.value, value)
            else:
                row.value = value
    db.flush()
    return get_all_settings(db)


def reset_settings(db: Session) -> dict[str, Any]:
    db.query(Setting).delete()
    db.flush()
    return get_all_settings(db)
