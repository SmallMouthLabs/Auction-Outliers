"""Adversarial model output through the guard; input validation; invariants found in review."""
from __future__ import annotations

import copy
from datetime import UTC

from outlier.analysis.guards import apply_guards
from outlier.analysis.schemas import DeepResult
from outlier.demo.fixtures import demo_analysis_fixtures

FIX = demo_analysis_fixtures()


def _id(client, key="mohair_cardigan") -> int:
    """Demo ids change when another test clears/reloads demo data; look them up fresh."""
    items = client.get("/api/listings?limit=500").json()["items"]
    return next(i["id"] for i in items if i["source_item_id"] == f"demo-{key}")


def _adversarial_jewelry():
    d = copy.deepcopy(FIX["silvertone_necklace:deep"])
    d["candidates"][0].update({"label": "Tiffany & Co sterling necklace", "brand_or_maker": "Tiffany", "status": "confirmed", "confidence": 1.0})
    d["jewelry"]["materials"][0].update({"confidence": 0.98, "basis": ["looks like sterling"], "verification_needed": None})
    d["jewelry"]["melt_value_note"] = "Melt value approx $42 at spot"
    d["jewelry"]["maker_confidence"] = 0.99
    d["overall_confidence"] = 1.0
    d["risk_flags"] = []
    return d


def test_guard_demotes_confirmed_precious_and_designer_and_strips_melt_value():
    out = apply_guards(_adversarial_jewelry())
    DeepResult.model_validate({k: v for k, v in out.items() if k != "guard_notes"})
    assert out["candidates"][0]["status"] == "inferred" and out["candidates"][0]["confidence"] <= 0.95
    assert out["jewelry"]["materials"][0]["confidence"] == 0.7
    assert out["jewelry"]["materials"][0]["verification_needed"]
    assert "$" not in out["jewelry"]["melt_value_note"]
    assert out["jewelry"]["maker_confidence"] <= 0.9 and out["overall_confidence"] <= 0.95
    assert "precious metal unverified" in out["risk_flags"] and any("melt" in f for f in out["risk_flags"])
    assert len(out["guard_notes"]) >= 3


def test_guard_allows_tested_material():
    d = _adversarial_jewelry()
    d["jewelry"]["materials"][0].update({"confidence": 0.95, "basis": ["acid tested by seller, photo of test"]})
    out = apply_guards(d)
    assert out["jewelry"]["materials"][0]["confidence"] == 0.95


def test_guard_caps_designer_clothing_brand_confidence():
    d = copy.deepcopy(FIX["damaged_designer_sweater:deep"])
    d["clothing"]["brand_or_manufacturer"] = "Comme des Garcons"
    d["clothing"]["brand_confidence"] = 0.99
    out = apply_guards(d)
    assert out["clothing"]["brand_confidence"] == 0.9 and "designer authenticity not verified" in out["risk_flags"]


def test_guard_leaves_clean_output_alone():
    d = copy.deepcopy(FIX["mohair_cardigan:deep"])
    out = apply_guards(d)
    assert "guard_notes" not in out and out["risk_flags"] == []


def test_guard_runs_in_pipeline(client, demo):
    lid = _id(client, "silvertone_necklace")
    d = client.get(f"/api/listings/{lid}").json()
    assert d["identification_full"]["data"]["jewelry"]["materials"][0]["confidence"] <= 0.7


def test_negative_numbers_rejected(client, demo):
    lid = _id(client)
    assert client.post(f"/api/listings/{lid}/finance", json={"bid": -50}).status_code == 422
    assert client.post("/api/listings", json={"title": "neg", "current_bid": -5}).status_code == 422
    assert client.post(f"/api/listings/{lid}/comps", json={"title": "neg", "price": -50, "is_sold": True}).status_code == 422
    assert client.put(f"/api/watchlist/{lid}", json={"status": "bogus"}).status_code == 422
    assert client.put(f"/api/listings/{lid}/outcome", json={"resale_price": -100}).status_code == 422
    assert client.post("/api/reference", json={"name": "x", "domain": "bogus"}).status_code == 422
    assert client.post(f"/api/listings/{lid}/valuation/override", json={"expected": 300, "conservative": 500}).status_code == 422
    assert client.post("/api/listings", json={"title": "   "}).status_code == 422
    assert client.patch(f"/api/listings/{lid}", json={"title": None}).status_code == 400
    assert client.patch(f"/api/listings/{lid}", json={"source_url": "javascript:alert(1)"}).status_code == 422


def test_typed_overrides_and_unknown_platform(client, demo):
    lid = _id(client)
    assert client.post(f"/api/listings/{lid}/finance", json={"overrides": {"incoming_shipping": "abc"}}).status_code == 400
    assert client.post(f"/api/listings/{lid}/finance", json={"overrides": {"bogus_key": 1}}).status_code == 400
    assert client.patch(f"/api/listings/{lid}", json={"assumptions": {"incoming_shipping": "abc"}}).status_code == 400
    r = client.post(f"/api/listings/{lid}/finance", json={"platform": "nonexistent"})
    assert r.status_code == 400 and "unknown platform" in r.json()["detail"]
    r = client.post(f"/api/listings/{lid}/finance", json={"overrides": {"incoming_shipping": 20}})
    assert r.status_code == 200 and r.json()["scenarios"]["expected"]["acquisition_breakdown"]["incoming_shipping"] == 20


def test_nested_settings_validated(client):
    assert client.put("/api/settings", json={"thresholds": {"min_roi_pct": None}}).status_code == 400
    assert client.put("/api/settings", json={"ranking": {"weights": "banana"}}).status_code == 400
    assert client.put("/api/settings", json={"analysis": {"exclude_keywords": "string"}}).status_code == 400
    assert client.put("/api/settings", json={"acquisition": {"bid_increment": -1}}).status_code == 400
    assert client.put("/api/settings", json={"default_platform": "nope"}).status_code == 400
    assert client.put("/api/settings", json={"thresholds": {"bogus": 1}}).status_code == 400
    r = client.put("/api/settings", json={"thresholds": {"min_profit_usd": 30}})
    assert r.status_code == 200 and r.json()["settings"]["thresholds"]["min_profit_usd"] == 30
    client.post("/api/settings/reset")


def test_comp_sold_active_invariant(client, demo):
    lid = _id(client)
    before = client.get(f"/api/listings/{lid}").json()["valuation"]["expected"]
    r = client.post(f"/api/listings/{lid}/comps", json={"title": "asking 999", "price": 999, "is_sold": False, "comp_type": "exact"})
    cid = r.json()["comparable"]["id"]
    assert r.json()["listing"]["valuation"]["expected"] == before
    r = client.patch(f"/api/listings/{lid}/comps/{cid}", json={"is_sold": True})
    assert r.json()["comparable"]["comp_type"] == "category"
    # still an outlier vs the exact comps -> excluded, valuation unchanged
    assert r.json()["listing"]["valuation"]["expected"] == before
    r = client.patch(f"/api/listings/{lid}/comps/{cid}", json={"is_sold": False})
    assert r.json()["comparable"]["comp_type"] == "active"
    client.delete(f"/api/listings/{lid}/comps/{cid}")


def test_demo_rows_never_merge_with_real_imports(client, demo):
    r = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Real import", "source_item_id": "demo-mohair_cardigan", "current_bid": 1})
    assert r.status_code == 201 and r.json()["created"] is True and r.json()["listing"]["is_demo"] is False
    demo_row = client.get(f"/api/listings/{_id(client)}").json()
    assert demo_row["current_bid"] != 1
    client.delete(f"/api/listings/{r.json()['listing']['id']}")


def test_unknown_provider_and_budget_codes(client, demo, monkeypatch):
    lid = _id(client)
    r = client.post(f"/api/listings/{lid}/analyze", json={"mode": "deep", "provider": "bogus"})
    assert r.status_code == 424 and "Unknown provider" in r.json()["detail"]
    from outlier.config import reset_caches

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    monkeypatch.setenv("OUTLIER_DAILY_BUDGET_USD", "0")
    reset_caches()
    r = client.post(f"/api/listings/{lid}/analyze", json={"mode": "deep", "provider": "anthropic"})
    assert r.status_code == 429 and r.json()["code"] == "budget_exceeded"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("OUTLIER_DAILY_BUDGET_USD")
    reset_caches()


def test_ended_auction_cannot_be_rescued_by_feedback():
    from datetime import datetime, timedelta

    from outlier.ranking.score import RankInputs, score
    from outlier.settings_store import DEFAULT_SETTINGS

    now = datetime(2026, 10, 1, tzinfo=UTC)
    inp = RankInputs(expected_profit=80, optimistic_profit=150, risk_adjusted_profit=60, roi_pct=150, identification_confidence=0.9,
                     evidence_quality="high", demand="high", liquidity="high", num_bids=0, risk_flags=0, misidentification_signal=0.5,
                     ends_at=now - timedelta(hours=1), warrants_research=False, has_valuation=True, finance_complete=True,
                     feedback_labels=["excellent_find"])
    assert score(inp, {**DEFAULT_SETTINGS["ranking"], "thresholds": DEFAULT_SETTINGS["thresholds"]}, now)["score"] == 0


def test_image_fetch_refuses_private_hosts():
    import pytest

    from outlier.services.listings import _assert_public_host

    for u in ("http://127.0.0.1:8000/api/settings", "http://localhost/x.jpg", "http://10.0.0.5/a.png", "http://169.254.169.254/latest"):
        with pytest.raises(ValueError):
            _assert_public_host(u)


def test_page_import_rejects_non_html(client):
    r = client.post("/api/listings/import/page", data={"html": "just text no tags"})
    assert r.status_code == 400


def test_cached_flag_reported(client, demo):
    lid = _id(client)
    s = client.post(f"/api/listings/{lid}/analyze", json={"mode": "auto", "provider": "demo"}).json()["summary"]
    assert all(st.get("cached") for st in s["stages"] if st["stage"] in ("triage", "deep"))
