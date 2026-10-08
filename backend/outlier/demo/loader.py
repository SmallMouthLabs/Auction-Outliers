"""Load / run / remove DEMO MODE data."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..analysis.pipeline import analyze_listing
from ..models import Comparable, Listing, ReferenceEntry
from ..services.listings import ListingIn, store_image_bytes, upsert_listing
from ..services.opportunity import recompute_opportunity
from .fixtures import DEMO_LISTINGS, SEED_REFERENCES, _sold
from .images import synthetic_image


def seed_references(db: Session) -> int:
    n = 0
    for ref in SEED_REFERENCES:
        if db.query(ReferenceEntry).filter(ReferenceEntry.name == ref["name"]).first():
            continue
        db.add(ReferenceEntry(**ref, source="seed (approximate guidance; verify)", is_demo=False))
        n += 1
    db.flush()
    return n


def load_demo(db: Session) -> dict[str, Any]:
    created = []
    for spec in DEMO_LISTINGS:
        data = ListingIn(
            source="demo", source_item_id=f"demo-{spec['key']}", source_url=None, extraction_method="demo_fixture",
            title=spec["title"], description=spec["description"], category=spec["category"], seller=spec["seller"],
            domain=spec["domain"], current_bid=spec["current_bid"], num_bids=spec["num_bids"], ends_at=spec["ends_at"],
            shipping_cost=spec["shipping_cost"], handling_fee=spec["handling_fee"], measurements=spec.get("measurements", {}),
            condition_text=spec.get("condition_text"), raw={"demo_fixture_key": spec["key"]}, is_demo=True,
        )
        l, was_created, _ = upsert_listing(db, data, fetch_images=False)
        if spec.get("assumptions"):
            l.assumptions = spec["assumptions"]
        if was_created:
            for i, label in enumerate(spec["images"]):
                detail = label.split(":", 1)[1].strip() if ":" in label else None
                store_image_bytes(db, l, synthetic_image(spec["title"], spec["domain"], i, detail), position=i)
            for c in spec["comps"]:
                l.comparables.append(Comparable(
                    listing_id=l.id, title=c["title"], marketplace="ebay (synthetic)", url=c.get("url"),
                    sold_date=_sold(c["days"]) if c.get("is_sold", True) else None, price=c["price"],
                    shipping_included=False, is_sold=c.get("is_sold", True), comp_type=c["comp_type"],
                    similarity=c["similarity"], evidence_quality=c["evidence_quality"], condition=c.get("condition"),
                    source="demo", is_demo=True,
                ))
            db.flush()
        recompute_opportunity(db, l)
        created.append({"id": l.id, "key": spec["key"], "created": was_created})
    refs = seed_references(db)
    return {"listings": created, "references_seeded": refs}


def run_demo_workflow(db: Session) -> dict[str, Any]:
    """Load fixtures and run the (demo-provider) analysis on each demo listing."""
    loaded = load_demo(db)
    results = []
    for row in loaded["listings"]:
        l = db.get(Listing, row["id"])
        summary = analyze_listing(db, l, mode="auto", provider="demo", force=False)
        opp = recompute_opportunity(db, l)
        results.append({"id": l.id, "key": row["key"], "stages": summary["stages"], "score": opp.score, "tier": opp.tier})
    return {"loaded": loaded, "analysis": results, "note": "DEMO: fixtures + canned analysis outputs, not live data."}


def clear_demo(db: Session) -> int:
    rows = db.query(Listing).filter(Listing.is_demo == True).all()
    n = len(rows)
    for l in rows:
        db.delete(l)
    db.flush()
    return n
