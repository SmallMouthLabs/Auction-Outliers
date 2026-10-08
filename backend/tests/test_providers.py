"""Provider adapters tested with mocked SDK clients (no network, no keys)."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from outlier.analysis.schemas import DeepResult, TriageResult
from outlier.demo.fixtures import demo_analysis_fixtures
from outlier.providers.anthropic_provider import AnthropicProvider
from outlier.providers.base import ImageInput, ProviderError
from outlier.providers.gemini_provider import GeminiProvider
from outlier.providers.pricing import estimate_cost, estimate_image_tokens

FIX = demo_analysis_fixtures()
IMG = [ImageInput(data=b"\xff\xd8fake", media_type="image/jpeg", label="photo 0", index=0)]


def _usage(i=100, o=50):
    return SimpleNamespace(input_tokens=i, output_tokens=o)


def test_anthropic_structured_output_and_cost(monkeypatch):
    p = AnthropicProvider.__new__(AnthropicProvider)
    p.model, p._pricing, p._effort = "claude-haiku-5-5", None, "medium"
    client = MagicMock()
    parsed = TriageResult.model_validate(FIX["mohair_cardigan:triage"])
    client.messages.parse.return_value = SimpleNamespace(usage=_usage(1000, 200), stop_reason="end_turn", content=[SimpleNamespace(type="text", text="{}")], parsed_output=parsed)
    p._client = client
    res = p.analyze(images=IMG, system="sys", prompt="go", schema=TriageResult, stage="triage")
    assert res.parsed.interest_score == 82
    assert res.tokens_in == 1000 and res.tokens_out == 200
    assert res.est_cost_usd == pytest.approx(1000 / 1e6 * 0.10 + 200 / 1e6 * 0.50)
    kwargs = client.messages.parse.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-5-5" and kwargs["output_format"] is TriageResult
    assert kwargs["output_config"] == {"effort": "medium"}
    assert "tools" not in kwargs
    blocks = kwargs["messages"][0]["content"]
    assert blocks[1]["type"] == "image" and blocks[1]["source"]["media_type"] == "image/jpeg"


def test_anthropic_zoom_tool_loop():
    p = AnthropicProvider.__new__(AnthropicProvider)
    p.model, p._pricing, p._effort = "claude-opus-5-5", None, "high"
    client = MagicMock()
    tool_use = SimpleNamespace(type="tool_use", id="tu1", name="zoom_image", input={"image_index": 0, "x": 0.4, "y": 0.5, "w": 0.2, "h": 0.1, "reason": "label"})
    first = SimpleNamespace(usage=_usage(500, 40), stop_reason="tool_use", content=[tool_use], parsed_output=None)
    parsed = DeepResult.model_validate(FIX["mohair_cardigan:deep"])
    second = SimpleNamespace(usage=_usage(700, 900), stop_reason="end_turn", content=[SimpleNamespace(type="text", text="{}")], parsed_output=parsed)
    client.messages.parse.side_effect = [first, second]
    p._client = client
    crops = []

    def zoom(req):
        crops.append(req)
        return ImageInput(data=b"crop", media_type="image/jpeg", label="zoom", index=0)

    res = p.analyze(images=IMG, system="sys", prompt="go", schema=DeepResult, zoom=zoom, max_zoom_calls=3, stage="deep")
    assert res.parsed.headline_identification.startswith("1980s Kingstone")
    assert len(res.zoom_calls) == 1 and crops[0]["reason"] == "label"
    assert res.tokens_in == 1200 and res.tokens_out == 940
    second_call = client.messages.parse.call_args_list[1].kwargs
    msgs = second_call["messages"]
    assert msgs[1]["role"] == "assistant" and msgs[2]["role"] == "user"
    assert msgs[2]["content"][0]["type"] == "tool_result" and msgs[2]["content"][0]["tool_use_id"] == "tu1"
    assert second_call["tools"][0]["name"] == "zoom_image" and second_call["tools"][0]["strict"] is True


def test_anthropic_zoom_budget_exhausted_still_returns():
    p = AnthropicProvider.__new__(AnthropicProvider)
    p.model, p._pricing, p._effort = "claude-opus-5-5", None, None
    client = MagicMock()
    tu = SimpleNamespace(type="tool_use", id="t", name="zoom_image", input={"image_index": 0, "x": 0, "y": 0, "w": 0.5, "h": 0.5, "reason": "r"})
    tool_resp = SimpleNamespace(usage=_usage(), stop_reason="tool_use", content=[tu], parsed_output=None)
    parsed = DeepResult.model_validate(FIX["mohair_cardigan:deep"])
    final = SimpleNamespace(usage=_usage(), stop_reason="end_turn", content=[], parsed_output=parsed)
    client.messages.parse.side_effect = [tool_resp, tool_resp, final]
    p._client = client
    res = p.analyze(images=IMG, system="s", prompt="p", schema=DeepResult, zoom=lambda r: IMG[0], max_zoom_calls=1, stage="deep")
    assert res.parsed is parsed and len(res.zoom_calls) == 1
    assert "tools" not in client.messages.parse.call_args_list[2].kwargs


def test_anthropic_refusal_and_auth_errors():
    import anthropic

    p = AnthropicProvider.__new__(AnthropicProvider)
    p.model, p._pricing, p._effort = "claude-opus-5-5", None, None
    client = MagicMock()
    client.messages.parse.return_value = SimpleNamespace(usage=_usage(), stop_reason="refusal", content=[], parsed_output=None)
    p._client = client
    with pytest.raises(ProviderError, match="declined"):
        p.analyze(images=IMG, system="s", prompt="p", schema=TriageResult)
    client.messages.parse.side_effect = anthropic.AuthenticationError(message="bad key", response=MagicMock(status_code=401), body=None)
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        p.analyze(images=IMG, system="s", prompt="p", schema=TriageResult)


def test_anthropic_falls_back_to_text_json():
    p = AnthropicProvider.__new__(AnthropicProvider)
    p.model, p._pricing, p._effort = "claude-haiku-5-5", None, None
    client = MagicMock()
    txt = json.dumps(FIX["mohair_cardigan:triage"])
    client.messages.parse.return_value = SimpleNamespace(usage=_usage(), stop_reason="end_turn", content=[SimpleNamespace(type="text", text=txt)], parsed_output=None)
    p._client = client
    assert p.analyze(images=IMG, system="s", prompt="p", schema=TriageResult).parsed.domain == "clothing"
    client.messages.parse.return_value = SimpleNamespace(usage=_usage(), stop_reason="end_turn", content=[SimpleNamespace(type="text", text="not json")], parsed_output=None)
    with pytest.raises(ProviderError, match="schema"):
        p.analyze(images=IMG, system="s", prompt="p", schema=TriageResult)


def test_gemini_structured_output():
    p = GeminiProvider.__new__(GeminiProvider)
    p.model, p._pricing = "gemini-2.5-flash", None
    client = MagicMock()
    parsed = TriageResult.model_validate(FIX["silvertone_necklace:triage"])
    client.models.generate_content.return_value = SimpleNamespace(
        usage_metadata=SimpleNamespace(prompt_token_count=800, candidates_token_count=300), text=json.dumps(parsed.model_dump()),
        parsed=parsed, function_calls=None, candidates=[])
    p._client = client
    res = p.analyze(images=IMG, system="sys", prompt="go", schema=TriageResult, stage="triage")
    assert res.parsed.domain == "jewelry" and res.tokens_in == 800
    cfg = client.models.generate_content.call_args.kwargs["config"]
    assert cfg.response_mime_type == "application/json" and cfg.response_schema is TriageResult
    assert res.est_cost_usd == pytest.approx(800 / 1e6 * 0.30 + 300 / 1e6 * 2.5)


def test_gemini_zoom_loop_then_structured():
    from google.genai import types

    p = GeminiProvider.__new__(GeminiProvider)
    p.model, p._pricing = "gemini-2.5-pro", None
    client = MagicMock()
    fc = SimpleNamespace(name="zoom_image", args={"image_index": 0, "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "reason": "mark"})
    inspect_resp = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5), function_calls=[fc],
                                   candidates=[SimpleNamespace(content=types.Content(role="model", parts=[types.Part.from_text(text="zooming")]))], text=None, parsed=None)
    done_resp = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5), function_calls=[],
                                candidates=[SimpleNamespace(content=types.Content(role="model", parts=[types.Part.from_text(text="INSPECTION COMPLETE")]))], text=None, parsed=None)
    parsed = DeepResult.model_validate(FIX["silvertone_necklace:deep"])
    final = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=400), function_calls=None, candidates=[], text="{}", parsed=parsed)
    client.models.generate_content.side_effect = [inspect_resp, done_resp, final]
    p._client = client
    res = p.analyze(images=IMG, system="s", prompt="p", schema=DeepResult, zoom=lambda r: IMG[0], max_zoom_calls=4, stage="deep")
    assert res.parsed.domain == "jewelry" and len(res.zoom_calls) == 1
    assert res.tokens_in == 120 and client.models.generate_content.call_count == 3


def test_gemini_error_mapping():
    from google.genai import errors

    p = GeminiProvider.__new__(GeminiProvider)
    p.model, p._pricing = "gemini-2.5-flash", None
    client = MagicMock()
    client.models.generate_content.side_effect = errors.APIError(403, {"error": {"message": "denied"}})
    p._client = client
    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        p.analyze(images=IMG, system="s", prompt="p", schema=TriageResult)


def test_pricing_helpers():
    assert estimate_cost("unknown-model", 1000, 1000) == 0.0
    assert estimate_cost("claude-opus-5-5", 1_000_000, 0) == 4.0
    assert estimate_image_tokens(1092, 1092, "anthropic") == 1589
    assert estimate_image_tokens(300, 300, "gemini") == 258
    assert estimate_image_tokens(1536, 768, "gemini") == 516


def test_registry_resolution(monkeypatch):
    from outlier.config import reset_caches
    from outlier.providers import registry
    from outlier.providers.base import ProviderNotConfigured

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    reset_caches()
    with pytest.raises(ProviderNotConfigured):
        registry.resolve_provider_name("triage", None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    reset_caches()
    assert registry.resolve_provider_name("triage", None) == "anthropic"
    assert registry.resolve_provider_name("deep", None) == "anthropic"
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    reset_caches()
    assert registry.resolve_provider_name("triage", None) == "gemini"
    assert registry.resolve_provider_name("deep", None) == "anthropic"
    p = registry.build_provider("triage")
    assert p.name == "gemini" and p.model == "gemini-2.5-flash"
    p = registry.build_provider("deep", "anthropic")
    assert p.name == "anthropic" and p.model == "claude-opus-5-5"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("GEMINI_API_KEY")
    reset_caches()
