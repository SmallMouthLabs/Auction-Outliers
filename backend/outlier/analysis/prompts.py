"""Prompts for the vision stages. Kept stable (prefix-cacheable); listing data goes in the user turn."""
from __future__ import annotations

from typing import Any

JEWELRY_SAFEGUARD = (
    "CRITICAL JEWELRY SAFEGUARD: never conclude that an item is solid gold, sterling silver, or an authentic "
    "designer piece solely because it looks like one. A visible hallmark ('925', '14K', a maker's mark) is "
    "evidence, not verification; record it verbatim as an observation and keep the material a hypothesis with "
    "a confidence and the verification a buyer would need (acid/XRF test, loupe, weighing). Do not compute "
    "melt value. For lots, identify individually interesting pieces separately."
)

CLOTHING_GUIDANCE = (
    "For garments: transcribe every label verbatim (brand, union labels, RN/WPL numbers, care tags, 'Made in'); "
    "note tag style and construction clues that date the piece (single-stitch hems, chain-stitched hems, selvedge, "
    "Talon/Scovill/Gripper zippers, union labels, bar tacks, felled seams), fabric (mohair, cashmere, wool, "
    "cotton, nylon), prints/graphics, model names or lot numbers, and condition issues. Distinguish archival "
    "designer pieces from later reissues. Note when a label is missing but construction suggests quality."
)

TRIAGE_SYSTEM = (
    "You are a sourcing analyst for a vintage clothing and jewelry reseller. You examine auction photographs "
    "INDEPENDENTLY of the seller's title and look for evidence that the seller has under-described or "
    "misidentified the item. Report only what is visible; separate observations from hypotheses. Be concise. "
    "Output must follow the provided JSON schema exactly. "
    + CLOTHING_GUIDANCE + " " + JEWELRY_SAFEGUARD
)

DEEP_SYSTEM = (
    "You are a senior authentication and valuation specialist for vintage/designer clothing and jewelry. "
    "You receive auction photographs and the seller's text. Your job: identify what the item actually is, "
    "find characteristics that indicate overlooked resale value, and flag discrepancies between the seller's "
    "description and the visual evidence. Separate observed facts, candidate identifications (each with evidence, "
    "counter-evidence and an uncalibrated confidence), and alternative explanations. State what information is "
    "missing for valuation, and propose concrete sold-listing search queries. Never invent labels, marks or "
    "provenance you cannot see. If a detail is too small to read, use the zoom_image tool when available. "
    + CLOTHING_GUIDANCE + " " + JEWELRY_SAFEGUARD
)


def listing_block(listing: dict[str, Any]) -> str:
    lines = [
        f"Seller title: {listing.get('title','')}",
        f"Seller category: {listing.get('category') or 'n/a'}",
        f"Seller description: {(listing.get('description') or 'n/a')[:3000]}",
        f"Condition notes: {listing.get('condition_text') or 'n/a'}",
        f"Measurements: {listing.get('measurements') or 'n/a'}",
        f"Current bid: {listing.get('current_bid')} | bids: {listing.get('num_bids')}",
    ]
    return "\n".join(lines)


def triage_prompt(listing: dict[str, Any], domain_hint: str) -> str:
    return (
        "Examine the photographs first, then read the seller text.\n\n"
        f"Domain hint from prefilter: {domain_hint}\n\n{listing_block(listing)}\n\n"
        "Produce the triage JSON. Set escalate=true when there is a plausible chance of a desirable maker, "
        "designer, era, material or construction that the seller did not name, or when an identification "
        "requires reading small details. Set interest_score accordingly (0-100)."
    )


def deep_prompt(listing: dict[str, Any], domain: str, triage: dict[str, Any] | None, references: list[dict[str, Any]]) -> str:
    ref_txt = ""
    if references:
        ref_txt = "\n\nReference database candidates (from keyword/identifier matches; verify visually, do not assume):\n" + "\n".join(
            f"- {r['name']} ({r.get('entry_type')}, {r.get('domain')}): {r.get('characteristics') or ''} "
            f"identifiers={r.get('identifiers') or []} typical=${r.get('typical_low')}-{r.get('typical_high')}"
            for r in references[:8]
        )
    tri = ""
    if triage:
        tri = f"\n\nLow-cost triage notes (verify, do not trust blindly): {triage.get('item_summary','')}; " \
              f"visible text: {[t.get('text') for t in triage.get('visible_text', [])]}; " \
              f"mismatch: {triage.get('seller_vs_visual_mismatch')}"
    return (
        f"Domain: {domain}. Fill the `{domain}` details object and leave the other one null.\n\n"
        f"{listing_block(listing)}{tri}{ref_txt}\n\n"
        "Zoom into labels, hallmarks, maker's marks, stitching and hardware when they are not legible. Then produce "
        "the full structured JSON. Include seller-vs-visual discrepancies with their direction and strength, "
        "demand/liquidity indicators (unknown if unsure), risk flags, missing information, and 2-5 research queries "
        "targeting SOLD listings."
    )
