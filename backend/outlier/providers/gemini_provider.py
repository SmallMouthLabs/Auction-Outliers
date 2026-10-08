"""Google Gemini adapter (google-genai SDK). Structured JSON output via response_schema.

Gemini is used primarily for the low-cost triage stage. The zoom tool loop is implemented with
function calling when max_zoom_calls > 0.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from pydantic import BaseModel

from .base import ProviderError, ProviderResult, VisionProvider, ZoomFn
from .pricing import estimate_cost

log = logging.getLogger(__name__)


class GeminiProvider(VisionProvider):
    name = "gemini"
    supports_tools = True

    def __init__(self, api_key: str, model: str, pricing: dict | None = None):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model = model
        self._pricing = pricing

    def analyze(self, *, images, system, prompt, schema: type[BaseModel], zoom: ZoomFn | None = None,
                max_zoom_calls: int = 0, stage: str = "triage") -> ProviderResult:
        from google.genai import errors, types

        parts: list[Any] = []
        for img in images:
            parts.append(types.Part.from_text(text=f"[Image {img.index}] {img.label}".strip()))
            parts.append(types.Part.from_bytes(data=img.data, mime_type=img.media_type))
        parts.append(types.Part.from_text(text=prompt))
        contents: list[Any] = [types.Content(role="user", parts=parts)]

        zoom_calls: list[dict[str, Any]] = []
        t0 = time.time()
        tokens_in = tokens_out = 0
        try:
            # Phase 1 (optional): free-form inspection with the zoom function.
            if zoom is not None and max_zoom_calls > 0:
                zoom_decl = types.FunctionDeclaration(
                    name="zoom_image",
                    description="Crop and enlarge a region (fractions 0-1) of a listing photo to read labels/hallmarks/stitching.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "image_index": types.Schema(type="INTEGER"),
                            "x": types.Schema(type="NUMBER"), "y": types.Schema(type="NUMBER"),
                            "w": types.Schema(type="NUMBER"), "h": types.Schema(type="NUMBER"),
                            "reason": types.Schema(type="STRING"),
                        },
                        required=["image_index", "x", "y", "w", "h", "reason"],
                    ),
                )
                inspect_cfg = types.GenerateContentConfig(
                    system_instruction=system + "\nFirst inspect details with zoom_image if needed, then say 'INSPECTION COMPLETE'.",
                    tools=[types.Tool(function_declarations=[zoom_decl])],
                )
                for _ in range(max_zoom_calls):
                    resp = self._client.models.generate_content(model=self.model, contents=contents, config=inspect_cfg)
                    um = resp.usage_metadata
                    tokens_in += (um.prompt_token_count or 0) if um else 0
                    tokens_out += (um.candidates_token_count or 0) if um else 0
                    calls = resp.function_calls or []
                    if not calls:
                        if resp.candidates and resp.candidates[0].content:
                            contents.append(resp.candidates[0].content)
                        break
                    contents.append(resp.candidates[0].content)
                    fr_parts = []
                    for fc in calls:
                        args = dict(fc.args or {})
                        zoom_calls.append(args)
                        try:
                            crop = zoom(args)
                            fr_parts.append(types.Part.from_function_response(name=fc.name, response={"result": "crop attached"}))
                            fr_parts.append(types.Part.from_bytes(data=crop.data, mime_type=crop.media_type))
                        except Exception as e:  # noqa: BLE001
                            fr_parts.append(types.Part.from_function_response(name=fc.name, response={"error": str(e)}))
                    contents.append(types.Content(role="user", parts=fr_parts))
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Now produce the final structured JSON answer.")]))

            cfg = types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                max_output_tokens=8000 if stage == "deep" else 3000,
            )
            resp = self._client.models.generate_content(model=self.model, contents=contents, config=cfg)
        except errors.APIError as e:
            code = getattr(e, "code", None)
            if code in (401, 403):
                raise ProviderError("Gemini authentication failed: check GEMINI_API_KEY.") from e
            if code == 429:
                raise ProviderError("Gemini rate limit / quota hit; retry later.") from e
            raise ProviderError(f"Gemini API error {code}: {str(e)[:300]}") from e
        except Exception as e:
            raise ProviderError(f"Gemini request failed: {str(e)[:300]}") from e

        um = resp.usage_metadata
        if um:
            tokens_in += um.prompt_token_count or 0
            tokens_out += um.candidates_token_count or 0
        raw_text = resp.text or ""
        parsed = getattr(resp, "parsed", None)
        if parsed is None:
            try:
                parsed = schema.model_validate_json(raw_text)
            except Exception as e:
                raise ProviderError(f"Model output did not match schema: {e}") from e
        elif isinstance(parsed, dict):
            parsed = schema.model_validate(parsed)
        return ProviderResult(
            parsed=parsed, raw_text=raw_text or json.dumps(parsed.model_dump()), provider=self.name, model=self.model,
            tokens_in=tokens_in, tokens_out=tokens_out,
            est_cost_usd=estimate_cost(self.model, tokens_in, tokens_out, self._pricing),
            duration_ms=int((time.time() - t0) * 1000), zoom_calls=zoom_calls,
        )
