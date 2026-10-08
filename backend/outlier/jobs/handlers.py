"""Job handlers."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..analysis.pipeline import analyze_listing
from ..config import get_secrets, get_settings
from ..models import Job, Listing, WatchlistItem
from ..services.listings import retry_image_fetches, upsert_listing
from ..services.opportunity import recompute_opportunity
from .queue import handler

log = logging.getLogger(__name__)


@handler("analyze_listing")
def _analyze(db: Session, job: Job) -> dict:
    l = db.get(Listing, job.listing_id)
    if l is None:
        raise ValueError(f"listing {job.listing_id} not found")
    p = job.payload or {}
    summary = analyze_listing(db, l, mode=p.get("mode", "auto"), provider=p.get("provider"), model=p.get("model"), force=bool(p.get("force")))
    recompute_opportunity(db, l)
    return summary


@handler("fetch_images")
def _fetch_images(db: Session, job: Job) -> dict:
    l = db.get(Listing, job.listing_id)
    if l is None:
        raise ValueError(f"listing {job.listing_id} not found")
    n = retry_image_fetches(db, l)
    return {"fetched": n}


@handler("recompute_opportunity")
def _recompute(db: Session, job: Job) -> dict:
    l = db.get(Listing, job.listing_id)
    if l is None:
        raise ValueError(f"listing {job.listing_id} not found")
    opp = recompute_opportunity(db, l)
    return {"score": opp.score, "tier": opp.tier}


@handler("poll_email")
def _poll_email(db: Session, job: Job) -> dict:
    from ..ingestion.email_import import poll_imap

    s = get_settings()
    sec = get_secrets()
    if not (s.imap_host and s.imap_user and sec.imap_password):
        raise ValueError("IMAP is not configured (OUTLIER_IMAP_HOST, OUTLIER_IMAP_USER, OUTLIER_IMAP_PASSWORD).")
    batches = poll_imap(s.imap_host, s.imap_port, s.imap_user, sec.imap_password, s.imap_folder, s.imap_subject_filter)
    created = updated = 0
    for _subject, listings in batches:
        for li in listings:
            l, was_created, changed = upsert_listing(db, li, fetch_images=True)
            created += int(was_created)
            updated += int(changed and not was_created)
            recompute_opportunity(db, l)
    return {"emails": len(batches), "created": created, "updated": updated}


@handler("refresh_listing_unofficial")
def _refresh_unofficial(db: Session, job: Job) -> dict:
    from ..ingestion.sgw_unofficial import get_item

    l = db.get(Listing, job.listing_id)
    if l is None or not l.source_item_id:
        raise ValueError("listing has no ShopGoodwill item id")
    li = get_item(int(l.source_item_id))
    l2, _, changed = upsert_listing(db, li, fetch_images=True)
    recompute_opportunity(db, l2)
    return {"changed": changed}


@handler("watchlist_reminders")
def _reminders(db: Session, job: Job) -> dict:
    now = datetime.now(UTC)
    fired = []
    for w in db.query(WatchlistItem).filter(WatchlistItem.archived == False, WatchlistItem.reminder_sent_at == None).all():
        l = w.listing
        if not l.ends_at or w.remind_minutes_before_end is None:
            continue
        ends = l.ends_at if l.ends_at.tzinfo else l.ends_at.replace(tzinfo=UTC)
        if (ends - now).total_seconds() <= w.remind_minutes_before_end * 60:
            w.reminder_sent_at = now
            fired.append({"listing_id": l.id, "title": l.title, "ends_at": ends.isoformat(), "user_max_bid": w.user_max_bid})
            log.info("REMINDER: '%s' ends at %s (your max bid: %s)", l.title, ends.isoformat(), w.user_max_bid)
    return {"fired": fired}
