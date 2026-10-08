"""Import comparable sales from CSV/JSON rows."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .common import clean_text, parse_datetime, parse_price


class CompIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    marketplace: str = "ebay"
    url: str | None = None
    sold_date: Any = None
    price: float | None = Field(default=None, ge=0)
    shipping_included: bool | None = None
    shipping_amount: float | None = Field(default=None, ge=0)
    is_sold: bool = True
    accepted_offer: bool = False
    comp_type: str = "same_maker"
    similarity: float = Field(default=0.6, ge=0, le=1)
    evidence_quality: str = "medium"
    condition: str | None = None
    differences: str | None = None
    source: str = "manual"

    @field_validator("comp_type")
    @classmethod
    def _ct(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("exact", "same_maker", "category", "active", "unsupported"):
            raise ValueError("comp_type must be exact|same_maker|category|active|unsupported")
        return v

    @field_validator("evidence_quality")
    @classmethod
    def _eq(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("high", "medium", "low"):
            raise ValueError("evidence_quality must be high|medium|low")
        return v

    @field_validator("sold_date", mode="before")
    @classmethod
    def _sd(cls, v):
        return parse_datetime(v) if v not in (None, "") else None

    @field_validator("url")
    @classmethod
    def _url(cls, v):
        v = clean_text(v)
        return v if (v and v.startswith("http")) else None


def _truthy(v: Any) -> bool | None:
    if v is None or v == "":
        return None
    return str(v).strip().lower() in ("1", "true", "yes", "y", "sold", "included")


def rows_to_comps(rows: list[dict[str, Any]], source: str) -> tuple[list[CompIn], list[str]]:
    out, errors = [], []
    for i, r in enumerate(rows, start=1):
        try:
            low = {k.strip().lower(): v for k, v in r.items()}
            is_sold = _truthy(low.get("is_sold", low.get("sold")))
            comp_type = (low.get("comp_type") or low.get("type") or "same_maker")
            if is_sold is False:
                comp_type = "active"
            out.append(CompIn(
                title=low.get("title") or "", marketplace=low.get("marketplace") or low.get("source_marketplace") or "ebay",
                url=low.get("url") or low.get("link"), sold_date=low.get("sold_date") or low.get("date"),
                price=parse_price(low.get("price") or low.get("sold_price")), shipping_included=_truthy(low.get("shipping_included")),
                shipping_amount=parse_price(low.get("shipping_amount") or low.get("shipping")), is_sold=is_sold if is_sold is not None else True,
                accepted_offer=bool(_truthy(low.get("accepted_offer")) or False), comp_type=comp_type,
                similarity=float(low.get("similarity") or 0.6), evidence_quality=low.get("evidence_quality") or "medium",
                condition=low.get("condition"), differences=low.get("differences") or low.get("notes"), source=source,
            ))
        except Exception as e:  # noqa: BLE001
            errors.append(f"row {i}: {e}")
    return out, errors


def parse_comps_csv(text: str) -> tuple[list[CompIn], list[str]]:
    return rows_to_comps(list(csv.DictReader(io.StringIO(text))), "csv")


def parse_comps_json(text: str) -> tuple[list[CompIn], list[str]]:
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("comps") or data.get("comparables") or [data]
    return rows_to_comps(data, "json")
