from datetime import UTC, datetime, timedelta

from outlier.ranking.score import RankInputs, score
from outlier.settings_store import DEFAULT_SETTINGS

CFG = {**DEFAULT_SETTINGS["ranking"], "thresholds": DEFAULT_SETTINGS["thresholds"]}
NOW = datetime(2026, 10, 1, tzinfo=UTC)


def base(**kw):
    d = dict(expected_profit=80, optimistic_profit=150, risk_adjusted_profit=60, roi_pct=150,
             identification_confidence=0.85, evidence_quality="high", demand="high", liquidity="high",
             num_bids=0, risk_flags=0, misidentification_signal=0.6, ends_at=NOW + timedelta(days=2),
             warrants_research=True, has_valuation=True, finance_complete=True, feedback_labels=[])
    d.update(kw)
    return RankInputs(**d)


def test_high_confidence_tier():
    r = score(base(), CFG, NOW)
    assert r["tier"] == "HIGH_CONFIDENCE" and r["score"] > 60


def test_speculative_tier_when_evidence_low():
    r = score(base(evidence_quality="low", identification_confidence=0.4), CFG, NOW)
    assert r["tier"] == "SPECULATIVE_HIGH_UPSIDE"


def test_needs_research_without_valuation():
    r = score(base(has_valuation=False, expected_profit=None, roi_pct=None), CFG, NOW)
    assert r["tier"] == "NEEDS_RESEARCH"


def test_ended_auction_scores_zero():
    r = score(base(ends_at=NOW - timedelta(hours=1)), CFG, NOW)
    assert r["score"] == 0 and r["tier"] == "LOW_VALUE"


def test_feedback_adjusts_score():
    a = score(base(), CFG, NOW)["score"]
    b = score(base(feedback_labels=["not_worth_buying"]), CFG, NOW)["score"]
    assert b < a


def test_competition_reduces_score():
    a = score(base(num_bids=0), CFG, NOW)["score"]
    b = score(base(num_bids=25), CFG, NOW)["score"]
    assert b < a
