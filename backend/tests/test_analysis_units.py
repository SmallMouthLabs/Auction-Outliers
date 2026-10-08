from outlier.analysis.discrepancy import detect
from outlier.analysis.prefilter import guess_domain, run_prefilter
from outlier.demo.fixtures import demo_analysis_fixtures
from outlier.settings_store import DEFAULT_SETTINGS

CFG = DEFAULT_SETTINGS["analysis"]
FIX = demo_analysis_fixtures()


def test_domain_guess():
    assert guess_domain("Sterling silver Taxco bracelet", None, None) == "jewelry"
    assert guess_domain("Vintage Pendleton wool shirt jacket mens L", None, None) == "clothing"
    assert guess_domain("Mystery box", None, "Jewelry > Lots") == "jewelry"
    assert guess_domain("Sony walkman", None, None) == "unknown"


def test_prefilter_boosts_and_excludes():
    r = run_prefilter(title="Mohair cardigan made in England", description=None, category=None, current_bid=10, image_count=3, cfg=CFG)
    assert r.passed and "mohair" in r.boost_hits and r.priority > 40
    r = run_prefilter(title="Vintage jacket replica", description=None, category=None, current_bid=10, image_count=3, cfg=CFG)
    assert not r.passed and r.exclude_hits == ["replica"]
    r = run_prefilter(title="Sweater", description=None, category=None, current_bid=10, image_count=0, cfg=CFG)
    assert not r.passed and any("No photographs" in x for x in r.reasons)
    r = run_prefilter(title="Sweater", description=None, category=None, current_bid=900, image_count=1, cfg=CFG)
    assert not r.passed and any("above maximum" in x for x in r.reasons)


def test_discrepancy_rules_jewelry_silver_tone_vs_925():
    deep = FIX["silvertone_necklace:deep"]
    d = detect("Silver Tone Necklace with Blue Stones", "silver tone necklace", deep, "jewelry")
    assert d["signal"] > 0.5
    rule_hits = [f for f in d["findings"] if f["source"] == "rule"]
    assert any("precious-metal" in f["visual_evidence"].lower() for f in rule_hits)
    assert d["note"].startswith("Discrepancies raise research priority")


def test_discrepancy_zero_when_seller_names_everything():
    deep = FIX["leather_jacket_heavy_shipping:deep"]
    d = detect("Schott 618 Leather Motorcycle Jacket Size 42 made in USA NYC", "Schott Perfecto 618", deep, "clothing")
    assert d["signal"] == 0.0 and d["findings"] == []


def test_discrepancy_discounted_by_low_confidence():
    deep = dict(FIX["no_sold_comps:deep"])
    hi = detect("cuff", "", {**deep, "overall_confidence": 0.9}, "jewelry")
    lo = detect("cuff", "", {**deep, "overall_confidence": 0.2}, "jewelry")
    assert lo["signal"] < hi["signal"]
