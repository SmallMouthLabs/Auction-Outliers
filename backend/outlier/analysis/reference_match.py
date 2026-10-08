"""STRATEGY B - reference-based discovery: match listing text + transcribed labels against the reference DB."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from ..models import ReferenceEntry


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9&']+", text.lower()))


def match_references(db: Session, *, domain: str | None, texts: list[str], limit: int = 8) -> list[dict[str, Any]]:
    corpus = " ".join(t for t in texts if t).lower()
    toks = _tokens(corpus)
    q = db.query(ReferenceEntry)
    if domain in ("clothing", "jewelry"):
        q = q.filter(ReferenceEntry.domain.in_([domain, "both"]))
    scored: list[tuple[float, ReferenceEntry, list[str]]] = []
    for ref in q.all():
        hits: list[str] = []
        score = 0.0
        name = ref.name.lower()
        if name and name in corpus:
            hits.append(f"name:{ref.name}")
            score += 3.0
        for ident in ref.identifiers or []:
            il = str(ident).lower()
            if il and il in corpus:
                hits.append(f"identifier:{ident}")
                score += 4.0
        for kw in ref.keywords or []:
            kl = str(kw).lower()
            if " " in kl:
                if kl in corpus:
                    hits.append(f"kw:{kw}")
                    score += 1.5
            elif kl in toks:
                hits.append(f"kw:{kw}")
                score += 1.0
        if score > 0:
            scored.append((score, ref, hits))
    scored.sort(key=lambda s: -s[0])
    out = []
    for score, ref, hits in scored[:limit]:
        out.append({
            "id": ref.id, "name": ref.name, "entry_type": ref.entry_type, "domain": ref.domain,
            "category": ref.category, "characteristics": ref.characteristics, "identifiers": ref.identifiers,
            "typical_low": ref.typical_low, "typical_high": ref.typical_high, "demand": ref.demand,
            "liquidity": ref.liquidity, "match_score": score, "hits": hits, "is_demo": ref.is_demo,
        })
    return out
