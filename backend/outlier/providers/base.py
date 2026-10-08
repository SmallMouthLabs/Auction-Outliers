"""Provider-agnostic vision/LLM adapter interface."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    """Raised for provider failures; message is safe to show to the user (no secrets)."""


class ProviderNotConfigured(ProviderError):
    pass


class BudgetExceeded(ProviderError):
    pass


@dataclass
class ImageInput:
    data: bytes
    media_type: str  # image/jpeg | image/png | image/webp
    label: str = ""  # e.g. "image 0"
    index: int = 0


@dataclass
class ProviderResult:
    parsed: Any  # instance of the requested schema (or None on failure)
    raw_text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    est_cost_usd: float = 0.0
    duration_ms: int = 0
    zoom_calls: list[dict[str, Any]] = field(default_factory=list)
    is_demo: bool = False
    stop_reason: str | None = None


# Zoom tool: given a crop request dict, returns an ImageInput of the crop (or raises ValueError).
ZoomFn = Callable[[dict[str, Any]], ImageInput]


class VisionProvider:
    name: str = "base"
    model: str = ""
    supports_tools: bool = False
    is_demo: bool = False

    def analyze(
        self,
        *,
        images: list[ImageInput],
        system: str,
        prompt: str,
        schema: type[T],
        zoom: ZoomFn | None = None,
        max_zoom_calls: int = 0,
        stage: str = "triage",
    ) -> ProviderResult:
        raise NotImplementedError
