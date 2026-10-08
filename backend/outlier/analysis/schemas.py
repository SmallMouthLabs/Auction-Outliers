"""Structured, validated output schemas for the identification engine.

Design rules
- Observations (what is visible) are separated from hypotheses (what it might be) and from confirmed facts.
- Every candidate identification carries evidence and a model-reported confidence (uncalibrated).
- Precious metals / designer authenticity are never 'confirmed' from appearance alone; see materials fields.
- Schemas are kept Gemini- and Claude-compatible: no unions, no free-form dicts.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Confidence = float  # 0..1, model-reported, uncalibrated
Domain = Literal["clothing", "jewelry", "other"]
EvidenceLevel = Literal["observed", "inferred", "confirmed"]


class Observation(BaseModel):
    """A fact directly visible in a photograph (not an interpretation)."""

    text: str = Field(description="What is visible, stated plainly.")
    image_index: int | None = Field(default=None, description="0-based index of the image this was seen in.")
    region: str | None = Field(default=None, description="Where in the image (e.g. 'neck label', 'clasp', 'back of pendant').")


class Candidate(BaseModel):
    """A candidate identification (brand/designer/model/era) with evidence."""

    label: str = Field(description="Short identification, e.g. 'Pendleton wool shirt jacket, 1970s'.")
    brand_or_maker: str | None = None
    confidence: Confidence = Field(ge=0, le=1, description="Model-reported confidence 0-1 (uncalibrated).")
    evidence: list[str] = Field(default_factory=list, description="Specific visual or textual evidence.")
    counter_evidence: list[str] = Field(default_factory=list)
    status: EvidenceLevel = Field(default="inferred", description="'confirmed' only with unambiguous visible proof.")


class ValueIndicator(BaseModel):
    indicator: str = Field(description="Characteristic that may indicate resale value.")
    why_it_matters: str
    strength: Literal["weak", "moderate", "strong"] = "moderate"


class ConditionIssue(BaseModel):
    issue: str
    severity: Literal["minor", "moderate", "major"] = "minor"
    image_index: int | None = None


class LabelText(BaseModel):
    text: str = Field(description="Transcribed label / hallmark / inscription text, verbatim; use '?' for unreadable characters.")
    label_type: str | None = Field(default=None, description="e.g. 'brand label', 'care label', 'union label', 'hallmark', 'maker's mark', 'inscription'.")
    image_index: int | None = None
    legibility: Literal["clear", "partial", "poor"] = "clear"


class ResearchQuery(BaseModel):
    query: str = Field(description="A search string for sold-listing research.")
    marketplace: str = Field(default="ebay")
    purpose: str | None = None


class MaterialHypothesis(BaseModel):
    """For jewelry: materials are hypotheses unless there is a verifiable mark AND it is consistent with construction."""

    material: str = Field(description="e.g. 'sterling silver', 'gold-filled', '14k gold', 'silver tone base metal'.")
    basis: list[str] = Field(default_factory=list, description="Evidence: hallmark text, color/wear patterns, construction, magnet test unknown, etc.")
    confidence: Confidence = Field(ge=0, le=1)
    verification_needed: str | None = Field(default=None, description="What a buyer must do to confirm (acid test, XRF, weigh, loupe).")


class LotComponent(BaseModel):
    """An individually interesting item inside a multi-item lot."""

    description: str
    image_index: int | None = None
    why_interesting: str
    candidate: str | None = None
    confidence: Confidence = Field(default=0.3, ge=0, le=1)


class DiscrepancyFinding(BaseModel):
    """A mismatch between the seller's description and what the photographs show."""

    seller_claim: str = Field(description="What the seller's title/description says (or omits).")
    visual_evidence: str = Field(description="What the images show instead.")
    direction: Literal["seller_undervalues", "seller_overvalues", "neutral"] = "seller_undervalues"
    strength: Literal["weak", "moderate", "strong"] = "moderate"
    image_index: int | None = None


# ----------------------------------------------------------------------------------------------
# Stage 2: low-cost triage
# ----------------------------------------------------------------------------------------------
class TriageResult(BaseModel):
    domain: Domain
    item_summary: str = Field(description="One-line neutral description of what is pictured.")
    observations: list[Observation] = Field(default_factory=list, description="Up to ~10 key visible facts.")
    visible_text: list[LabelText] = Field(default_factory=list, description="Any labels/marks/inscriptions seen.")
    quick_candidates: list[Candidate] = Field(default_factory=list, description="0-3 candidate identifications.")
    value_indicators: list[ValueIndicator] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list, description="Signs of reproduction, damage, low quality.")
    interest_score: int = Field(ge=0, le=100, description="Heuristic 0-100: how much this deserves expensive analysis.")
    escalate: bool = Field(description="True if a deeper analysis pass is justified.")
    escalate_reason: str
    images_to_inspect: list[int] = Field(default_factory=list, description="Image indexes worth zooming into (labels, hallmarks, stitching).")
    seller_vs_visual_mismatch: str | None = Field(default=None, description="If the seller's title seems to miss something, say what.")


# ----------------------------------------------------------------------------------------------
# Stage 3: deep identification (domain-specific)
# ----------------------------------------------------------------------------------------------
class ClothingDetails(BaseModel):
    garment_type: str
    brand_or_manufacturer: str | None = None
    brand_confidence: Confidence = Field(default=0.0, ge=0, le=1)
    label_texts: list[LabelText] = Field(default_factory=list)
    era_estimate: str | None = Field(default=None, description="e.g. 'late 1960s-early 1970s'.")
    era_evidence: list[str] = Field(default_factory=list, description="Union labels, RN numbers, tag style, zipper brand, stitching...")
    fabric_and_construction: list[str] = Field(default_factory=list)
    stitching_and_seams: list[str] = Field(default_factory=list)
    country_of_manufacture: str | None = None
    country_evidence: str | None = None
    graphics_or_prints: str | None = None
    model_names_or_numbers: list[str] = Field(default_factory=list)
    size_and_measurements: str | None = None
    collectible_characteristics: list[str] = Field(default_factory=list)
    authenticity_indicators: list[str] = Field(default_factory=list)
    expert_inspection_points: list[str] = Field(default_factory=list, description="Features that warrant expert / in-hand inspection.")


class JewelryDetails(BaseModel):
    jewelry_type: str
    makers_marks: list[LabelText] = Field(default_factory=list)
    hallmarks_and_inscriptions: list[LabelText] = Field(default_factory=list)
    design_characteristics: list[str] = Field(default_factory=list)
    materials: list[MaterialHypothesis] = Field(default_factory=list, description="Hypotheses, never confirmed by appearance alone.")
    construction_techniques: list[str] = Field(default_factory=list)
    potential_maker: str | None = None
    maker_confidence: Confidence = Field(default=0.0, ge=0, le=1)
    stylistic_period: str | None = None
    period_evidence: list[str] = Field(default_factory=list)
    stones_or_other_materials: list[str] = Field(default_factory=list)
    collectible_characteristics: list[str] = Field(default_factory=list)
    authenticity_concerns: list[str] = Field(default_factory=list)
    lot_components: list[LotComponent] = Field(default_factory=list, description="For lots: individually valuable pieces.")
    melt_value_note: str = Field(
        default="Not computed: metal content and weight are unverified.",
        description="Must not compute melt value from unverified material/weight.",
    )


class DeepResult(BaseModel):
    domain: Domain
    headline_identification: str = Field(description="Best single-line identification for the dashboard.")
    overall_confidence: Confidence = Field(ge=0, le=1, description="Model-reported, uncalibrated.")
    observed_facts: list[Observation] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list, description="Ranked candidate identifications with evidence.")
    alternative_explanations: list[str] = Field(default_factory=list, description="Plausible alternatives (reproduction, later reissue, misattribution).")
    clothing: ClothingDetails | None = None
    jewelry: JewelryDetails | None = None
    condition_issues: list[ConditionIssue] = Field(default_factory=list)
    value_indicators: list[ValueIndicator] = Field(default_factory=list)
    discrepancies: list[DiscrepancyFinding] = Field(default_factory=list, description="Seller description vs visual evidence.")
    missing_information: list[str] = Field(default_factory=list, description="What is needed to value this item properly.")
    research_queries: list[ResearchQuery] = Field(default_factory=list)
    warrants_further_research: bool
    research_rationale: str
    demand_indicator: Literal["high", "medium", "low", "unknown"] = "unknown"
    liquidity_indicator: Literal["high", "medium", "low", "unknown"] = "unknown"
    risk_flags: list[str] = Field(default_factory=list, description="Authenticity / condition / legal risks.")


class ZoomRequest(BaseModel):
    """Tool input for the zoom/crop inspection tool."""

    image_index: int = Field(description="0-based image index.")
    x: float = Field(ge=0, le=1, description="Left edge of crop as fraction of width.")
    y: float = Field(ge=0, le=1, description="Top edge of crop as fraction of height.")
    w: float = Field(gt=0, le=1, description="Crop width as fraction of width.")
    h: float = Field(gt=0, le=1, description="Crop height as fraction of height.")
    reason: str = Field(description="What you expect to see (label, hallmark, stitching...).")


SCHEMA_VERSION = "1.0"
