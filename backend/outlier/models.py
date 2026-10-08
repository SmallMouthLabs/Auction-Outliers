"""SQLAlchemy ORM models.

Design notes
- Every row that originates from demo fixtures carries is_demo=True so the UI can label it.
- Listing holds the *current verified* state; ListingSnapshot keeps historical observations.
- Secrets are never stored here.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("source", "source_item_id", name="uq_listing_source_item"),
        Index("ix_listing_fingerprint", "fingerprint"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), default="manual")  # manual|csv|email|page_html|webhook|sgw_unofficial|demo
    source_item_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seller: Mapped[str | None] = mapped_column(String(200), nullable=True)
    domain: Mapped[str] = mapped_column(String(20), default="unknown")  # clothing|jewelry|other|unknown

    current_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    num_bids: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buy_now_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipping_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    handling_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    other_costs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # {"name": amount}
    measurements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    condition_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|ended|unknown

    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # per-listing finance overrides
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    images: Mapped[list[ListingImage]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="ListingImage.position"
    )
    snapshots: Mapped[list[ListingSnapshot]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="ListingSnapshot.captured_at"
    )
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    identifications: Mapped[list[Identification]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="Identification.created_at"
    )
    comparables: Mapped[list[Comparable]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    valuations: Mapped[list[Valuation]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="Valuation.created_at"
    )
    opportunity: Mapped[Opportunity | None] = relationship(
        back_populates="listing", cascade="all, delete-orphan", uselist=False
    )
    watchlist: Mapped[WatchlistItem | None] = relationship(
        back_populates="listing", cascade="all, delete-orphan", uselist=False
    )
    feedback: Mapped[list[Feedback]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    notes: Mapped[list[ResearchNote]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    outcome: Mapped[Outcome | None] = relationship(back_populates="listing", cascade="all, delete-orphan", uselist=False)


class ListingSnapshot(Base):
    """Historical observation of mutable auction fields."""

    __tablename__ = "listing_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    current_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    num_bids: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipping_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    listing: Mapped[Listing] = relationship(back_populates="snapshots")


class ListingImage(Base):
    __tablename__ = "listing_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    remote_url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(600), nullable=True)  # relative to data_dir
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetch_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="images")


class AnalysisRun(Base):
    """One model invocation (or deterministic stage) for a listing."""

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(20))  # prefilter|triage|deep|discrepancy|reference
    provider: Mapped[str] = mapped_column(String(40))  # rules|anthropic|gemini|demo
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="succeeded")  # succeeded|failed|skipped|cached
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="analysis_runs")


class Identification(Base):
    """Current best structured identification. New rows are appended on re-analysis or user correction."""

    __tablename__ = "identifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(20), default="ai")  # ai|user|demo
    run_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True)
    domain: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(String(500))  # e.g. "1970s Pendleton wool shirt jacket"
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # model-reported, uncalibrated
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # full structured schema output
    discrepancy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    warrants_research: Mapped[bool] = mapped_column(Boolean, default=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="identifications")


class Comparable(Base):
    __tablename__ = "comparables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=True)
    reference_id: Mapped[int | None] = mapped_column(ForeignKey("reference_entries.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    marketplace: Mapped[str] = mapped_column(String(60), default="ebay")
    url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    sold_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)  # actual transaction price if is_sold
    shipping_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    shipping_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=True)  # False => active asking price
    accepted_offer: Mapped[bool] = mapped_column(Boolean, default=False)
    comp_type: Mapped[str] = mapped_column(String(20), default="category")  # exact|same_maker|category|active|unsupported
    similarity: Mapped[float] = mapped_column(Float, default=0.5)  # 0..1
    evidence_quality: Mapped[str] = mapped_column(String(10), default="medium")  # high|medium|low
    condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    differences: Mapped[str | None] = mapped_column(Text, nullable=True)  # size/material/etc differences
    source: Mapped[str] = mapped_column(String(40), default="manual")  # manual|csv|provider:<name>|demo
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing | None] = relationship(back_populates="comparables")


class Valuation(Base):
    __tablename__ = "valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(40))  # sold_comps|user_override|unsupported
    conservative: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected: Mapped[float | None] = mapped_column(Float, nullable=True)
    optimistic: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_speculative: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_quality: Mapped[str] = mapped_column(String(10), default="none")  # high|medium|low|none
    n_sold_comps: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="valuations")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), unique=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    tier: Mapped[str] = mapped_column(String(30), default="LOW_VALUE")
    components: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    finance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # cached expected-scenario finance
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="opportunity")


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="watching")  # watching|bidding|won|lost|passed|archived
    user_max_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    remind_minutes_before_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="watchlist")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="feedback")


class ResearchNote(Base):
    __tablename__ = "research_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)  # marked for investigation
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="notes")


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), unique=True)
    purchased: Mapped[bool] = mapped_column(Boolean, default=False)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    acquisition_expenses: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold: Mapped[bool] = mapped_column(Boolean, default=False)
    resale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    selling_fees: Mapped[float | None] = mapped_column(Float, nullable=True)
    resale_platform: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    days_to_sale: Mapped[int | None] = mapped_column(Integer, nullable=True)
    realized_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    listing: Mapped[Listing] = relationship(back_populates="outcome")


class ReferenceEntry(Base):
    """Reference database of designers/brands/products/characteristics with resale evidence."""

    __tablename__ = "reference_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    entry_type: Mapped[str] = mapped_column(String(30), default="brand")  # brand|designer|product|characteristic|maker_mark
    domain: Mapped[str] = mapped_column(String(20), default="clothing")
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    characteristics: Mapped[str | None] = mapped_column(Text, nullable=True)
    identifiers: Mapped[list[str]] = mapped_column(JSON, default=list)  # label text, hallmarks, model numbers
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)  # matching terms (lowercase)
    reference_image_urls: Mapped[list[str]] = mapped_column(JSON, default=list)  # only licensed/user-supplied
    price_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # [{price, date, url, note}]
    typical_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    typical_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    demand: Mapped[str] = mapped_column(String(10), default="medium")  # high|medium|low
    liquidity: Mapped[str] = mapped_column(String(10), default="medium")  # high|medium|low
    id_confidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="seed")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(40), index=True)
    listing_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|running|succeeded|failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(20), nullable=True)
    listing_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Setting(Base):
    """Non-secret user settings (fee configs, thresholds, ranking weights, model choices)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
