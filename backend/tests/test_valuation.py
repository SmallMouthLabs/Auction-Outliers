from datetime import UTC, datetime, timedelta

from outlier.valuation.engine import CompInput, valuate

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def sold(i, price, t="exact", sim=0.9, q="high", days=30, **kw):
    return CompInput(id=i, title=f"comp {i}", price=price, is_sold=True, comp_type=t, similarity=sim,
                     evidence_quality=q, sold_date=NOW - timedelta(days=days), **kw)


def test_active_listings_never_feed_valuation():
    comps = [CompInput(id=1, title="asking", price=999, is_sold=False, comp_type="exact", similarity=1.0)]
    v = valuate(comps, NOW)
    assert v.method == "unsupported" and v.expected is None and v.is_speculative
    assert v.active_listing_context["median_asking"] == 999
    assert v.n_sold_comps == 0


def test_mislabeled_active_comp_is_reclassified():
    comps = [CompInput(id=1, title="x", price=50, is_sold=False, comp_type="exact")]
    assert valuate(comps, NOW).n_sold_comps == 0


def test_three_exact_comps_quantiles():
    v = valuate([sold(1, 100), sold(2, 120), sold(3, 140)], NOW)
    assert v.method == "sold_comps"
    assert v.conservative == 100 and v.expected == 120 and v.optimistic == 140
    assert v.evidence_quality == "high" and not v.is_speculative
    assert v.stats["tier_used"] == "exact"


def test_outlier_excluded():
    v = valuate([sold(1, 100), sold(2, 110), sold(3, 120), sold(4, 900)], NOW)
    assert v.n_sold_comps == 3
    assert any(e["id"] == 4 for e in v.excluded)


def test_single_comp_is_low_evidence():
    v = valuate([sold(1, 200)], NOW)
    assert v.expected == 200 and v.conservative == 150
    assert v.evidence_quality == "low" and v.is_speculative


def test_category_only_is_speculative():
    v = valuate([sold(1, 40, t="category", sim=0.3, q="low"), sold(2, 60, t="category", sim=0.3, q="low"), sold(3, 50, t="category", sim=0.3, q="low")], NOW)
    assert v.is_speculative and v.stats["tier_used"] == "category"


def test_shipping_included_is_separated():
    v = valuate([sold(1, 110, shipping_included=True, shipping_amount=10), sold(2, 100), sold(3, 100)], NOW)
    assert v.expected == 100


def test_unsupported_comp_without_price():
    v = valuate([CompInput(id=1, title="no price", price=None, is_sold=True, comp_type="exact")], NOW)
    assert v.method == "unsupported" and v.excluded[0]["reason"] == "no transaction price"
