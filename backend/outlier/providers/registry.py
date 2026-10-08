"""Resolve which provider/model to use for each stage.

Resolution order for 'auto':
  triage: gemini (flash) if GEMINI_API_KEY, else anthropic (haiku) if ANTHROPIC_API_KEY
  deep:   anthropic (opus) if ANTHROPIC_API_KEY, else gemini (pro) if GEMINI_API_KEY
If nothing is configured, raise ProviderNotConfigured with setup instructions.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings, get_secrets, get_settings
from .base import ProviderNotConfigured, VisionProvider

DEFAULT_MODELS = {
    ("anthropic", "triage"): "claude-haiku-5-5",
    ("anthropic", "deep"): "claude-opus-5-5",
    ("gemini", "triage"): "gemini-2.5-flash",
    ("gemini", "deep"): "gemini-2.5-pro",
}

SETUP_HINT = (
    "No AI provider is configured. Set ANTHROPIC_API_KEY and/or GEMINI_API_KEY in .env (see .env.example), "
    "then restart the backend. Demo listings can still be analyzed with the demo provider."
)


@dataclass
class ProviderStatus:
    provider: str
    configured: bool
    triage_model: str
    deep_model: str
    note: str


def provider_status() -> list[ProviderStatus]:
    sec = get_secrets().configured()
    out = []
    for p in ("anthropic", "gemini"):
        out.append(ProviderStatus(
            provider=p, configured=sec[p],
            triage_model=DEFAULT_MODELS[(p, "triage")], deep_model=DEFAULT_MODELS[(p, "deep")],
            note="live" if sec[p] else f"set {'ANTHROPIC_API_KEY' if p == 'anthropic' else 'GEMINI_API_KEY'} to enable",
        ))
    out.append(ProviderStatus(provider="demo", configured=True, triage_model="demo-fixtures", deep_model="demo-fixtures",
                              note="canned fixture outputs for demo listings only"))
    return out


def resolve_provider_name(stage: str, requested: str | None, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    sec = get_secrets().configured()
    req = requested or (settings.triage_provider if stage == "triage" else settings.deep_provider)
    if req and req != "auto":
        return req
    order = ["gemini", "anthropic"] if stage == "triage" else ["anthropic", "gemini"]
    for p in order:
        if sec[p]:
            return p
    raise ProviderNotConfigured(SETUP_HINT)


def build_provider(stage: str, requested: str | None = None, model: str | None = None,
                   pricing: dict | None = None, demo_fixtures: dict | None = None) -> VisionProvider:
    settings = get_settings()
    secrets = get_secrets()
    name = resolve_provider_name(stage, requested, settings)
    if name == "demo":
        from .demo_provider import DemoProvider

        return DemoProvider(demo_fixtures)
    model = model or (settings.triage_model if stage == "triage" else settings.deep_model) or DEFAULT_MODELS[(name, stage)]
    if name == "anthropic":
        if not secrets.anthropic_api_key:
            raise ProviderNotConfigured("ANTHROPIC_API_KEY is not set. " + SETUP_HINT)
        from .anthropic_provider import AnthropicProvider

        effort = "medium" if stage == "triage" else "high"
        return AnthropicProvider(secrets.anthropic_api_key, model, pricing, effort=effort)
    if name == "gemini":
        if not secrets.gemini_api_key:
            raise ProviderNotConfigured("GEMINI_API_KEY is not set. " + SETUP_HINT)
        from .gemini_provider import GeminiProvider

        return GeminiProvider(secrets.gemini_api_key, model, pricing)
    raise ProviderNotConfigured(f"Unknown provider '{name}'. Use anthropic, gemini, demo or auto.")
