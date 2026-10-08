"""DEMO MODE fixtures.

Everything in this module is SYNTHETIC. Listings are not real ShopGoodwill auctions, comparables are not real
market transactions, and analysis outputs are canned (not model output). All rows are flagged is_demo=True.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


def _ends(hours: float) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)


def _sold(days_ago: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days_ago)


DEMO_LISTINGS: list[dict[str, Any]] = [
    {
        "key": "mohair_cardigan",
        "title": "Vintage Wool Sweater Womens Medium",
        "description": "Vintage sweater, wool, button front. Some wear. Measures 20 inches pit to pit, 24 inches long.",
        "category": "Clothing > Women's > Sweaters",
        "seller": "Goodwill of Demo County (synthetic)",
        "domain": "clothing",
        "current_bid": 12.00, "num_bids": 2, "ends_at": _ends(30), "shipping_cost": 11.95, "handling_fee": 1.00,
        "measurements": {"pit_to_pit_in": 20, "length_in": 24},
        "condition_text": "Pre-owned, some wear.",
        "images": ["front", "back", "neck label: KINGSTONE DESIGNS", "care label: 75% MOHAIR 25% WOOL MADE IN ENGLAND"],
        "comps": [
            {"title": "Vintage 80s Kingstone Designs Mohair Cardigan England M", "price": 148, "days": 20, "comp_type": "same_maker", "similarity": 0.85, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-1"},
            {"title": "80s Fluffy Mohair Wool Cardigan Made in England Womens M", "price": 125, "days": 45, "comp_type": "same_maker", "similarity": 0.75, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-2"},
            {"title": "Kingstone Designs vintage mohair cardigan (shawl collar)", "price": 170, "days": 70, "comp_type": "exact", "similarity": 0.9, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-3"},
            {"title": "Vintage mohair cardigan (asking)", "price": 240, "is_sold": False, "comp_type": "active", "similarity": 0.8, "evidence_quality": "low", "url": "https://example.invalid/demo-active-1"},
        ],
    },
    {
        "key": "silvertone_necklace",
        "title": "Silver Tone Necklace with Blue Stones",
        "description": "Silver tone necklace, blue stones, 18 inches. Clasp works.",
        "category": "Jewelry > Necklaces",
        "seller": "Goodwill of Demo County (synthetic)",
        "domain": "jewelry",
        "current_bid": 9.99, "num_bids": 1, "ends_at": _ends(52), "shipping_cost": 7.50, "handling_fee": 1.00,
        "measurements": {"length_in": 18},
        "condition_text": "Pre-owned.",
        "images": ["front", "clasp", "back of pendant: 925 MEXICO TC-121", "stone detail"],
        "comps": [
            {"title": "Taxco Mexico 925 sterling link necklace w/ turquoise 18in", "price": 95, "days": 35, "comp_type": "category", "similarity": 0.45, "evidence_quality": "medium", "url": "https://example.invalid/demo-comp-4"},
            {"title": "Vintage Taxco sterling silver necklace blue stones", "price": 120, "days": 80, "comp_type": "category", "similarity": 0.5, "evidence_quality": "medium", "url": "https://example.invalid/demo-comp-5"},
        ],
    },
    {
        "key": "leather_jacket_heavy_shipping",
        "title": "Schott Leather Motorcycle Jacket Size 42",
        "description": "Schott Perfecto 618 leather jacket, size 42, heavy. Zippers work, lining intact.",
        "category": "Clothing > Men's > Coats & Jackets",
        "seller": "Goodwill of Demo County (synthetic)",
        "domain": "clothing",
        "current_bid": 61.00, "num_bids": 9, "ends_at": _ends(20), "shipping_cost": 64.90, "handling_fee": 2.00,
        "measurements": {"pit_to_pit_in": 22, "length_in": 25},
        "condition_text": "Good pre-owned condition.",
        "images": ["front", "back", "label: SCHOTT N.Y.C. 618 MADE IN USA", "zipper detail"],
        "comps": [
            {"title": "Schott 618 Perfecto leather motorcycle jacket 42", "price": 240, "days": 12, "comp_type": "exact", "similarity": 0.95, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-6"},
            {"title": "Schott NYC 618 steerhide jacket size 42 vintage", "price": 265, "days": 30, "comp_type": "exact", "similarity": 0.9, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-7"},
            {"title": "Schott Perfecto 618 42 USA", "price": 210, "days": 55, "comp_type": "exact", "similarity": 0.9, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-8"},
        ],
        "assumptions": {"outgoing_shipping": 28.0},
    },
    {
        "key": "damaged_designer_sweater",
        "title": "Missoni Knit Sweater Mens Large",
        "description": "Missoni sweater, zigzag pattern, made in Italy. Several moth holes on front and sleeve, see photos.",
        "category": "Clothing > Men's > Sweaters",
        "seller": "Goodwill of Demo County (synthetic)",
        "domain": "clothing",
        "current_bid": 18.00, "num_bids": 3, "ends_at": _ends(70), "shipping_cost": 12.50, "handling_fee": 1.00,
        "measurements": {"pit_to_pit_in": 23, "length_in": 27},
        "condition_text": "Damaged: multiple moth holes.",
        "images": ["front", "label: MISSONI MADE IN ITALY", "moth holes detail", "sleeve damage"],
        "comps": [
            {"title": "Missoni mens zigzag wool sweater L Italy", "price": 160, "days": 15, "comp_type": "same_maker", "similarity": 0.7, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-9", "condition": "excellent"},
            {"title": "Missoni vintage knit sweater L (small holes)", "price": 55, "days": 40, "comp_type": "same_maker", "similarity": 0.8, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-10", "condition": "damaged"},
            {"title": "Missoni sweater mens large repaired", "price": 70, "days": 60, "comp_type": "same_maker", "similarity": 0.75, "evidence_quality": "medium", "url": "https://example.invalid/demo-comp-11", "condition": "repaired"},
        ],
        "assumptions": {"cleaning_repair_cost": 25.0},
    },
    {
        "key": "jewelry_lot",
        "title": "Lot of Costume Jewelry Brooches Pins",
        "description": "Mixed lot of 12 pins and brooches, costume jewelry. Sold as is.",
        "category": "Jewelry > Lots",
        "seller": "Goodwill of Demo County (synthetic)",
        "domain": "jewelry",
        "current_bid": 14.00, "num_bids": 4, "ends_at": _ends(90), "shipping_cost": 9.95, "handling_fee": 1.00,
        "measurements": {},
        "condition_text": "As is.",
        "images": ["lot overview", "brooch 3 back: EISENBERG ICE", "brooch 7 back: STERLING DANECRAFT", "brooch 11 front"],
        "comps": [
            {"title": "Eisenberg Ice rhinestone brooch signed", "price": 48, "days": 25, "comp_type": "same_maker", "similarity": 0.6, "evidence_quality": "medium", "url": "https://example.invalid/demo-comp-12"},
            {"title": "Danecraft sterling leaf brooch", "price": 32, "days": 50, "comp_type": "same_maker", "similarity": 0.55, "evidence_quality": "medium", "url": "https://example.invalid/demo-comp-13"},
            {"title": "Vintage costume brooch lot 10 pcs", "price": 28, "days": 10, "comp_type": "category", "similarity": 0.35, "evidence_quality": "low", "url": "https://example.invalid/demo-comp-14"},
        ],
    },
    {
        "key": "no_sold_comps",
        "title": "Vintage Studio Silver Cuff Bracelet Modernist",
        "description": "Heavy modernist cuff, hand made, signed on inside, unknown maker. 48 grams.",
        "category": "Jewelry > Bracelets",
        "seller": "Goodwill of Demo County (synthetic)",
        "domain": "jewelry",
        "current_bid": 26.00, "num_bids": 5, "ends_at": _ends(10), "shipping_cost": 6.50, "handling_fee": 1.00,
        "measurements": {"weight_g": 48},
        "condition_text": "Good.",
        "images": ["front", "inside signature: illegible cursive + STERLING", "profile"],
        "comps": [
            {"title": "Modernist sterling cuff (asking, dealer)", "price": 650, "is_sold": False, "comp_type": "active", "similarity": 0.6, "evidence_quality": "low", "url": "https://example.invalid/demo-active-2"},
            {"title": "Studio sterling cuff bracelet modernist (asking)", "price": 420, "is_sold": False, "comp_type": "active", "similarity": 0.5, "evidence_quality": "low", "url": "https://example.invalid/demo-active-3"},
        ],
    },
    {
        "key": "carhartt_over_max",
        "title": "Mens Brown Work Jacket XL",
        "description": "Brown canvas jacket with blanket lining. XL.",
        "category": "Clothing > Men's > Coats & Jackets",
        "seller": "Goodwill of Demo County (synthetic)",
        "domain": "clothing",
        "current_bid": 72.00, "num_bids": 14, "ends_at": _ends(3), "shipping_cost": 16.95, "handling_fee": 1.00,
        "measurements": {"pit_to_pit_in": 26, "length_in": 27},
        "condition_text": "Pre-owned, fading.",
        "images": ["front", "label: CARHARTT MADE IN USA J97 BRN", "blanket lining", "back"],
        "comps": [
            {"title": "Vintage Carhartt Detroit jacket J97 USA blanket lined XL", "price": 118, "days": 9, "comp_type": "exact", "similarity": 0.9, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-15"},
            {"title": "Carhartt Detroit J97 brown XL made in USA 90s", "price": 135, "days": 22, "comp_type": "exact", "similarity": 0.9, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-16"},
            {"title": "Carhartt J97 blanket lined chore Detroit XL", "price": 104, "days": 40, "comp_type": "exact", "similarity": 0.85, "evidence_quality": "high", "url": "https://example.invalid/demo-comp-17"},
        ],
    },
]


def _obs(text: str, idx: int | None = None, region: str | None = None) -> dict[str, Any]:
    return {"text": text, "image_index": idx, "region": region}


def _lbl(text: str, t: str, idx: int, leg: str = "clear") -> dict[str, Any]:
    return {"text": text, "label_type": t, "image_index": idx, "legibility": leg}


def _cand(label: str, brand: str | None, conf: float, ev: list[str], counter: list[str] | None = None, status: str = "inferred") -> dict[str, Any]:
    return {"label": label, "brand_or_maker": brand, "confidence": conf, "evidence": ev, "counter_evidence": counter or [], "status": status}


def _vi(ind: str, why: str, strength: str = "moderate") -> dict[str, Any]:
    return {"indicator": ind, "why_it_matters": why, "strength": strength}


def _disc(claim: str, vis: str, strength: str = "moderate", idx: int | None = None) -> dict[str, Any]:
    return {"seller_claim": claim, "visual_evidence": vis, "direction": "seller_undervalues", "strength": strength, "image_index": idx}


def _rq(q: str, purpose: str = "sold comps") -> dict[str, Any]:
    return {"query": q, "marketplace": "ebay", "purpose": purpose}


def _triage(domain: str, summary: str, obs: list, text: list, cands: list, vis: list, flags: list, score: int, esc: bool,
            reason: str, inspect: list[int], mismatch: str | None) -> dict[str, Any]:
    return {"domain": domain, "item_summary": summary, "observations": obs, "visible_text": text, "quick_candidates": cands,
            "value_indicators": vis, "red_flags": flags, "interest_score": score, "escalate": esc, "escalate_reason": reason,
            "images_to_inspect": inspect, "seller_vs_visual_mismatch": mismatch}


def demo_analysis_fixtures() -> dict[str, dict[str, Any]]:
    f: dict[str, dict[str, Any]] = {}

    f["mohair_cardigan:triage"] = _triage(
        "clothing", "Fluffy brushed-knit cardigan, shawl collar, button front",
        [_obs("Long brushed pile consistent with mohair blend", 0, "body"), _obs("Woven neck label with brand name", 2, "neck label"),
         _obs("Care label lists fibre content and country", 3, "care label")],
        [_lbl("KINGSTONE DESIGNS", "brand label", 2), _lbl("75% MOHAIR 25% WOOL MADE IN ENGLAND", "care label", 3)],
        [_cand("1980s English mohair cardigan (Kingstone Designs)", "Kingstone Designs", 0.7, ["brand label", "mohair content label"])],
        [_vi("Mohair content 75%", "High-mohair English knits have strong collector demand", "strong")],
        [], 82, True, "Seller calls it 'wool sweater'; label shows a 75% mohair English maker.", [2, 3],
        "Seller omits mohair content and brand.",
    )
    f["mohair_cardigan:deep"] = {
        "domain": "clothing",
        "headline_identification": "1980s Kingstone Designs 75% mohair shawl-collar cardigan, made in England",
        "overall_confidence": 0.82,
        "observed_facts": [_obs("Brushed long-pile knit with visible halo", 0, "body"), _obs("Woven label reads KINGSTONE DESIGNS", 2, "neck label"),
                           _obs("Care label: 75% MOHAIR 25% WOOL MADE IN ENGLAND", 3, "care label"), _obs("Shawl collar, five buttons", 0)],
        "candidates": [
            _cand("Kingstone Designs mohair cardigan, 1980s", "Kingstone Designs", 0.82, ["brand label legible", "fibre label", "construction consistent with 80s English mohair knits"], status="observed"),
            _cand("Unbranded English mohair blend, later reproduction label", None, 0.1, ["none"], ["label style consistent with period"]),
        ],
        "alternative_explanations": ["Label could be transplanted (unlikely; stitching matches)."],
        "clothing": {
            "garment_type": "cardigan", "brand_or_manufacturer": "Kingstone Designs", "brand_confidence": 0.85,
            "label_texts": [_lbl("KINGSTONE DESIGNS", "brand label", 2), _lbl("75% MOHAIR 25% WOOL MADE IN ENGLAND", "care label", 3)],
            "era_estimate": "1980s", "era_evidence": ["label typography", "shawl collar silhouette"],
            "fabric_and_construction": ["75% mohair / 25% wool brushed knit"], "stitching_and_seams": ["linked seams"],
            "country_of_manufacture": "England", "country_evidence": "care label", "graphics_or_prints": None,
            "model_names_or_numbers": [], "size_and_measurements": "~M (20in p2p, 24in length)",
            "collectible_characteristics": ["high mohair content", "English maker"],
            "authenticity_indicators": ["period-correct woven label"], "expert_inspection_points": ["check for felting/pilling in hand"],
        },
        "jewelry": None,
        "condition_issues": [{"issue": "general wear noted by seller", "severity": "minor", "image_index": None}],
        "value_indicators": [_vi("75% mohair, made in England", "Collector demand for high-mohair knits", "strong")],
        "discrepancies": [_disc("'Vintage wool sweater'", "Label: 75% mohair, named English maker", "strong", 3)],
        "missing_information": ["sleeve length", "any holes/felting"],
        "research_queries": [_rq("Kingstone Designs mohair cardigan"), _rq("vintage 80s mohair cardigan made in England shawl collar")],
        "warrants_further_research": True, "research_rationale": "Named maker and premium fibre not reflected in title.",
        "demand_indicator": "high", "liquidity_indicator": "high", "risk_flags": [],
    }

    f["silvertone_necklace:triage"] = _triage(
        "jewelry", "Link necklace with blue cabochon stones; back of pendant bears stamped marks",
        [_obs("Stamped marks on pendant reverse", 2, "back of pendant"), _obs("Bezel-set blue stones, possibly turquoise", 3)],
        [_lbl("925 MEXICO TC-121", "hallmark", 2, "partial")],
        [_cand("Mexican sterling (Taxco) necklace", None, 0.5, ["'925 MEXICO' stamp", "TC- registry-style mark"])],
        [_vi("Apparent 925 + Mexico + TC registry mark", "Could indicate Taxco sterling rather than 'silver tone'", "strong")],
        [], 78, True, "Seller says 'silver tone' but a 925/MEXICO stamp is visible (unverified).", [2],
        "Seller describes as silver tone; stamp suggests sterling.",
    )
    f["silvertone_necklace:deep"] = {
        "domain": "jewelry",
        "headline_identification": "Possible Taxco (Mexico) sterling link necklace with blue stones, maker TC-121 (unverified)",
        "overall_confidence": 0.55,
        "observed_facts": [_obs("Stamp reads '925 MEXICO TC-121' (TC-121 partially legible)", 2, "pendant reverse"),
                           _obs("Blue opaque cabochons in bezels", 3), _obs("Heavy cast links", 0)],
        "candidates": [
            _cand("Taxco sterling necklace, 1970s-90s, workshop TC-121", None, 0.55, ["925 MEXICO stamp", "TC- eagle-era successor registry mark style"], ["stamp could be spurious; metal untested"]),
            _cand("Silver-plated base metal with fake stamp", None, 0.2, ["cannot verify metal"], ["weight and wear pattern look like sterling"]),
        ],
        "alternative_explanations": ["Stones may be dyed howlite rather than turquoise."],
        "clothing": None,
        "jewelry": {
            "jewelry_type": "necklace",
            "makers_marks": [_lbl("TC-121", "maker's mark", 2, "partial")],
            "hallmarks_and_inscriptions": [_lbl("925 MEXICO", "hallmark", 2)],
            "design_characteristics": ["cast links", "bezel-set cabochons"],
            "materials": [{"material": "sterling silver", "basis": ["'925' stamp", "wear/tarnish pattern"], "confidence": 0.6, "verification_needed": "acid test or XRF; weigh"},
                          {"material": "turquoise (or dyed howlite)", "basis": ["opaque blue cabochons"], "confidence": 0.4, "verification_needed": "loupe for matrix/dye"}],
            "construction_techniques": ["casting", "bezel setting"],
            "potential_maker": "Taxco workshop TC-121", "maker_confidence": 0.45,
            "stylistic_period": "1970s-1990s", "period_evidence": ["TC- registry mark system introduced late 1970s"],
            "stones_or_other_materials": ["blue cabochons"], "collectible_characteristics": ["Mexican silver"],
            "authenticity_concerns": ["metal content unverified", "stamp partially legible"],
            "lot_components": [], "melt_value_note": "Not computed: metal content and weight are unverified.",
        },
        "condition_issues": [],
        "value_indicators": [_vi("925 MEXICO stamp", "Taxco sterling resells well when verified", "moderate")],
        "discrepancies": [_disc("'Silver tone necklace'", "925 MEXICO stamp visible on reverse (unverified)", "strong", 2)],
        "missing_information": ["weight in grams", "clear photo of full mark", "acid/XRF test"],
        "research_queries": [_rq("Taxco TC-121 sterling necklace"), _rq("Taxco 925 necklace turquoise cabochon link")],
        "warrants_further_research": True, "research_rationale": "Stamp contradicts seller description; metal must be verified.",
        "demand_indicator": "medium", "liquidity_indicator": "medium", "risk_flags": ["precious metal unverified"],
    }

    f["leather_jacket_heavy_shipping:triage"] = _triage(
        "clothing", "Black leather asymmetrical motorcycle jacket with belted waist",
        [_obs("Woven label SCHOTT N.Y.C. with style number", 2, "label"), _obs("Heavy-duty zippers", 3)],
        [_lbl("SCHOTT N.Y.C. 618 MADE IN USA", "brand label", 2)],
        [_cand("Schott Perfecto 618", "Schott", 0.9, ["label with style number"])],
        [_vi("Schott 618 made in USA", "Iconic model with liquid resale", "strong")],
        [], 70, True, "Known desirable model; confirm era from label style.", [2], None,
    )
    f["leather_jacket_heavy_shipping:deep"] = {
        "domain": "clothing", "headline_identification": "Schott Perfecto 618 steerhide motorcycle jacket, size 42, made in USA",
        "overall_confidence": 0.9,
        "observed_facts": [_obs("Label: SCHOTT N.Y.C. 618 MADE IN USA", 2), _obs("Asymmetrical zip, belted waist, epaulets", 0)],
        "candidates": [_cand("Schott Perfecto 618, 1990s-2000s", "Schott", 0.9, ["label", "hardware", "silhouette"], status="observed")],
        "alternative_explanations": [],
        "clothing": {"garment_type": "leather motorcycle jacket", "brand_or_manufacturer": "Schott", "brand_confidence": 0.95,
                     "label_texts": [_lbl("SCHOTT N.Y.C. 618 MADE IN USA", "brand label", 2)], "era_estimate": "1990s-2000s",
                     "era_evidence": ["label style"], "fabric_and_construction": ["steerhide", "quilted lining"],
                     "stitching_and_seams": [], "country_of_manufacture": "USA", "country_evidence": "label", "graphics_or_prints": None,
                     "model_names_or_numbers": ["618"], "size_and_measurements": "42", "collectible_characteristics": ["Perfecto 618"],
                     "authenticity_indicators": ["correct label"], "expert_inspection_points": ["check leather for cracking"]},
        "jewelry": None, "condition_issues": [],
        "value_indicators": [_vi("Schott 618", "Strong sold history", "strong")],
        "discrepancies": [], "missing_information": [],
        "research_queries": [_rq("Schott 618 Perfecto 42")], "warrants_further_research": False,
        "research_rationale": "Already correctly identified by seller; value depends on economics (heavy shipping).",
        "demand_indicator": "high", "liquidity_indicator": "high", "risk_flags": [],
    }

    f["damaged_designer_sweater:triage"] = _triage(
        "clothing", "Multicolour zigzag knit sweater with visible holes",
        [_obs("Label MISSONI MADE IN ITALY", 1, "label"), _obs("Several moth holes on front", 2), _obs("Holes on sleeve", 3)],
        [_lbl("MISSONI MADE IN ITALY", "brand label", 1)],
        [_cand("Missoni zigzag knit sweater", "Missoni", 0.85, ["label", "signature zigzag"])],
        [_vi("Missoni signature knit", "Designer knitwear with demand", "strong")],
        ["multiple moth holes"], 60, True, "Designer piece but condition is a major factor.", [2, 3], None,
    )
    f["damaged_designer_sweater:deep"] = {
        "domain": "clothing", "headline_identification": "Missoni zigzag wool-blend sweater, made in Italy (damaged: moth holes)",
        "overall_confidence": 0.85,
        "observed_facts": [_obs("Label MISSONI MADE IN ITALY", 1), _obs("At least 5 moth holes front, 2 on sleeve", 2)],
        "candidates": [_cand("Missoni mainline knit, 1990s-2000s", "Missoni", 0.85, ["label", "pattern"], status="observed")],
        "alternative_explanations": ["Could be Missoni Sport diffusion line (label not fully shown)."],
        "clothing": {"garment_type": "sweater", "brand_or_manufacturer": "Missoni", "brand_confidence": 0.85,
                     "label_texts": [_lbl("MISSONI MADE IN ITALY", "brand label", 1)], "era_estimate": "1990s-2000s", "era_evidence": ["label"],
                     "fabric_and_construction": ["space-dyed zigzag knit"], "stitching_and_seams": [], "country_of_manufacture": "Italy",
                     "country_evidence": "label", "graphics_or_prints": "zigzag", "model_names_or_numbers": [], "size_and_measurements": "L",
                     "collectible_characteristics": ["signature pattern"], "authenticity_indicators": [], "expert_inspection_points": ["count and size holes; reweave cost"]},
        "jewelry": None,
        "condition_issues": [{"issue": "multiple moth holes front", "severity": "major", "image_index": 2}, {"issue": "holes on sleeve", "severity": "moderate", "image_index": 3}],
        "value_indicators": [_vi("Missoni", "Designer demand", "strong")],
        "discrepancies": [], "missing_information": ["fibre content label"],
        "research_queries": [_rq("Missoni sweater mens L zigzag"), _rq("Missoni sweater damaged holes", "damaged comps")],
        "warrants_further_research": True, "research_rationale": "Value hinges on damaged-condition comps and repair cost.",
        "demand_indicator": "high", "liquidity_indicator": "medium", "risk_flags": ["significant damage", "possible diffusion line"],
    }

    f["jewelry_lot:triage"] = _triage(
        "jewelry", "Lot of ~12 brooches; at least two carry maker signatures",
        [_obs("Brooch 3 reverse stamped EISENBERG ICE", 1), _obs("Brooch 7 reverse stamped STERLING DANECRAFT", 2)],
        [_lbl("EISENBERG ICE", "maker's mark", 1), _lbl("STERLING DANECRAFT", "maker's mark", 2)],
        [_cand("Mixed lot containing signed Eisenberg Ice and Danecraft sterling pieces", None, 0.6, ["stamps"])],
        [_vi("Signed pieces inside a 'costume' lot", "Signed brooches resell individually", "moderate")],
        [], 72, True, "Lot described as costume contains at least two signed pieces.", [1, 2],
        "Seller does not mention signed pieces.",
    )
    f["jewelry_lot:deep"] = {
        "domain": "jewelry", "headline_identification": "Brooch lot incl. signed Eisenberg Ice rhinestone brooch and Danecraft sterling brooch",
        "overall_confidence": 0.65,
        "observed_facts": [_obs("EISENBERG ICE stamp", 1), _obs("STERLING DANECRAFT stamp", 2), _obs("Remaining pieces unsigned", 0)],
        "candidates": [_cand("Eisenberg Ice brooch (1950s-70s)", "Eisenberg", 0.7, ["stamp"]), _cand("Danecraft sterling brooch (1940s-50s)", "Danecraft", 0.7, ["stamp"])],
        "alternative_explanations": ["Stamps could be on later reissues."],
        "clothing": None,
        "jewelry": {"jewelry_type": "brooch lot", "makers_marks": [_lbl("EISENBERG ICE", "maker's mark", 1), _lbl("DANECRAFT", "maker's mark", 2)],
                    "hallmarks_and_inscriptions": [_lbl("STERLING", "hallmark", 2)], "design_characteristics": ["rhinestone cluster", "leaf motif"],
                    "materials": [{"material": "sterling silver (Danecraft piece)", "basis": ["STERLING stamp"], "confidence": 0.6, "verification_needed": "test"},
                                  {"material": "rhodium-plated base metal with rhinestones (Eisenberg)", "basis": ["typical construction"], "confidence": 0.6, "verification_needed": None}],
                    "construction_techniques": ["prong-set rhinestones", "cast sterling"], "potential_maker": "Eisenberg; Danecraft", "maker_confidence": 0.7,
                    "stylistic_period": "1940s-1970s", "period_evidence": ["mark styles"], "stones_or_other_materials": ["rhinestones"],
                    "collectible_characteristics": ["signed"], "authenticity_concerns": [],
                    "lot_components": [{"description": "Eisenberg Ice rhinestone brooch", "image_index": 1, "why_interesting": "signed, collectible", "candidate": "Eisenberg Ice", "confidence": 0.7},
                                       {"description": "Danecraft sterling leaf brooch", "image_index": 2, "why_interesting": "sterling, signed", "candidate": "Danecraft", "confidence": 0.7},
                                       {"description": "Unsigned enamel flower brooch", "image_index": 3, "why_interesting": "could be signed on back; not shown", "candidate": None, "confidence": 0.2}],
                    "melt_value_note": "Not computed: metal content and weight are unverified."},
        "condition_issues": [], "value_indicators": [_vi("Two signed pieces", "Individual resale beats lot price", "moderate")],
        "discrepancies": [_disc("'Costume jewelry lot'", "Signed Eisenberg Ice and sterling Danecraft pieces visible", "moderate", 1)],
        "missing_information": ["backs of the other 10 pieces"],
        "research_queries": [_rq("Eisenberg Ice brooch"), _rq("Danecraft sterling brooch")],
        "warrants_further_research": True, "research_rationale": "Signed components not reflected in lot description.",
        "demand_indicator": "medium", "liquidity_indicator": "medium", "risk_flags": [],
    }

    f["no_sold_comps:triage"] = _triage(
        "jewelry", "Heavy hand-wrought modernist cuff with an illegible signature",
        [_obs("Hammered texture, asymmetric form", 0), _obs("Inside: STERLING and cursive signature (illegible)", 1)],
        [_lbl("STERLING", "hallmark", 1), _lbl("??? (cursive)", "maker's mark", 1, "poor")],
        [_cand("Studio modernist sterling cuff, mid-century", None, 0.4, ["form", "signature present"])],
        [_vi("Signed studio piece", "Could be a collectible American studio maker", "moderate")],
        [], 68, True, "Illegible signature could be a known studio maker; needs identification.", [1], None,
    )
    f["no_sold_comps:deep"] = {
        "domain": "jewelry", "headline_identification": "Signed modernist sterling cuff, maker unidentified (signature illegible)",
        "overall_confidence": 0.35,
        "observed_facts": [_obs("STERLING stamp inside", 1), _obs("Cursive signature, not legible even enlarged", 1), _obs("Weight claimed 48 g by seller", None)],
        "candidates": [_cand("American studio jeweler, 1960s-70s", None, 0.35, ["hammered modernist form", "signature"], ["signature unread"])],
        "alternative_explanations": ["Contemporary artisan piece", "Mexican modernist (no eagle mark seen)"],
        "clothing": None,
        "jewelry": {"jewelry_type": "cuff bracelet", "makers_marks": [_lbl("??? cursive", "maker's mark", 1, "poor")], "hallmarks_and_inscriptions": [_lbl("STERLING", "hallmark", 1)],
                    "design_characteristics": ["hammered", "asymmetric"], "materials": [{"material": "sterling silver", "basis": ["STERLING stamp", "weight"], "confidence": 0.6, "verification_needed": "test"}],
                    "construction_techniques": ["forging", "hammering"], "potential_maker": None, "maker_confidence": 0.0, "stylistic_period": "1960s-1970s",
                    "period_evidence": ["style"], "stones_or_other_materials": [], "collectible_characteristics": ["studio-made"], "authenticity_concerns": ["maker unknown"],
                    "lot_components": [], "melt_value_note": "Not computed: metal content and weight are unverified."},
        "condition_issues": [], "value_indicators": [_vi("Studio modernist, signed", "Known makers command premiums; unknown makers do not", "weak")],
        "discrepancies": [], "missing_information": ["legible signature photo", "verified weight"],
        "research_queries": [_rq("modernist sterling cuff signed hammered"), _rq("studio sterling cuff 1970s signed")],
        "warrants_further_research": True, "research_rationale": "High upside only if the maker can be identified.",
        "demand_indicator": "unknown", "liquidity_indicator": "low", "risk_flags": ["maker unidentified", "metal unverified"],
    }

    f["carhartt_over_max:triage"] = _triage(
        "clothing", "Brown duck canvas chore jacket with blanket lining",
        [_obs("Label CARHARTT MADE IN USA J97 BRN", 1), _obs("Blanket lining", 2)],
        [_lbl("CARHARTT MADE IN USA J97 BRN", "brand label", 1)],
        [_cand("Carhartt Detroit jacket J97, USA-made 1990s", "Carhartt", 0.85, ["label with style code"])],
        [_vi("USA-made Carhartt J97", "Strong streetwear demand", "strong")], [], 75, True, "Seller omits brand entirely.", [1],
        "Seller title 'work jacket' omits Carhartt and model.",
    )
    f["carhartt_over_max:deep"] = {
        "domain": "clothing", "headline_identification": "Carhartt Detroit jacket J97, blanket-lined, made in USA (1990s), XL",
        "overall_confidence": 0.88,
        "observed_facts": [_obs("Label CARHARTT MADE IN USA J97 BRN", 1), _obs("Blanket lining, corduroy collar", 2)],
        "candidates": [_cand("Carhartt J97 Detroit jacket, 1990s USA", "Carhartt", 0.88, ["label", "construction"], status="observed")],
        "alternative_explanations": [],
        "clothing": {"garment_type": "chore jacket", "brand_or_manufacturer": "Carhartt", "brand_confidence": 0.95,
                     "label_texts": [_lbl("CARHARTT MADE IN USA J97 BRN", "brand label", 1)], "era_estimate": "1990s", "era_evidence": ["label style", "USA production"],
                     "fabric_and_construction": ["duck canvas", "blanket lining"], "stitching_and_seams": ["triple stitched"], "country_of_manufacture": "USA",
                     "country_evidence": "label", "graphics_or_prints": None, "model_names_or_numbers": ["J97"], "size_and_measurements": "XL",
                     "collectible_characteristics": ["USA-made Detroit"], "authenticity_indicators": ["label"], "expert_inspection_points": []},
        "jewelry": None, "condition_issues": [{"issue": "fading", "severity": "minor", "image_index": 0}],
        "value_indicators": [_vi("Carhartt J97 USA", "Liquid, in-demand", "strong")],
        "discrepancies": [_disc("'Mens brown work jacket'", "Carhartt J97 label", "strong", 1)],
        "missing_information": [], "research_queries": [_rq("Carhartt Detroit J97 XL USA")],
        "warrants_further_research": False, "research_rationale": "Identified; but bidding already active.",
        "demand_indicator": "high", "liquidity_indicator": "high", "risk_flags": [],
    }
    return f


SEED_REFERENCES: list[dict[str, Any]] = [
    # NOTE: typical ranges are rough guidance from general market knowledge, not sold comps. Verify before relying on them.
    {"name": "Carhartt Detroit jacket (J97/J01) USA-made", "entry_type": "product", "domain": "clothing", "category": "workwear",
     "characteristics": "Duck canvas, blanket-lined, corduroy collar; 'Made in USA' label pre-2000s; style codes J97 (blanket) / J01 (Detroit).",
     "identifiers": ["J97", "J01", "carhartt made in usa"], "keywords": ["carhartt", "detroit", "chore", "blanket lined", "duck"],
     "typical_low": 80, "typical_high": 200, "demand": "high", "liquidity": "high"},
    {"name": "Schott Perfecto 618/613", "entry_type": "product", "domain": "clothing", "category": "leather jackets",
     "characteristics": "Steerhide asymmetrical motorcycle jacket; style numbers on label; made in USA.",
     "identifiers": ["618", "613", "perfecto"], "keywords": ["schott", "perfecto", "steerhide", "motorcycle jacket"],
     "typical_low": 180, "typical_high": 400, "demand": "high", "liquidity": "high"},
    {"name": "Levi's Big E / redline selvedge denim", "entry_type": "characteristic", "domain": "clothing", "category": "denim",
     "characteristics": "Capital 'E' on red tab (pre-1971); redline selvedge; single stitch back pocket; paper patch.",
     "identifiers": ["big e", "redline", "selvedge", "501xx"], "keywords": ["levi", "levis", "501", "selvedge", "selvage", "big e", "redline"],
     "typical_low": 150, "typical_high": 1500, "demand": "high", "liquidity": "medium"},
    {"name": "Lee 101J / Storm Rider", "entry_type": "product", "domain": "clothing", "category": "denim jackets",
     "characteristics": "Blanket-lined Storm Rider; Sanforized labels; Union Made tags date the piece.", "identifiers": ["101j", "storm rider"],
     "keywords": ["lee", "storm rider", "101j", "union made"], "typical_low": 90, "typical_high": 400, "demand": "high", "liquidity": "medium"},
    {"name": "Pendleton wool shirts/jackets (vintage)", "entry_type": "brand", "domain": "clothing", "category": "knitwear/outerwear",
     "characteristics": "Virgin wool; blue/gold label with 'Portland Oregon'; older labels lack size tags.", "identifiers": ["pendleton"],
     "keywords": ["pendleton", "virgin wool", "portland"], "typical_low": 40, "typical_high": 150, "demand": "medium", "liquidity": "high"},
    {"name": "Harris Tweed", "entry_type": "characteristic", "domain": "clothing", "category": "tailoring",
     "characteristics": "Orb label certifying hand-woven Outer Hebrides tweed.", "identifiers": ["harris tweed", "orb"], "keywords": ["harris tweed"],
     "typical_low": 40, "typical_high": 150, "demand": "medium", "liquidity": "medium"},
    {"name": "Mohair knitwear (English/Scottish 1980s)", "entry_type": "characteristic", "domain": "clothing", "category": "knitwear",
     "characteristics": "High mohair content (60%+), brushed halo; makers incl. Kingstone, Jaeger, Ballantyne.", "identifiers": ["mohair"],
     "keywords": ["mohair", "kingstone", "jaeger", "ballantyne"], "typical_low": 80, "typical_high": 250, "demand": "high", "liquidity": "high"},
    {"name": "Missoni knitwear", "entry_type": "brand", "domain": "clothing", "category": "designer knitwear",
     "characteristics": "Space-dyed zigzag/chevron knits, made in Italy; mainline vs Missoni Sport diffusion.", "identifiers": ["missoni"],
     "keywords": ["missoni", "zigzag", "chevron"], "typical_low": 80, "typical_high": 350, "demand": "high", "liquidity": "medium"},
    {"name": "Coogi knit sweaters", "entry_type": "brand", "domain": "clothing", "category": "knitwear",
     "characteristics": "3D textured multicolour knits, made in Australia (older) vs later imports.", "identifiers": ["coogi"],
     "keywords": ["coogi", "australia"], "typical_low": 100, "typical_high": 400, "demand": "high", "liquidity": "high"},
    {"name": "Single-stitch vintage band/graphic tees", "entry_type": "characteristic", "domain": "clothing", "category": "t-shirts",
     "characteristics": "Single-stitch hems (pre-mid-90s), 50/50 blends, tags like Screen Stars, Hanes Beefy, Brockum, Giant.",
     "identifiers": ["single stitch", "screen stars", "brockum"], "keywords": ["single stitch", "band tee", "tour", "screen stars", "brockum", "giant"],
     "typical_low": 60, "typical_high": 600, "demand": "high", "liquidity": "high"},
    {"name": "Issey Miyake Pleats Please", "entry_type": "brand", "domain": "clothing", "category": "designer",
     "characteristics": "Permanent micro-pleated polyester; labels 'PLEATS PLEASE ISSEY MIYAKE', Japanese sizing 2-5.", "identifiers": ["pleats please", "issey miyake"],
     "keywords": ["issey miyake", "pleats please", "pleated"], "typical_low": 120, "typical_high": 500, "demand": "high", "liquidity": "high"},
    {"name": "Comme des Garçons / Yohji Yamamoto archival", "entry_type": "designer", "domain": "clothing", "category": "designer",
     "characteristics": "AD-year labels (CdG), 'Yohji Yamamoto Pour Homme' labels; made in Japan.", "identifiers": ["comme des garcons", "yohji yamamoto", "ad19", "ad20"],
     "keywords": ["comme des garcons", "cdg", "yohji", "yamamoto"], "typical_low": 150, "typical_high": 1500, "demand": "high", "liquidity": "medium"},
    {"name": "Georg Jensen", "entry_type": "maker_mark", "domain": "jewelry", "category": "Danish silver",
     "characteristics": "Dotted oval 'GEORG JENSEN' mark, design numbers, 'DENMARK 925 S'.", "identifiers": ["georg jensen", "925 s denmark"],
     "keywords": ["georg jensen", "jensen", "denmark"], "typical_low": 150, "typical_high": 1200, "demand": "high", "liquidity": "high"},
    {"name": "William Spratling (Taxco)", "entry_type": "maker_mark", "domain": "jewelry", "category": "Mexican silver",
     "characteristics": "Spratling script/print marks; early 'WS' conjoined; 980/925 silver; Taxco.", "identifiers": ["spratling", "ws", "980"],
     "keywords": ["spratling", "taxco", "980"], "typical_low": 300, "typical_high": 3000, "demand": "high", "liquidity": "medium"},
    {"name": "Taxco sterling (TC-/TS- registry marks, eagle marks)", "entry_type": "characteristic", "domain": "jewelry", "category": "Mexican silver",
     "characteristics": "Eagle assay marks (1948-1979) then letter-number registry (e.g. TC-121); '925 MEXICO'.", "identifiers": ["taxco", "925 mexico", "eagle"],
     "keywords": ["taxco", "mexico", "925", "eagle"], "typical_low": 40, "typical_high": 400, "demand": "medium", "liquidity": "high"},
    {"name": "Margot de Taxco", "entry_type": "maker_mark", "domain": "jewelry", "category": "Mexican silver",
     "characteristics": "Enamel on sterling; marked 'Margot de Taxco' with design numbers.", "identifiers": ["margot de taxco"],
     "keywords": ["margot", "taxco", "enamel"], "typical_low": 150, "typical_high": 1500, "demand": "high", "liquidity": "medium"},
    {"name": "Ed Levin", "entry_type": "maker_mark", "domain": "jewelry", "category": "American studio",
     "characteristics": "Modernist sterling, 'Ed Levin' or 'EL' marks, hand-forged.", "identifiers": ["ed levin"],
     "keywords": ["ed levin", "modernist"], "typical_low": 80, "typical_high": 500, "demand": "medium", "liquidity": "medium"},
    {"name": "Kalo Shop (Chicago Arts & Crafts)", "entry_type": "maker_mark", "domain": "jewelry", "category": "American studio",
     "characteristics": "'KALO' mark, hand-wrought sterling, Arts & Crafts period.", "identifiers": ["kalo"], "keywords": ["kalo", "hand wrought", "arts and crafts"],
     "typical_low": 150, "typical_high": 1500, "demand": "high", "liquidity": "medium"},
    {"name": "Navajo / Zuni sterling (hallmarked)", "entry_type": "characteristic", "domain": "jewelry", "category": "Native American",
     "characteristics": "Artist hallmarks, sterling, natural turquoise; squash blossoms, cuffs, concho belts.", "identifiers": ["navajo", "zuni", "hopi"],
     "keywords": ["navajo", "zuni", "hopi", "turquoise", "squash blossom", "concho"], "typical_low": 60, "typical_high": 1500, "demand": "high", "liquidity": "medium"},
    {"name": "Eisenberg / Eisenberg Ice", "entry_type": "maker_mark", "domain": "jewelry", "category": "costume",
     "characteristics": "High-quality rhinestone costume jewelry, marks 'Eisenberg Original' (1930s-40s), 'Eisenberg Ice' (1950s+).",
     "identifiers": ["eisenberg", "eisenberg ice", "eisenberg original"], "keywords": ["eisenberg"], "typical_low": 30, "typical_high": 400, "demand": "medium", "liquidity": "medium"},
    {"name": "Danecraft sterling", "entry_type": "maker_mark", "domain": "jewelry", "category": "American sterling",
     "characteristics": "Providence RI; 'Danecraft Sterling' marks; leaf/floral brooches.", "identifiers": ["danecraft"], "keywords": ["danecraft"],
     "typical_low": 20, "typical_high": 80, "demand": "low", "liquidity": "medium"},
    {"name": "Trifari / Alfred Philippe era", "entry_type": "maker_mark", "domain": "jewelry", "category": "costume",
     "characteristics": "Crown Trifari mark; 'Trifari Pat. Pend.' pieces designed by Alfred Philippe; jelly bellies.",
     "identifiers": ["trifari", "crown trifari", "pat pend"], "keywords": ["trifari", "jelly belly"], "typical_low": 25, "typical_high": 500, "demand": "medium", "liquidity": "high"},
    {"name": "Miriam Haskell", "entry_type": "maker_mark", "domain": "jewelry", "category": "costume",
     "characteristics": "Hand-wired baroque pearls and beads on filigree backs; horseshoe/oval marks.", "identifiers": ["miriam haskell", "haskell"],
     "keywords": ["haskell"], "typical_low": 60, "typical_high": 800, "demand": "high", "liquidity": "medium"},
    {"name": "Gold-filled vs solid gold marks", "entry_type": "characteristic", "domain": "jewelry", "category": "precious metals",
     "characteristics": "'1/20 12K GF', 'GF', 'RGP', 'HGE' = plated/filled; '10K/14K/18K' or '585/750' = karat marks (verify by test).",
     "identifiers": ["14k", "18k", "10k", "585", "750", "gf", "hge", "rgp"], "keywords": ["gold", "14k", "18k", "10k", "585", "750", "gold filled"],
     "typical_low": None, "typical_high": None, "demand": "high", "liquidity": "high"},
]
