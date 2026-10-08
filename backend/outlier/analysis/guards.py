"""Deterministic post-validation of model output (the jewelry / designer safeguard, enforced in code).

The prompts ask the model not to 'confirm' precious metals or designer authenticity from appearance; this module
makes sure it cannot, whatever the model returns:
- precious-metal / designer candidates marked 'confirmed' are demoted to 'inferred';
- material hypotheses for precious metals are capped at 0.7 confidence unless a physical test is cited;
- a melt-value note containing a dollar figure is replaced and flagged;
- overall confidence is capped when every candidate relies on unverified marks.
"""
from __future__ import annotations

import re
from typing import Any

PRECIOUS = re.compile(r"\b(gold|14k|18k|10k|22k|24k|585|750|sterling|silver|925|platinum|plat|pt950|palladium)\b", re.I)
DESIGNER_WORDS = re.compile(r"\b(tiffany|cartier|van cleef|bulgari|bvlgari|chanel|hermes|herm[eè]s|gucci|rolex|david yurman|georg jensen|"
                            r"spratling|lalaounis|buccellati|dior|louis vuitton|prada|balenciaga|margiela|comme des gar[cç]ons|yohji|"
                            r"issey miyake|vivienne westwood|raf simons|helmut lang|number \(n\)ine|undercover)\b", re.I)
TESTED = re.compile(r"\b(acid[- ]test|xrf|assay|tested|magnet[- ]test(ed)?|weighed and tested|specific gravity)\b", re.I)
MONEY = re.compile(r"\$\s?\d|\d+\s?(usd|dollars)", re.I)
MELT_NOTE = "Not computed: metal content and weight are unverified."
MAX_MATERIAL_CONF = 0.7


def apply_guards(out: dict[str, Any]) -> dict[str, Any]:
    """Mutates and returns the DeepResult dict; appends to out['guard_notes'] whenever something was changed."""
    notes: list[str] = []
    flags: list[str] = list(out.get("risk_flags") or [])

    def _flag(f: str) -> None:
        if f not in flags:
            flags.append(f)

    for c in out.get("candidates") or []:
        label = f"{c.get('label','')} {c.get('brand_or_maker') or ''}"
        if c.get("status") == "confirmed" and (PRECIOUS.search(label) or DESIGNER_WORDS.search(label)):
            c["status"] = "inferred"
            notes.append(f"Candidate '{c.get('label')}' demoted from 'confirmed' to 'inferred': appearance and marks are evidence, not verification.")
            _flag("authenticity / material not physically verified")
        if c.get("confidence", 0) > 0.95:
            c["confidence"] = 0.95

    j = out.get("jewelry")
    if isinstance(j, dict):
        for m in j.get("materials") or []:
            mat = str(m.get("material") or "")
            basis = " ".join(str(b) for b in (m.get("basis") or [])) + " " + str(m.get("verification_needed") or "")
            if PRECIOUS.search(mat) and float(m.get("confidence") or 0) > MAX_MATERIAL_CONF and not TESTED.search(basis):
                m["confidence"] = MAX_MATERIAL_CONF
                if not m.get("verification_needed"):
                    m["verification_needed"] = "acid/XRF test and weighing before relying on metal content"
                notes.append(f"Material '{mat}' confidence capped at {MAX_MATERIAL_CONF}: no physical test cited.")
                _flag("precious metal unverified")
        note = str(j.get("melt_value_note") or "")
        if MONEY.search(note) or re.search(r"\bmelt\b.*\d", note, re.I) and MONEY.search(note):
            j["melt_value_note"] = MELT_NOTE
            notes.append("Melt value removed: it must not be computed from unverified material/weight.")
            _flag("melt value claim removed (unverified)")
        if float(j.get("maker_confidence") or 0) > 0.9 and not any(
            TESTED.search(" ".join(str(x) for x in (j.get("design_characteristics") or []) + [t.get("text", "") for t in (j.get("makers_marks") or [])]))
            for _ in [0]
        ):
            j["maker_confidence"] = 0.9

    cl = out.get("clothing")
    if isinstance(cl, dict):
        brand = str(cl.get("brand_or_manufacturer") or "")
        if DESIGNER_WORDS.search(brand) and float(cl.get("brand_confidence") or 0) > 0.9:
            cl["brand_confidence"] = 0.9
            notes.append(f"Brand confidence for '{brand}' capped at 0.9: designer authenticity needs in-hand inspection.")
            _flag("designer authenticity not verified")

    if out.get("overall_confidence", 0) > 0.95:
        out["overall_confidence"] = 0.95
    if notes:
        out["guard_notes"] = (out.get("guard_notes") or []) + notes
    out["risk_flags"] = flags
    return out
