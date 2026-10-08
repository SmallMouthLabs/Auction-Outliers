"""Cost estimation helpers. Prices are editable in Settings (model_pricing_usd_per_1m)."""
from __future__ import annotations

from ..settings_store import DEFAULT_SETTINGS

_FALLBACK = DEFAULT_SETTINGS["model_pricing_usd_per_1m"]


def estimate_cost(model: str, tokens_in: int, tokens_out: int, pricing: dict | None = None) -> float:
    table = pricing or _FALLBACK
    rate = table.get(model)
    if rate is None:
        # try prefix match (e.g. dated model ids)
        for k, v in table.items():
            if model.startswith(k):
                rate = v
                break
    if rate is None:
        return 0.0
    return round(tokens_in / 1e6 * rate[0] + tokens_out / 1e6 * rate[1], 6)


def estimate_image_tokens(width: int, height: int, provider: str) -> int:
    if provider == "anthropic":
        return int(width * height / 750)
    if provider == "gemini":
        # 258 tokens for images <= 384px on both sides; otherwise tiled in 768px crops of 258 tokens each
        if width <= 384 and height <= 384:
            return 258
        tiles = max(1, -(-width // 768)) * max(1, -(-height // 768))
        return 258 * tiles
    return int(width * height / 750)
