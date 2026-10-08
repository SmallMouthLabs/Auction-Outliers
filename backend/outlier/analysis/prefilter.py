"""STAGE 1 - deterministic prefiltering. No model calls.

Produces: domain guess, pass/skip decision with reasons, keyword hits, and a prefilter priority 0-100.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

CLOTHING_TERMS = [
    "jacket", "coat", "sweater", "cardigan", "shirt", "blouse", "dress", "skirt", "pants", "jeans", "denim",
    "trousers", "vest", "blazer", "suit", "overalls", "coveralls", "chore", "workwear", "knit", "wool", "mohair",
    "cashmere", "leather", "parka", "anorak", "hoodie", "sweatshirt", "t-shirt", "tee", "tshirt", "flannel",
    "pullover", "jumper", "gown", "kimono", "poncho", "cape", "shawl", "scarf", "hat", "cap", "boots", "shoes",
    "sneakers", "loafers", "size", "mens", "men's", "womens", "women's", "unisex", "vintage clothing", "apparel",
]
JEWELRY_TERMS = [
    "jewelry", "jewellery", "necklace", "bracelet", "ring", "earrings", "earring", "brooch", "pin", "pendant",
    "cuff", "bangle", "choker", "locket", "cameo", "charm", "sterling", "silver", "gold", "14k", "18k", "10k",
    "925", "turquoise", "navajo", "taxco", "gemstone", "rhinestone", "costume jewelry", "chain", "watch",
    "cufflinks", "tie clip", "signed", "hallmark",
]
_WORD = re.compile(r"[a-z0-9']+")


@dataclass
class PrefilterResult:
    domain: str  # clothing|jewelry|other|unknown
    passed: bool
    reasons: list[str] = field(default_factory=list)
    boost_hits: list[str] = field(default_factory=list)
    exclude_hits: list[str] = field(default_factory=list)
    priority: int = 0  # 0-100
    label: str = "deterministic prefilter (no model call)"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _score_terms(text: str, terms: list[str]) -> int:
    return sum(1 for t in terms if t in text)


def guess_domain(title: str, description: str | None, category: str | None) -> str:
    text = " ".join(x for x in (title, description or "", category or "") if x).lower()
    cat = (category or "").lower()
    if any(k in cat for k in ("jewelry", "jewellery", "watches")):
        return "jewelry"
    if any(k in cat for k in ("clothing", "apparel", "shoes", "fashion", "accessories")):
        return "clothing"
    c = _score_terms(text, CLOTHING_TERMS)
    j = _score_terms(text, JEWELRY_TERMS)
    if c == 0 and j == 0:
        return "unknown"
    if j > c:
        return "jewelry"
    if c > j:
        return "clothing"
    return "unknown"


def run_prefilter(
    *, title: str, description: str | None, category: str | None, current_bid: float | None,
    image_count: int, cfg: dict[str, Any], existing_domain: str | None = None,
) -> PrefilterResult:
    text = " ".join(x for x in (title, description or "", category or "") if x).lower()
    domain = existing_domain if existing_domain in ("clothing", "jewelry") else guess_domain(title, description, category)
    reasons: list[str] = []
    passed = True

    exclude_hits = [k for k in cfg.get("exclude_keywords", []) if k.lower() in text]
    boost_hits = [k for k in cfg.get("boost_keywords", []) if re.search(rf"\b{re.escape(k.lower())}\b", text)]

    if domain == "other":
        passed = False
        reasons.append("Out of scope category (not clothing or jewelry).")
    if domain == "unknown":
        reasons.append("Domain could not be determined from text; triage will classify from images.")
    if exclude_hits:
        passed = False
        reasons.append("Exclusion keyword(s): " + ", ".join(exclude_hits))
    if image_count == 0:
        passed = False
        reasons.append("No photographs available; visual analysis is impossible.")
    lo = cfg.get("min_current_bid", 0.0) or 0.0
    hi = cfg.get("max_current_bid")
    if current_bid is not None:
        if current_bid < lo:
            passed = False
            reasons.append(f"Current bid ${current_bid:.2f} below minimum ${lo:.2f}.")
        if hi is not None and current_bid > hi:
            passed = False
            reasons.append(f"Current bid ${current_bid:.2f} above maximum ${hi:.2f}.")

    priority = 30 + min(len(boost_hits), 5) * 12
    if domain in ("clothing", "jewelry"):
        priority += 5
    # vague titles are interesting: fewer specific words => more room for misidentification
    words = _WORD.findall(title.lower())
    if len(words) <= 4:
        priority += 8
        reasons.append("Short/vague title: higher chance of seller under-description.")
    priority = max(0, min(100, priority))
    if passed and not reasons:
        reasons.append("Passed deterministic prefilter.")
    return PrefilterResult(domain=domain, passed=passed, reasons=reasons, boost_hits=boost_hits,
                           exclude_hits=exclude_hits, priority=priority)
