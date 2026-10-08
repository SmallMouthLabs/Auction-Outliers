"""Tiered analysis pipeline.

Stage 1 prefilter (rules) -> Stage 2 triage (cheap vision model) -> Stage 3 deep (strong model, zoom tool)
-> discrepancy detection + reference matching -> Identification row -> opportunity recompute.

Caching: each model stage is keyed by a hash of (image sha256s, seller text, schema version, model). Unchanged
inputs are never re-sent to a provider unless force=True.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AnalysisRun, Identification, Listing
from ..providers.base import ProviderError, ProviderNotConfigured, ProviderResult, VisionProvider
from ..providers.registry import build_provider
from ..providers.usage import check_budget, record_usage
from ..settings_store import get_all_settings
from . import discrepancy, prompts
from .images import make_zoom, prepare_inputs
from .prefilter import run_prefilter
from .reference_match import match_references
from .schemas import SCHEMA_VERSION, DeepResult, TriageResult

log = logging.getLogger(__name__)


def _listing_dict(l: Listing) -> dict[str, Any]:
    return {
        "title": l.title, "category": l.category, "description": l.description, "condition_text": l.condition_text,
        "measurements": l.measurements, "current_bid": l.current_bid, "num_bids": l.num_bids,
    }


def _input_hash(l: Listing, stage: str, model: str) -> str:
    h = hashlib.sha256()
    h.update(SCHEMA_VERSION.encode())
    h.update(stage.encode())
    h.update(model.encode())
    h.update(json.dumps(_listing_dict(l), sort_keys=True, default=str).encode())
    for im in l.images:
        h.update((im.sha256 or im.remote_url or "").encode())
    return h.hexdigest()


def _cached_run(db: Session, listing_id: int, stage: str, ih: str) -> AnalysisRun | None:
    return (
        db.query(AnalysisRun)
        .filter(AnalysisRun.listing_id == listing_id, AnalysisRun.stage == stage, AnalysisRun.input_hash == ih,
                AnalysisRun.status == "succeeded")
        .order_by(AnalysisRun.id.desc())
        .first()
    )


def _save_run(db: Session, l: Listing, stage: str, provider: str, model: str | None, status: str, output: dict,
              ih: str | None, res: ProviderResult | None = None, error: str | None = None, duration_ms: int = 0,
              is_demo: bool = False) -> AnalysisRun:
    run = AnalysisRun(
        listing_id=l.id, stage=stage, provider=provider, model=model, status=status, input_hash=ih, output=output,
        tokens_in=res.tokens_in if res else 0, tokens_out=res.tokens_out if res else 0,
        est_cost_usd=res.est_cost_usd if res else 0.0, duration_ms=res.duration_ms if res else duration_ms,
        error=error, is_demo=is_demo,
    )
    db.add(run)
    db.flush()
    return run


def stage_prefilter(db: Session, l: Listing) -> AnalysisRun:
    cfg = get_all_settings(db)["analysis"]
    res = run_prefilter(
        title=l.title, description=l.description, category=l.category, current_bid=l.current_bid,
        image_count=len([i for i in l.images if i.local_path]), cfg=cfg, existing_domain=l.domain,
    )
    if l.domain in ("unknown", None) and res.domain in ("clothing", "jewelry"):
        l.domain = res.domain
    return _save_run(db, l, "prefilter", "rules", None, "succeeded", res.to_dict(), None)


def _provider_for(db: Session, l: Listing, stage: str, provider_name: str | None, model: str | None) -> VisionProvider:
    pricing = get_all_settings(db)["model_pricing_usd_per_1m"]
    if l.is_demo and (provider_name in (None, "auto", "demo")):
        from ..demo.fixtures import demo_analysis_fixtures
        from ..providers.demo_provider import DemoProvider

        p = DemoProvider(demo_analysis_fixtures())
        p.fixture_key = (l.raw or {}).get("demo_fixture_key") or l.source_item_id
        return p
    if provider_name == "demo" and not l.is_demo:
        raise ProviderNotConfigured("The demo provider only works on demo listings; configure a real provider for live items.")
    return build_provider(stage, provider_name, model, pricing)


def _run_vision_stage(db: Session, l: Listing, stage: str, provider: VisionProvider, schema, system: str,
                      prompt: str, max_px: int, zoom_calls: int, force: bool) -> tuple[AnalysisRun, bool]:
    ih = _input_hash(l, stage, provider.model)
    if not force:
        cached = _cached_run(db, l.id, stage, ih)
        if cached:
            return cached, True
    paths = [im.local_path for im in l.images if im.local_path]
    s = get_settings()
    images = prepare_inputs(paths, max_px, s.max_images_per_call)
    if not images:
        raise ProviderError("No local photographs available for analysis. Upload photos or fetch image URLs first.")
    if not provider.is_demo:
        check_budget(db, l.id, est_next_call_usd=0.02 if stage == "triage" else 0.15)
    zoom = make_zoom(paths) if (zoom_calls > 0 and provider.supports_tools) else None
    t0 = time.time()
    try:
        res = provider.analyze(images=images, system=system, prompt=prompt, schema=schema, zoom=zoom,
                               max_zoom_calls=zoom_calls, stage=stage)
    except ProviderError as e:
        record_usage(db, provider=provider.name, model=provider.model, stage=stage, listing_id=l.id,
                     duration_ms=int((time.time() - t0) * 1000), error=str(e))
        _save_run(db, l, stage, provider.name, provider.model, "failed", {}, ih, error=str(e),
                  duration_ms=int((time.time() - t0) * 1000), is_demo=provider.is_demo)
        raise
    if not provider.is_demo:
        record_usage(db, provider=provider.name, model=provider.model, stage=stage, listing_id=l.id, result=res)
    out = res.parsed.model_dump()
    out["_meta"] = {"zoom_calls": res.zoom_calls, "is_demo": res.is_demo, "provider": res.provider, "model": res.model}
    run = _save_run(db, l, stage, provider.name, provider.model, "succeeded", out, ih, res, is_demo=res.is_demo)
    return run, False


def stage_triage(db: Session, l: Listing, provider_name: str | None = None, model: str | None = None, force: bool = False) -> AnalysisRun:
    provider = _provider_for(db, l, "triage", provider_name, model)
    s = get_settings()
    domain_hint = l.domain if l.domain in ("clothing", "jewelry") else "unknown"
    run, _ = _run_vision_stage(db, l, "triage", provider, TriageResult, prompts.TRIAGE_SYSTEM,
                               prompts.triage_prompt(_listing_dict(l), domain_hint), s.triage_image_max_px, 0, force)
    out = run.output
    if l.domain not in ("clothing", "jewelry") and out.get("domain") in ("clothing", "jewelry"):
        l.domain = out["domain"]
    return run


def stage_deep(db: Session, l: Listing, provider_name: str | None = None, model: str | None = None, force: bool = False,
               triage_output: dict | None = None) -> AnalysisRun:
    provider = _provider_for(db, l, "deep", provider_name, model)
    s = get_settings()
    domain = l.domain if l.domain in ("clothing", "jewelry") else ((triage_output or {}).get("domain") or "clothing")
    texts = [l.title, l.description or "", l.category or ""]
    if triage_output:
        texts += [t.get("text", "") for t in triage_output.get("visible_text", [])]
        texts += [c.get("label", "") for c in triage_output.get("quick_candidates", [])]
    refs = match_references(db, domain=domain, texts=texts)
    run, cached = _run_vision_stage(db, l, "deep", provider, DeepResult, prompts.DEEP_SYSTEM,
                                    prompts.deep_prompt(_listing_dict(l), domain, triage_output, refs),
                                    s.deep_image_max_px, s.max_zoom_calls, force)
    out = dict(run.output)
    # post-processing: discrepancy signal + reference matches on the transcribed text
    deep_texts = texts + [o.get("text", "") for o in out.get("observed_facts", [])]
    if out.get("clothing"):
        deep_texts += [t.get("text", "") for t in out["clothing"].get("label_texts", [])]
        deep_texts += [out["clothing"].get("brand_or_manufacturer") or ""]
    if out.get("jewelry"):
        deep_texts += [t.get("text", "") for t in out["jewelry"].get("makers_marks", []) + out["jewelry"].get("hallmarks_and_inscriptions", [])]
        deep_texts += [out["jewelry"].get("potential_maker") or ""]
    refs2 = match_references(db, domain=out.get("domain") or domain, texts=deep_texts)
    disc = discrepancy.detect(l.title, l.description, out, out.get("domain") or domain)
    # record as current identification (supersede older AI identifications; keep user corrections current)
    for ident in l.identifications:
        if ident.is_current and ident.origin != "user":
            ident.is_current = False
    has_user = any(i.is_current and i.origin == "user" for i in l.identifications)
    ident = Identification(
        listing_id=l.id, origin="demo" if run.is_demo else "ai", run_id=run.id, domain=out.get("domain") or domain,
        summary=out.get("headline_identification", "")[:500], confidence=out.get("overall_confidence"),
        data={**out, "reference_matches": refs2}, discrepancy=disc,
        warrants_research=bool(out.get("warrants_further_research")), is_current=not has_user, is_demo=run.is_demo,
    )
    db.add(ident)
    l.identifications.append(ident)
    if out.get("domain") in ("clothing", "jewelry"):
        l.domain = out["domain"]
    db.flush()
    return run


def analyze_listing(db: Session, l: Listing, *, mode: str = "auto", provider: str | None = None, model: str | None = None,
                    force: bool = False) -> dict[str, Any]:
    """Run the pipeline. mode: auto (prefilter->triage->deep if justified) | triage | deep | prefilter."""
    summary: dict[str, Any] = {"listing_id": l.id, "stages": []}
    pre = stage_prefilter(db, l)
    summary["stages"].append({"stage": "prefilter", "run_id": pre.id, "passed": pre.output.get("passed"), "reasons": pre.output.get("reasons")})
    if mode == "prefilter":
        return summary
    if mode == "auto" and not pre.output.get("passed") and not force:
        summary["stopped"] = "prefilter"
        return summary
    triage_out = None
    if mode in ("auto", "triage"):
        tr = stage_triage(db, l, provider, model, force)
        triage_out = tr.output
        summary["stages"].append({"stage": "triage", "run_id": tr.id, "cached": tr.status == "cached",
                                  "interest_score": triage_out.get("interest_score"), "escalate": triage_out.get("escalate")})
        if mode == "triage":
            return summary
        thr = get_all_settings(db)["analysis"]["auto_escalate_min_triage_interest"]
        if not (triage_out.get("escalate") or (triage_out.get("interest_score") or 0) >= thr) and not force:
            summary["stopped"] = "triage"
            return summary
    else:
        last_tr = db.query(AnalysisRun).filter(AnalysisRun.listing_id == l.id, AnalysisRun.stage == "triage",
                                              AnalysisRun.status == "succeeded").order_by(AnalysisRun.id.desc()).first()
        triage_out = last_tr.output if last_tr else None
    deep = stage_deep(db, l, provider, model, force, triage_out)
    summary["stages"].append({"stage": "deep", "run_id": deep.id, "headline": deep.output.get("headline_identification"),
                              "confidence": deep.output.get("overall_confidence")})
    return summary
