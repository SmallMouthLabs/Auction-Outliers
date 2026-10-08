"""End-to-end API tests covering the demo workflow and the spec's edge cases."""
from __future__ import annotations

import json

TIERS = {"HIGH_CONFIDENCE", "SPECULATIVE_HIGH_UPSIDE", "NEEDS_RESEARCH", "LOW_VALUE"}


def _by_key(demo, key):
    return next(a for a in demo["analysis"] if a["key"] == key)


def test_demo_workflow_runs_all_stages(client, demo):
    assert demo["note"].startswith("DEMO")
    for a in demo["analysis"]:
        assert [s["stage"] for s in a["stages"]] == ["prefilter", "triage", "deep"]
        assert a["tier"] in TIERS


def test_demo_rows_are_labeled(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    d = client.get(f"/api/listings/{lid}").json()
    assert d["is_demo"] is True
    assert all(im["is_demo"] for im in d["images"])
    assert all(c["is_demo"] for c in d["comparables"])
    assert d["identification_full"]["origin"] == "demo"
    assert all(r["is_demo"] for r in d["analysis_runs"] if r["stage"] != "prefilter")
    assert d["analysis_runs"][0]["tokens_in"] == 0 and d["analysis_runs"][0]["est_cost_usd"] == 0


def test_mohair_cardigan_is_high_confidence_with_discrepancy(client, demo):
    a = _by_key(demo, "mohair_cardigan")
    assert a["tier"] == "HIGH_CONFIDENCE"
    d = client.get(f"/api/listings/{a['id']}").json()
    disc = d["identification_full"]["discrepancy"]
    assert disc["signal"] > 0.5
    assert any("mohair" in f["visual_evidence"].lower() for f in disc["findings"])
    fin = d["opportunity"]["finance"]
    assert fin["expected_profit"] > 50 and fin["max_bid"] > d["current_bid"]
    assert fin["evidence_quality"] == "high" and fin["is_speculative"] is False


def test_necklace_precious_metal_unverified(client, demo):
    a = _by_key(demo, "silvertone_necklace")
    d = client.get(f"/api/listings/{a['id']}").json()
    j = d["identification_full"]["data"]["jewelry"]
    assert all(m["confidence"] < 0.9 for m in j["materials"])
    assert "unverified" in j["melt_value_note"].lower()
    assert "precious metal unverified" in d["identification_full"]["data"]["risk_flags"]
    assert d["opportunity"]["tier"] == "SPECULATIVE_HIGH_UPSIDE"
    assert d["valuation"]["is_speculative"] is True


def test_heavy_shipping_kills_jacket(client, demo):
    a = _by_key(demo, "leather_jacket_heavy_shipping")
    d = client.get(f"/api/listings/{a['id']}").json()
    fin = d["opportunity"]["finance"]
    assert d["valuation"]["evidence_quality"] == "high"  # strong comps...
    assert fin["expected_roi_pct"] < 50  # ...but shipping kills ROI
    assert fin["max_bid"] <= d["current_bid"] + 1
    assert d["opportunity"]["tier"] == "LOW_VALUE"


def test_damaged_designer_sweater_negative(client, demo):
    a = _by_key(demo, "damaged_designer_sweater")
    d = client.get(f"/api/listings/{a['id']}").json()
    assert any(c["severity"] == "major" for c in d["identification_full"]["data"]["condition_issues"])
    assert d["opportunity"]["finance"]["expected_profit"] < 25
    assert d["opportunity"]["tier"] == "LOW_VALUE"


def test_jewelry_lot_components(client, demo):
    a = _by_key(demo, "jewelry_lot")
    d = client.get(f"/api/listings/{a['id']}").json()
    comps = d["identification_full"]["data"]["jewelry"]["lot_components"]
    assert len(comps) >= 2 and any("Eisenberg" in c["description"] for c in comps)


def test_no_sold_comps_is_unsupported_and_active_not_used(client, demo):
    a = _by_key(demo, "no_sold_comps")
    d = client.get(f"/api/listings/{a['id']}").json()
    assert d["valuation"]["method"] == "unsupported" and d["valuation"]["expected"] is None
    assert d["valuation_full"]["detail"]["active_listing_context"]["n"] == 2
    assert d["opportunity"]["finance"]["complete"] is False
    assert d["opportunity"]["tier"] == "NEEDS_RESEARCH"


def test_price_above_max_bid_flagged(client, demo):
    a = _by_key(demo, "carhartt_over_max")
    d = client.get(f"/api/listings/{a['id']}").json()
    fin = d["opportunity"]["finance"]
    assert fin["over_max_bid"] is True and d["current_bid"] > fin["max_bid"]


def test_manual_comp_entry_and_valuation_recalc(client, demo):
    lid = _by_key(demo, "no_sold_comps")["id"]
    r = client.post(f"/api/listings/{lid}/comps", json={"title": "signed modernist sterling cuff sold", "price": 180, "is_sold": True,
                                                        "comp_type": "same_maker", "similarity": 0.7, "evidence_quality": "medium",
                                                        "sold_date": "2026-09-10", "url": "https://example.com/sold1"})
    assert r.status_code == 201
    r = client.post(f"/api/listings/{lid}/comps", json={"title": "modernist cuff sold 2", "price": 220, "is_sold": True, "comp_type": "same_maker",
                                                        "similarity": 0.6, "evidence_quality": "medium", "sold_date": "2026-08-01"})
    d = r.json()["listing"]
    assert d["valuation"]["method"] == "sold_comps" and d["valuation"]["n_sold_comps"] == 2
    assert 180 <= d["valuation"]["expected"] <= 220
    # active comp labeled as sold is reclassified
    r = client.post(f"/api/listings/{lid}/comps", json={"title": "asking", "price": 900, "is_sold": False, "comp_type": "exact"})
    assert r.json()["comparable"]["comp_type"] == "active"
    assert r.json()["listing"]["valuation"]["n_sold_comps"] == 2
    # override + recalc
    r = client.post(f"/api/listings/{lid}/valuation/override", json={"expected": 300, "note": "dealer quote"})
    assert r.json()["valuation"]["method"] == "user_override" and r.json()["valuation"]["is_speculative"] is True
    r = client.post(f"/api/listings/{lid}/valuation/recalculate")
    assert r.json()["valuation"]["method"] == "sold_comps"


def test_comps_csv_import(client, demo):
    lid = _by_key(demo, "jewelry_lot")["id"]
    csv = "title,price,sold_date,url,comp_type,similarity,evidence_quality,is_sold\nEisenberg Ice brooch,52,2026-09-02,https://e.com/1,same_maker,0.6,high,yes\nactive one,99,,https://e.com/2,exact,0.9,low,no\n"
    r = client.post(f"/api/listings/{lid}/comps/import", files={"file": ("c.csv", csv, "text/csv")})
    assert r.status_code == 200 and r.json()["imported"] == 2 and r.json()["errors"] == []
    comps = r.json()["listing"]["comparables"]
    assert any(c["title"] == "active one" and c["comp_type"] == "active" and c["is_sold"] is False for c in comps)


def test_finance_what_if(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    base = client.post(f"/api/listings/{lid}/finance", json={"sensitivity": True}).json()
    assert base["scenarios"]["expected"]["complete"] is True
    assert base["risk_adjusted"]["meta"]["label"].startswith("heuristic")
    assert len(base["sensitivity"]) == 25
    hi_ship = client.post(f"/api/listings/{lid}/finance", json={"overrides": {"incoming_shipping": 60}}).json()
    assert hi_ship["scenarios"]["expected"]["max_bid"] < base["scenarios"]["expected"]["max_bid"]
    etsy = client.post(f"/api/listings/{lid}/finance", json={"platform": "etsy"}).json()
    assert etsy["platform"] == "etsy" and etsy["scenarios"]["expected"]["selling_fees"] != base["scenarios"]["expected"]["selling_fees"]
    local = client.post(f"/api/listings/{lid}/finance", json={"platform": "local"}).json()
    assert local["scenarios"]["expected"]["selling_fees"] == 0


def test_unknown_shipping_surfaced(client):
    r = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Vintage Pendleton wool shirt jacket mens L", "current_bid": 15, "image_urls": ["https://example.invalid/a.jpg"]})
    assert r.status_code == 201
    lid = r.json()["listing"]["id"]
    client.post(f"/api/listings/{lid}/comps", json={"title": "Pendleton sold", "price": 90, "is_sold": True, "comp_type": "same_maker", "similarity": 0.7, "evidence_quality": "medium"})
    fin = client.post(f"/api/listings/{lid}/finance", json={}).json()
    assert "incoming_shipping" in fin["scenarios"]["expected"]["unknown_costs"]
    assert fin["scenarios"]["expected"]["complete"] is False
    assert "outgoing_shipping" in fin["scenarios"]["expected"]["assumed_costs"]  # default from settings, reported


def test_identification_correction_and_revert(client, demo):
    lid = _by_key(demo, "no_sold_comps")["id"]
    r = client.post(f"/api/listings/{lid}/identification", json={"summary": "Ed Levin modernist sterling cuff", "brand_or_maker": "Ed Levin", "confidence": 0.85, "liquidity_indicator": "medium"})
    assert r.status_code == 200
    d = r.json()
    assert d["identification"]["origin"] == "user" and d["identification"]["confidence"] == 0.85
    assert any(m["name"] == "Ed Levin" for m in d["identification_full"]["data"]["reference_matches"])
    assert d["identification_full"]["data"]["jewelry"]["potential_maker"] == "Ed Levin"
    r = client.delete(f"/api/listings/{lid}/identification/user")
    assert r.json()["identification"]["origin"] == "demo"


def test_feedback_persists_and_affects_score(client, demo):
    lid = _by_key(demo, "jewelry_lot")["id"]
    before = client.get(f"/api/listings/{lid}").json()["opportunity"]["score"]
    r = client.post(f"/api/listings/{lid}/feedback", json={"label": "too_risky", "note": "backs not shown"})
    assert r.status_code == 201
    after = r.json()["opportunity"]["score"]
    assert after < before
    assert "too_risky" in r.json()["feedback_labels"]
    assert client.post(f"/api/listings/{lid}/feedback", json={"label": "bogus"}).status_code == 400
    d = client.get(f"/api/listings/{lid}").json()
    assert d["feedback"][0]["label"] == "too_risky" and d["feedback"][0]["note"] == "backs not shown"


def test_outcome_persists(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    client.post(f"/api/listings/{lid}/feedback", json={"label": "purchased"})
    r = client.put(f"/api/listings/{lid}/outcome", json={"purchased": True, "purchase_price": 31, "acquisition_expenses": 13, "purchased_at": "2026-09-01T00:00:00Z",
                                                        "sold": True, "resale_price": 150, "selling_fees": 20.3, "sold_at": "2026-09-21T00:00:00Z", "resale_platform": "ebay"})
    o = r.json()["outcome"]
    assert o["days_to_sale"] == 20 and abs(o["realized_profit"] - 85.7) < 0.01
    an = client.get("/api/analytics/summary").json()
    assert an["sales"] >= 1 and an["realized_profit_total"] >= 85


def test_watchlist_and_reminders(client, demo):
    lid = _by_key(demo, "carhartt_over_max")["id"]  # ends in ~3h
    r = client.put(f"/api/watchlist/{lid}", json={"user_max_bid": 90, "remind_minutes_before_end": 600, "notes": "snipe"})
    assert r.status_code == 200 and r.json()["watchlist"]["user_max_bid"] == 90
    assert any(i["id"] == lid for i in client.get("/api/watchlist").json()["items"])
    due = client.get("/api/watchlist/reminders/due").json()["due"]
    assert any(d["listing_id"] == lid for d in due)
    r = client.put(f"/api/watchlist/{lid}", json={"status": "passed", "archived": True})
    assert r.json()["watchlist"]["archived"] is True
    assert not any(i["id"] == lid for i in client.get("/api/watchlist").json()["items"])


def test_snapshot_history(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    r = client.post(f"/api/listings/{lid}/snapshot", json={"current_bid": 70, "num_bids": 9})
    d = r.json()
    assert d["current_bid"] == 70 and len(d["snapshots"]) >= 2
    assert d["opportunity"]["finance"]["over_max_bid"] is True  # 70 > max bid (65)
    client.post(f"/api/listings/{lid}/snapshot", json={"current_bid": 12, "num_bids": 2})


def test_missing_provider_gives_clear_instructions(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    r = client.post(f"/api/listings/{lid}/analyze", json={"mode": "deep", "provider": "anthropic"})
    assert r.status_code == 424
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]
    r = client.post(f"/api/listings/{lid}/analyze", json={"mode": "deep", "provider": "auto"})
    # demo listing with auto -> demo provider works
    assert r.status_code == 200
    # real listing with auto -> not configured
    r = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Sterling brooch", "image_urls": []})
    lid2 = r.json()["listing"]["id"]
    r = client.post(f"/api/listings/{lid2}/analyze", json={"mode": "deep"})
    assert r.status_code == 424 and "GEMINI_API_KEY" in r.json()["detail"]
    r = client.post(f"/api/listings/{lid2}/analyze", json={"mode": "deep", "provider": "demo"})
    assert r.status_code == 424 and "demo provider only works on demo listings" in r.json()["detail"]


def test_analysis_cached_not_rerun(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    n_before = len(client.get(f"/api/listings/{lid}/analysis").json()["runs"])
    r = client.post(f"/api/listings/{lid}/analyze", json={"mode": "deep", "provider": "demo"})
    assert r.status_code == 200
    n_after = len(client.get(f"/api/listings/{lid}/analysis").json()["runs"])
    assert n_after == n_before + 1  # only a new prefilter run; triage/deep are served from cache


def test_prefilter_excludes_out_of_scope(client):
    r = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Sony Walkman cassette player", "category": "Electronics", "current_bid": 10, "image_urls": ["https://example.invalid/x.jpg"]})
    lid = r.json()["listing"]["id"]
    r = client.post(f"/api/listings/{lid}/analyze", json={"mode": "auto"})
    assert r.status_code == 200 and r.json()["summary"].get("stopped") == "prefilter"
    r = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Vintage sweater reproduction lot", "current_bid": 10, "image_urls": ["https://example.invalid/y.jpg"]})
    lid = r.json()["listing"]["id"]
    s = client.post(f"/api/listings/{lid}/analyze", json={"mode": "auto"}).json()["summary"]
    assert s["stopped"] == "prefilter" and any("Exclusion" in x for x in s["stages"][0]["reasons"])


def test_dedupe_by_item_id_url_and_fingerprint(client):
    base = {"title": "Vintage Levis 501 redline jeans 32x32", "current_bid": 20, "source_url": "https://shopgoodwill.com/item/987654321", "ends_at": "2026-12-01T10:00:00Z"}
    r1 = client.post("/api/listings", params={"fetch_images": "false"}, json=base)
    assert r1.json()["created"] is True
    r2 = client.post("/api/listings", params={"fetch_images": "false"}, json={**base, "current_bid": 25, "num_bids": 3})
    assert r2.json()["created"] is False and r2.json()["listing"]["id"] == r1.json()["listing"]["id"]
    assert r2.json()["listing"]["current_bid"] == 25 and len(r2.json()["listing"]["snapshots"]) == 2
    # same item id via a different source (email) -> same listing
    r3 = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Levis 501", "source": "email", "source_item_id": "987654321"})
    assert r3.json()["listing"]["id"] == r1.json()["listing"]["id"]
    # fingerprint fallback (no url/id)
    fp = {"title": "Odd  Vintage CARDIGAN!!", "seller": "x", "ends_at": "2026-12-02T10:00:00Z"}
    a = client.post("/api/listings", params={"fetch_images": "false"}, json=fp).json()["listing"]["id"]
    b = client.post("/api/listings", params={"fetch_images": "false"}, json={**fp, "title": "odd vintage cardigan"}).json()["listing"]["id"]
    assert a == b
    assert len(client.get("/api/listings?q=Levis").json()["items"]) == 1


def test_photo_upload_and_delete(client, tmp_png):
    r = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Upload test sterling ring"})
    lid = r.json()["listing"]["id"]
    r = client.post(f"/api/listings/{lid}/images", files=[("files", ("a.png", tmp_png, "image/png"))])
    assert r.status_code == 200 and r.json()["images"][0]["width"] == 64
    img = r.json()["images"][0]
    assert client.get(img["url"]).status_code == 200
    # duplicate bytes are deduplicated
    r = client.post(f"/api/listings/{lid}/images", files=[("files", ("b.png", tmp_png, "image/png"))])
    assert r.json()["images"][0]["id"] == img["id"]
    assert client.post(f"/api/listings/{lid}/images", files=[("files", ("c.png", b"notanimage", "image/png"))]).status_code == 400
    assert client.delete(f"/api/listings/{lid}/images/{img['id']}").status_code == 200
    assert client.get(img["url"]).status_code == 404


def test_csv_listing_import(client):
    csv = "Item ID,Title,Current Price,Bids,End Time,Shipping,URL,Images\n555001,Vintage mohair sweater L,14.50,3,10/20/2026 5:00 PM,12.95,https://shopgoodwill.com/item/555001,https://example.invalid/1.jpg|https://example.invalid/2.jpg\n,,,,,,,\n"
    r = client.post("/api/listings/import/csv", params={"fetch_images": "false"}, files={"file": ("l.csv", csv, "text/csv")})
    assert r.status_code == 200
    j = r.json()
    assert j["created"] == 1 and len(j["errors"]) == 1
    d = client.get(f"/api/listings/{j['ids'][0]}").json()
    assert d["source_item_id"] == "555001" and d["current_bid"] == 14.5 and d["num_bids"] == 3 and d["image_count"] == 2
    assert d["ends_at"].startswith("2026-10-21T00:00") or d["ends_at"].startswith("2026-10-20T")  # PT -> UTC


def test_email_import(client):
    html = """<html><body><h2>Your Personal Shopper found new items</h2>
    <table><tr><td><a href="https://shopgoodwill.com/item/123456789?utm=x"><img src="https://example.invalid/t1.jpg"></a></td>
    <td><a href="https://shopgoodwill.com/item/123456789">Vintage Sterling Silver Taxco Bracelet</a><br>Current Price: $12.00<br>3 bids<br>Ends: 10/15/2026 6:30 PM PT</td></tr>
    <tr><td><a href="https://shopgoodwill.com/item/223456789">Mohair Cardigan Womens</a> $8.50 0 bids</td></tr></table></body></html>"""
    r = client.post("/api/listings/import/email", params={"fetch_images": "false"}, data={"html": html})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["created"] == 2
    parsed = {p["source_item_id"]: p for p in j["parsed"]}
    p = parsed["123456789"]
    assert p["title"] == "Vintage Sterling Silver Taxco Bracelet" and p["current_bid"] == 12.0 and p["num_bids"] == 3
    assert p["image_urls"] == ["https://example.invalid/t1.jpg"] and p["ends_at"] is not None
    assert parsed["223456789"]["current_bid"] == 8.5
    # .eml path
    eml = ("Subject: Personal Shopper Alert\r\nContent-Type: text/html; charset=utf-8\r\nMIME-Version: 1.0\r\n\r\n" + html).encode()
    r = client.post("/api/listings/import/email", params={"fetch_images": "false"}, files={"file": ("a.eml", eml, "message/rfc822")})
    assert r.status_code == 200 and r.json()["created"] == 0 and r.json()["unchanged"] + r.json()["updated"] == 2
    r = client.post("/api/listings/import/email", params={"fetch_images": "false"}, data={"html": "<p>no links</p>"})
    assert r.json()["errors"]


def test_page_import(client):
    html = """<html><head><title>Vintage Wool Coat - Size M | ShopGoodwill</title><meta property="og:image" content="https://example.invalid/big.jpg">
    <link rel="canonical" href="https://shopgoodwill.com/item/777000111"></head><body><h1>Vintage Wool Coat Size M</h1>
    <div>Current Price: $23.00</div><div>5 bids</div><div>Ends: 10/30/2026 7:00 PM PT</div><div>Shipping: $14.25</div><div>Handling: $1.00</div>
    <div>Seller: Goodwill Demo Store</div><div>Category: Clothing > Women's > Coats</div><img src="https://example.invalid/p2.jpg"></body></html>"""
    r = client.post("/api/listings/import/page", params={"fetch_images": "false"}, data={"html": html})
    assert r.status_code == 200, r.text
    p = r.json()["parsed"]
    assert p["title"] == "Vintage Wool Coat Size M" and p["source_item_id"] == "777000111" and p["current_bid"] == 23.0
    assert p["num_bids"] == 5 and p["shipping_cost"] == 14.25 and p["handling_fee"] == 1.0 and p["seller"].startswith("Goodwill Demo")
    assert "https://example.invalid/big.jpg" in p["image_urls"] and "https://example.invalid/p2.jpg" in p["image_urls"]


def test_settings_roundtrip_and_recompute(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    before = client.get(f"/api/listings/{lid}").json()["opportunity"]["finance"]["max_bid"]
    r = client.put("/api/settings", json={"thresholds": {"min_roi_pct": 200}})
    assert r.status_code == 200 and r.json()["settings"]["thresholds"]["min_roi_pct"] == 200
    after = client.get(f"/api/listings/{lid}").json()["opportunity"]["finance"]["max_bid"]
    assert after < before
    assert client.put("/api/settings", json={"nope": 1}).status_code == 400
    r = client.post("/api/settings/reset")
    assert r.json()["settings"]["thresholds"]["min_roi_pct"] == 50
    s = client.get("/api/settings").json()
    assert "anthropic_api_key" not in json.dumps(s).lower()


def test_jobs_queue_runs_and_handles_failure(client, demo):
    lid = _by_key(demo, "mohair_cardigan")["id"]
    r = client.post("/api/jobs", json={"job_type": "analyze_listing", "listing_id": lid, "payload": {"mode": "triage", "provider": "demo"}})
    jid = r.json()["id"]
    r = client.post("/api/jobs", json={"job_type": "analyze_listing", "listing_id": 999999})
    bad = r.json()["id"]
    client.post("/api/jobs/process", params={"limit": 10})
    jobs = {j["id"]: j for j in client.get("/api/jobs").json()["items"]}
    assert jobs[jid]["status"] == "succeeded"
    assert jobs[bad]["status"] == "failed" and "not found" in jobs[bad]["error"]
    r = client.post(f"/api/jobs/{bad}/retry")
    assert r.json()["status"] == "pending"


def test_webhook_requires_token(client):
    r = client.post("/api/webhooks/listing", json={"title": "x"})
    assert r.status_code == 503


def test_reference_crud_and_matching(client, demo):
    r = client.post("/api/reference", json={"name": "Testmaker Studio", "domain": "jewelry", "entry_type": "maker_mark", "identifiers": ["TMS"], "keywords": ["testmaker"], "typical_low": 50, "typical_high": 200, "demand": "high", "liquidity": "high"})
    assert r.status_code == 201
    rid = r.json()["id"]
    r = client.post("/api/listings", params={"fetch_images": "false"}, json={"title": "Sterling pendant marked TMS", "domain": "jewelry"})
    lid = r.json()["listing"]["id"]
    m = client.get(f"/api/listings/{lid}/references").json()["matches"]
    assert m and m[0]["name"] == "Testmaker Studio"
    assert client.delete(f"/api/reference/{rid}").status_code == 200


def test_status_and_analytics(client, demo):
    s = client.get("/api/status").json()
    assert s["components"]["ai_deep"]["state"] == "needs_config"
    assert s["components"]["sold_data_manual"]["state"] == "live"
    assert s["counts"]["demo_listings"] == 7
    a = client.get("/api/analytics/summary").json()
    assert a["items_analyzed_deep"] >= 7 and a["ai_usage"]["spent_today_usd"] == 0


def test_demo_clear(client, demo):
    r = client.delete("/api/demo")
    assert r.json()["removed"] == 7
    assert client.get("/api/status").json()["counts"]["demo_listings"] == 0
    assert client.post("/api/demo/run").status_code == 200


def test_notes_create_and_patch(client, demo):
    lid = client.get("/api/listings?limit=1").json()["items"][0]["id"]
    r = client.post(f"/api/listings/{lid}/notes", json={"text": "check sleeve length", "flagged": True})
    assert r.status_code == 201, r.text
    n = r.json()["notes"][0]
    assert n["text"] == "check sleeve length" and n["flagged"] is True
    r = client.patch(f"/api/listings/{lid}/notes/{n['id']}", json={"resolved": True})
    assert r.status_code == 200 and r.json()["notes"][0]["resolved"] is True


def test_settings_put_returns_full_payload(client):
    r = client.put("/api/settings", json={"default_platform": "etsy"})
    assert r.status_code == 200
    assert set(r.json()) >= {"settings", "defaults", "env", "credentials_configured", "feedback_labels"}
    assert r.json()["settings"]["default_platform"] == "etsy"
    client.post("/api/settings/reset")
