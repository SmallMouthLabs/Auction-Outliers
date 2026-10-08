"""DEMO provider: returns canned, clearly labeled fixture outputs. Never used for real listings
unless explicitly requested. Every result is marked is_demo=True and provider='demo'."""
from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from .base import ProviderError, ProviderResult, VisionProvider


class DemoProvider(VisionProvider):
    name = "demo"
    model = "demo-fixtures"
    is_demo = True

    def __init__(self, fixtures: dict[str, dict[str, Any]] | None = None):
        # fixtures: {"<fixture_key>:<stage>": {...schema dict...}}
        self._fixtures = fixtures or {}
        self.fixture_key: str | None = None

    def analyze(self, *, images, system, prompt, schema: type[BaseModel], zoom=None, max_zoom_calls=0, stage="triage") -> ProviderResult:
        t0 = time.time()
        key = f"{self.fixture_key}:{stage}"
        data = self._fixtures.get(key)
        if data is None:
            raise ProviderError(
                f"No demo fixture for '{key}'. Demo analysis only works for demo listings; configure a real provider for live items."
            )
        parsed = schema.model_validate(data)
        return ProviderResult(
            parsed=parsed, raw_text="[DEMO FIXTURE OUTPUT - not a real model response]", provider=self.name,
            model=self.model, tokens_in=0, tokens_out=0, est_cost_usd=0.0,
            duration_ms=int((time.time() - t0) * 1000), is_demo=True,
        )
