"""Durable, resumable job queue backed by the `jobs` table with an in-process worker thread.

Suitable for a single-user local app: survives restarts (pending/running jobs are resumed), retries with
backoff, and one failing job never stops the batch.
"""
from __future__ import annotations

import logging
import threading
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..db import session_scope
from ..models import Job

log = logging.getLogger(__name__)
Handler = Callable[[Session, Job], dict[str, Any]]
_HANDLERS: dict[str, Handler] = {}


def handler(job_type: str):
    def deco(fn: Handler) -> Handler:
        _HANDLERS[job_type] = fn
        return fn
    return deco


def enqueue(db: Session, job_type: str, *, listing_id: int | None = None, payload: dict | None = None,
            max_attempts: int = 3, dedupe: bool = True) -> Job:
    if dedupe:
        existing = (db.query(Job).filter(Job.job_type == job_type, Job.listing_id == listing_id,
                                         Job.status.in_(["pending", "running"]), Job.payload == (payload or {})).first())
        if existing:
            return existing
    job = Job(job_type=job_type, listing_id=listing_id, payload=payload or {}, max_attempts=max_attempts)
    db.add(job)
    db.flush()
    return job


def _claim(db: Session) -> Job | None:
    now = datetime.now(UTC)
    job = (db.query(Job).filter(Job.status == "pending")
           .filter((Job.run_after == None) | (Job.run_after <= now))
           .order_by(Job.id).first())
    if job is None:
        return None
    job.status = "running"
    job.started_at = now
    job.attempts += 1
    db.flush()
    return job


def run_one(db: Session, job: Job) -> None:
    fn = _HANDLERS.get(job.job_type)
    if fn is None:
        job.status = "failed"
        job.error = f"no handler for {job.job_type}"
        job.finished_at = datetime.now(UTC)
        return
    try:
        result = fn(db, job)
        job.result = result or {}
        job.status = "succeeded"
        job.error = None
    except Exception as e:  # noqa: BLE001
        db.rollback()
        job = db.get(Job, job.id)
        log.warning("job %s (%s) failed: %s", job.id, job.job_type, e)
        job.error = f"{type(e).__name__}: {e}"[:2000]
        job.result = {"traceback": traceback.format_exc()[-2000:]}
        if job.attempts < job.max_attempts and not _non_retryable(e):
            job.status = "pending"
            job.run_after = datetime.now(UTC) + timedelta(seconds=15 * (2 ** (job.attempts - 1)))
        else:
            job.status = "failed"
    job.finished_at = datetime.now(UTC)


def _non_retryable(e: Exception) -> bool:
    from ..providers.base import BudgetExceeded, ProviderNotConfigured

    return isinstance(e, (ProviderNotConfigured, BudgetExceeded, ValueError))


def recover_stale(db: Session, max_age_minutes: int = 30) -> int:
    cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
    n = 0
    for job in db.query(Job).filter(Job.status == "running").all():
        started = job.started_at.replace(tzinfo=UTC) if job.started_at and job.started_at.tzinfo is None else job.started_at
        if started is None or started < cutoff:
            job.status = "pending" if job.attempts < job.max_attempts else "failed"
            if job.status == "failed":
                job.error = (job.error or "") + " [stale: worker restarted]"
            n += 1
    return n


def process_pending(limit: int = 50) -> int:
    """Process up to `limit` pending jobs synchronously (used by tests and the worker loop)."""
    done = 0
    for _ in range(limit):
        with session_scope() as db:
            job = _claim(db)
            if job is None:
                break
            run_one(db, job)
            done += 1
    return done


class Worker:
    """Polls the job table and also enqueues periodic housekeeping jobs (reminders, optional e-mail polling)."""

    def __init__(self, poll_seconds: float = 2.0):
        self.poll = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_periodic: dict[str, float] = {}

    def _periodic(self) -> None:
        from ..config import get_secrets, get_settings

        now = time.time()
        s = get_settings()
        schedule = {"watchlist_reminders": 300.0}
        if s.imap_host and s.imap_user and get_secrets().imap_password:
            schedule["poll_email"] = 900.0
        for job_type, every in schedule.items():
            if now - self._last_periodic.get(job_type, 0.0) >= every:
                self._last_periodic[job_type] = now
                with session_scope() as db:
                    enqueue(db, job_type, max_attempts=1)

    def start(self) -> None:
        with session_scope() as db:
            recover_stale(db, max_age_minutes=0)
        self._thread = threading.Thread(target=self._loop, name="outlier-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._periodic()
                n = process_pending(limit=5)
            except Exception:
                log.exception("worker loop error")
                n = 0
            if n == 0:
                self._stop.wait(self.poll)
