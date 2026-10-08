"""Anthropic (Claude) adapter.

- Structured output via client.messages.parse(output_format=<pydantic model>).
- Optional zoom tool loop for the deep stage: the model may request crops of listing photos to inspect
  labels, hallmarks, stitching; we return the crop as an image tool result.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Any

from pydantic import BaseModel

from .base import ImageInput, ProviderError, ProviderResult, VisionProvider, ZoomFn
from .pricing import estimate_cost

log = logging.getLogger(__name__)

ZOOM_TOOL = {
    "name": "zoom_image",
    "description": (
        "Crop and enlarge a region of one of the listing photographs so you can read labels, hallmarks, "
        "maker's marks, inscriptions, stitching or construction details. Coordinates are fractions (0-1) of the "
        "image width/height. Use it only when a detail is too small to read in the original image."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "image_index": {"type": "integer", "description": "0-based index of the image."},
            "x": {"type": "number", "minimum": 0, "maximum": 1},
            "y": {"type": "number", "minimum": 0, "maximum": 1},
            "w": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
            "h": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
            "reason": {"type": "string"},
        },
        "required": ["image_index", "x", "y", "w", "h", "reason"],
        "additionalProperties": False,
    },
    "strict": True,
}


def _image_block(img: ImageInput) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": img.media_type, "data": base64.b64encode(img.data).decode()},
    }


class AnthropicProvider(VisionProvider):
    name = "anthropic"
    supports_tools = True

    def __init__(self, api_key: str, model: str, pricing: dict | None = None, effort: str | None = None):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._pricing = pricing
        self._effort = effort

    def analyze(self, *, images, system, prompt, schema: type[BaseModel], zoom: ZoomFn | None = None,
                max_zoom_calls: int = 0, stage: str = "triage") -> ProviderResult:
        import anthropic

        content: list[dict[str, Any]] = []
        for img in images:
            content.append({"type": "text", "text": f"[Image {img.index}] {img.label}".strip()})
            content.append(_image_block(img))
        content.append({"type": "text", "text": prompt})
        messages: list[dict[str, Any]] = [{"role": "user", "content": content}]

        tools = [ZOOM_TOOL] if (zoom is not None and max_zoom_calls > 0) else []
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=8000 if stage == "deep" else 3000,
            system=system,
            messages=messages,
            output_format=schema,
        )
        if tools:
            kwargs["tools"] = tools
        if self._effort:
            kwargs["output_config"] = {"effort": self._effort}

        t0 = time.time()
        tokens_in = tokens_out = 0
        zoom_calls: list[dict[str, Any]] = []
        parsed = None
        raw_text = ""
        stop_reason = None
        try:
            for _ in range(max_zoom_calls + 2):
                resp = self._client.messages.parse(**kwargs)
                tokens_in += resp.usage.input_tokens
                tokens_out += resp.usage.output_tokens
                stop_reason = resp.stop_reason
                if resp.stop_reason == "refusal":
                    raise ProviderError("The model declined this request (safety refusal).")
                tool_uses = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
                if tool_uses and zoom is not None and len(zoom_calls) < max_zoom_calls:
                    messages.append({"role": "assistant", "content": resp.content})
                    results = []
                    for tu in tool_uses:
                        inp = dict(tu.input)
                        zoom_calls.append(inp)
                        try:
                            crop = zoom(inp)
                            results.append({
                                "type": "tool_result", "tool_use_id": tu.id,
                                "content": [{"type": "text", "text": f"Crop of image {inp.get('image_index')} ({inp.get('reason','')})"}, _image_block(crop)],
                            })
                        except Exception as e:  # noqa: BLE001
                            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": f"zoom failed: {e}", "is_error": True})
                    messages.append({"role": "user", "content": results})
                    kwargs["messages"] = messages
                    continue
                if tool_uses:
                    # zoom budget exhausted: answer the tool calls and ask for the final structured answer
                    messages.append({"role": "assistant", "content": resp.content})
                    messages.append({"role": "user", "content": [
                        *[{"type": "tool_result", "tool_use_id": tu.id, "content": "zoom budget exhausted; answer with what you have"} for tu in tool_uses],
                        {"type": "text", "text": "Provide your final structured answer now."},
                    ]})
                    kwargs["messages"] = messages
                    kwargs.pop("tools", None)
                    continue
                parsed = getattr(resp, "parsed_output", None)
                raw_text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
                break
        except anthropic.AuthenticationError as e:
            raise ProviderError("Anthropic authentication failed: check ANTHROPIC_API_KEY.") from e
        except anthropic.RateLimitError as e:
            raise ProviderError("Anthropic rate limit hit; retry later.") from e
        except anthropic.APIStatusError as e:
            raise ProviderError(f"Anthropic API error {e.status_code}: {getattr(e, 'message', str(e))[:300]}") from e
        except anthropic.APIConnectionError as e:
            raise ProviderError("Could not connect to the Anthropic API.") from e

        if parsed is None and raw_text:
            try:
                parsed = schema.model_validate_json(raw_text)
            except Exception as e:
                raise ProviderError(f"Model output did not match schema: {e}") from e
        if parsed is None:
            raise ProviderError(f"No structured output returned (stop_reason={stop_reason}).")
        return ProviderResult(
            parsed=parsed, raw_text=raw_text, provider=self.name, model=self.model,
            tokens_in=tokens_in, tokens_out=tokens_out,
            est_cost_usd=estimate_cost(self.model, tokens_in, tokens_out, self._pricing),
            duration_ms=int((time.time() - t0) * 1000), zoom_calls=zoom_calls, stop_reason=stop_reason,
        )
