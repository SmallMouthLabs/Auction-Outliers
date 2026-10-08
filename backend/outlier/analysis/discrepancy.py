"""Identification discrepancy detection.

Combines (a) the model's own discrepancy findings with (b) deterministic checks between the seller's text and
the structured visual findings (labels transcribed vs. brand named; hallmark seen vs. 'silver tone'; etc.).
Outputs an uncertainty-aware 'possible misidentification' signal in [0,1] with the supporting evidence.
"""
from __future__ import annotations

import re
from typing import Any

GENERIC_MATERIAL_TERMS = ["silver tone", "silvertone", "gold tone", "goldtone", "costume", "fashion jewelry", "plated"]
PRECIOUS_MARKS = [r"\b925\b", r"\bsterling\b", r"\bster\b", r"\b(10|14|18|22|24)\s?k\b", r"\b(585|750|916|999)\b", r"\bplat\b", r"\bpt950\b"]
STRENGTH = {"weak": 0.25, "moderate": 0.5, "strong": 0.85}


def _norm(s: str | None) -> str:
    return (s or "").lower()


def detect(seller_title: str, seller_description: str | None, deep: dict[str, Any], domain: str) -> dict[str, Any]:
    seller_text = _norm(seller_title) + " " + _norm(seller_description)
    findings: list[dict[str, Any]] = []

    # (a) model-reported discrepancies
    for d in deep.get("discrepancies", []) or []:
        if d.get("direction") == "seller_undervalues":
            findings.append({
                "source": "model", "seller_claim": d.get("seller_claim"), "visual_evidence": d.get("visual_evidence"),
                "strength": d.get("strength", "moderate"), "image_index": d.get("image_index"),
            })

    # (b) deterministic: transcribed labels/marks the seller never mentions
    texts: list[dict[str, Any]] = []
    if domain == "clothing" and deep.get("clothing"):
        texts = deep["clothing"].get("label_texts", []) or []
        brand = deep["clothing"].get("brand_or_manufacturer")
        bconf = deep["clothing"].get("brand_confidence") or 0
        if brand and bconf >= 0.5 and _norm(brand).split()[0] not in seller_text:
            findings.append({
                "source": "rule", "seller_claim": "Brand/manufacturer not named by seller",
                "visual_evidence": f"Label/construction suggests '{brand}' (model confidence {bconf:.2f})",
                "strength": "strong" if bconf >= 0.75 else "moderate", "image_index": None,
            })
    if domain == "jewelry" and deep.get("jewelry"):
        j = deep["jewelry"]
        texts = (j.get("makers_marks", []) or []) + (j.get("hallmarks_and_inscriptions", []) or [])
        generic = [g for g in GENERIC_MATERIAL_TERMS if g in seller_text]
        marks = " ".join(_norm(t.get("text")) for t in texts)
        precious_hit = [p for p in PRECIOUS_MARKS if re.search(p, marks)]
        if generic and precious_hit:
            findings.append({
                "source": "rule", "seller_claim": f"Seller describes as '{generic[0]}'",
                "visual_evidence": f"Apparent precious-metal mark transcribed: '{marks.strip()[:80]}' (unverified)",
                "strength": "strong", "image_index": next((t.get("image_index") for t in texts if t.get("image_index") is not None), None),
            })
        maker = j.get("potential_maker")
        mconf = j.get("maker_confidence") or 0
        if maker and mconf >= 0.5 and _norm(maker).split()[0] not in seller_text:
            findings.append({
                "source": "rule", "seller_claim": "Maker not named by seller",
                "visual_evidence": f"Marks/design suggest '{maker}' (model confidence {mconf:.2f})",
                "strength": "strong" if mconf >= 0.75 else "moderate", "image_index": None,
            })
    for t in texts:
        txt = _norm(t.get("text"))
        if len(txt) >= 3 and t.get("legibility", "clear") != "poor" and txt not in seller_text:
            key = txt.split()[0] if txt.split() else txt
            if key and key not in seller_text and not any(key in _norm(f.get("visual_evidence")) for f in findings):
                findings.append({
                    "source": "rule", "seller_claim": "Label/mark text absent from seller description",
                    "visual_evidence": f"Transcribed: '{t.get('text')}' ({t.get('label_type') or 'label'})",
                    "strength": "weak" if t.get("legibility") == "partial" else "moderate", "image_index": t.get("image_index"),
                })

    # aggregate -> signal in [0,1], saturating; uncertainty-aware (discounted by overall confidence)
    raw = 1.0
    for f in findings:
        raw *= 1.0 - STRENGTH.get(f.get("strength", "moderate"), 0.5) * 0.8
    signal = 1.0 - raw
    conf = float(deep.get("overall_confidence") or 0.5)
    signal_adj = round(signal * (0.5 + 0.5 * conf), 3)
    return {
        "signal": signal_adj,
        "raw_signal": round(signal, 3),
        "findings": findings,
        "note": "Discrepancies raise research priority; they do not establish value.",
    }
