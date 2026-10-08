/* Types derived from docs/api-samples.json and docs/openapi.json */

export type Tier = "HIGH_CONFIDENCE" | "SPECULATIVE_HIGH_UPSIDE" | "NEEDS_RESEARCH" | "LOW_VALUE";
export type EvidenceQuality = "high" | "medium" | "low" | "none";
export type Domain = "clothing" | "jewelry" | "other" | "unknown";
export type IdentOrigin = "user" | "ai" | "demo" | string;
export type WatchStatus = "watching" | "bidding" | "won" | "lost" | "passed" | "archived";
export type CompType = "exact" | "same_maker" | "category" | "active";

export interface ApiErrorBody {
  detail: string | { loc: (string | number)[]; msg: string; type: string }[];
  code?: string;
}

export interface ImageOut {
  id: number;
  position: number;
  remote_url: string | null;
  url: string;
  sha256: string | null;
  width: number | null;
  height: number | null;
  fetch_error: string | null;
  is_demo: boolean;
}

export interface IdentificationBrief {
  summary: string;
  confidence: number | null;
  origin: IdentOrigin;
  domain: string | null;
  warrants_research: boolean;
  misidentification_signal: number | null;
  is_demo: boolean;
}

export interface ValuationBrief {
  conservative: number | null;
  expected: number | null;
  optimistic: number | null;
  evidence_quality: EvidenceQuality;
  is_speculative: boolean;
  n_sold_comps: number;
  method: string;
}

export interface OpportunityComponents {
  score: number;
  tier: Tier;
  components: Record<string, number>;
  weights: Record<string, number>;
  time_factor: number;
  hours_left: number | null;
  feedback_adjustment: number;
  label: string;
}

export interface OpportunityFinance {
  expected_profit: number | null;
  expected_roi_pct: number | null;
  max_bid: number | null;
  break_even_bid: number | null;
  risk_adjusted_profit: number | null;
  complete: boolean;
  unknown_costs: string[];
  resale_low: number | null;
  resale_expected: number | null;
  resale_high: number | null;
  evidence_quality: EvidenceQuality;
  is_speculative: boolean;
  platform: string;
  over_max_bid: boolean;
}

export interface Opportunity {
  score: number | null;
  tier: Tier | null;
  components: OpportunityComponents | null;
  finance: OpportunityFinance | null;
  computed_at: string | null;
}

export interface WatchlistEntry {
  id: number;
  listing_id: number;
  status: WatchStatus;
  user_max_bid: number | null;
  remind_minutes_before_end: number | null;
  reminder_sent_at: string | null;
  notes: string | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ListingSummary {
  id: number;
  source: string;
  source_item_id: string | null;
  source_url: string | null;
  extraction_method: string | null;
  is_demo: boolean;
  title: string;
  category: string | null;
  seller: string | null;
  domain: Domain | string | null;
  current_bid: number | null;
  num_bids: number | null;
  buy_now_price: number | null;
  ends_at: string | null;
  shipping_cost: number | null;
  handling_fee: number | null;
  status: string;
  archived: boolean;
  first_seen_at: string | null;
  last_updated_at: string | null;
  last_verified_at: string | null;
  image_count: number;
  thumbnail: ImageOut | null;
  identification: IdentificationBrief | null;
  valuation: ValuationBrief | null;
  opportunity: Opportunity | null;
  watchlist: WatchlistEntry | null;
  feedback_labels: string[];
}

export interface ListingsResponse {
  total: number;
  items: ListingSummary[];
}

export interface Snapshot {
  id: number;
  captured_at: string | null;
  source: string;
  current_bid: number | null;
  num_bids: number | null;
  ends_at: string | null;
  shipping_cost: number | null;
  status: string | null;
}

export interface LabelText {
  text: string;
  label_type: string | null;
  image_index: number | null;
  legibility: string | null;
}

export interface ObservedFact {
  text: string;
  image_index: number | null;
  region: string | null;
}

export interface Candidate {
  label: string;
  brand_or_maker: string | null;
  confidence: number | null;
  evidence: string[];
  counter_evidence: string[];
  status: string | null;
}

export interface ClothingDetail {
  garment_type: string | null;
  brand_or_manufacturer: string | null;
  brand_confidence: number | null;
  label_texts: LabelText[];
  era_estimate: string | null;
  era_evidence: string[];
  fabric_and_construction: string[];
  stitching_and_seams: string[];
  country_of_manufacture: string | null;
  country_evidence: string | null;
  graphics_or_prints: string | null;
  model_names_or_numbers: string[];
  size_and_measurements: string | null;
  collectible_characteristics: string[];
  authenticity_indicators: string[];
  expert_inspection_points: string[];
}

export interface MaterialHypothesis {
  material: string;
  basis: string[];
  confidence: number | null;
  verification_needed: string | null;
}

export interface JewelryDetail {
  jewelry_type: string | null;
  makers_marks: LabelText[];
  hallmarks_and_inscriptions: LabelText[];
  design_characteristics: string[];
  materials: MaterialHypothesis[];
  construction_techniques: string[];
  potential_maker: string | null;
  maker_confidence: number | null;
  stylistic_period: string | null;
  period_evidence: string[];
  stones_or_other_materials: string[];
  collectible_characteristics: string[];
  authenticity_concerns: string[];
  lot_components: (string | Record<string, unknown>)[];
  melt_value_note: string | null;
}

export interface ConditionIssue {
  issue: string;
  severity: string | null;
  image_index: number | null;
}

export interface ValueIndicator {
  indicator: string;
  why_it_matters: string | null;
  strength: string | null;
}

export interface Discrepancy {
  seller_claim: string;
  visual_evidence: string;
  direction?: string | null;
  strength: string | null;
  image_index: number | null;
  source?: string;
}

export interface ResearchQuery {
  query: string;
  marketplace: string | null;
  purpose: string | null;
}

export interface ReferenceMatch {
  id: number;
  name: string;
  entry_type: string;
  domain: string;
  category: string | null;
  characteristics: string | null;
  identifiers: string[];
  typical_low: number | null;
  typical_high: number | null;
  demand: string | null;
  liquidity: string | null;
  match_score: number;
  hits: string[];
  is_demo: boolean;
}

export interface IdentificationData {
  domain?: string;
  headline_identification?: string;
  overall_confidence?: number;
  observed_facts?: ObservedFact[];
  candidates?: Candidate[];
  alternative_explanations?: string[];
  clothing?: ClothingDetail | null;
  jewelry?: JewelryDetail | null;
  condition_issues?: ConditionIssue[];
  value_indicators?: ValueIndicator[];
  discrepancies?: Discrepancy[];
  missing_information?: string[];
  research_queries?: ResearchQuery[];
  warrants_further_research?: boolean;
  research_rationale?: string | null;
  demand_indicator?: string | null;
  liquidity_indicator?: string | null;
  risk_flags?: string[];
  reference_matches?: ReferenceMatch[];
  user_correction?: { brand_or_maker: string | null; era: string | null; notes: string | null };
  _meta?: { zoom_calls?: unknown[]; is_demo?: boolean; provider?: string; model?: string };
  [k: string]: unknown;
}

export interface DiscrepancyBlock {
  signal: number | null;
  raw_signal?: number | null;
  findings: Discrepancy[];
  note?: string;
}

export interface IdentificationFull {
  id: number;
  origin: IdentOrigin;
  run_id: number | null;
  domain: string | null;
  summary: string;
  confidence: number | null;
  data: IdentificationData;
  discrepancy: DiscrepancyBlock | Record<string, never> | null;
  warrants_research: boolean;
  is_current: boolean;
  is_demo: boolean;
  created_at: string | null;
}

export interface ValuationDetail {
  method: string;
  conservative: number | null;
  expected: number | null;
  optimistic: number | null;
  is_speculative: boolean;
  evidence_quality: EvidenceQuality;
  n_sold_comps: number;
  used_comp_ids?: number[];
  excluded?: { comp_id?: number; id?: number; reason?: string; title?: string }[] | number[];
  active_listing_context?: { n?: number; min_asking?: number; median_asking?: number; max_asking?: number; note?: string } | Record<string, never>;
  notes?: string[];
  stats?: Record<string, number | string | null>;
  note?: string;
  [k: string]: unknown;
}

export interface ValuationFull {
  id: number;
  method: string;
  conservative: number | null;
  expected: number | null;
  optimistic: number | null;
  is_speculative: boolean;
  evidence_quality: EvidenceQuality;
  n_sold_comps: number;
  detail: ValuationDetail;
  created_at: string | null;
}

export interface Comparable {
  id: number;
  listing_id: number;
  title: string;
  marketplace: string | null;
  url: string | null;
  sold_date: string | null;
  price: number | null;
  shipping_included: boolean | null;
  shipping_amount: number | null;
  is_sold: boolean;
  accepted_offer: boolean;
  comp_type: CompType | string;
  similarity: number | null;
  evidence_quality: EvidenceQuality | string;
  condition: string | null;
  differences: string | null;
  source: string;
  is_demo: boolean;
  created_at: string | null;
}

export interface AnalysisRun {
  id: number;
  stage: string;
  provider: string | null;
  model: string | null;
  status: string;
  tokens_in: number | null;
  tokens_out: number | null;
  est_cost_usd: number | null;
  duration_ms: number | null;
  error: string | null;
  is_demo: boolean;
  created_at: string | null;
  input_hash?: string | null;
  output?: Record<string, unknown> | null;
}

export interface FeedbackItem {
  id: number;
  label: string;
  note: string | null;
  created_at: string | null;
}

export interface NoteItem {
  id: number;
  text: string;
  flagged: boolean;
  resolved: boolean;
  created_at: string | null;
}

export interface Outcome {
  purchased: boolean | null;
  purchase_price: number | null;
  acquisition_expenses: number | null;
  purchased_at: string | null;
  sold: boolean | null;
  resale_price: number | null;
  selling_fees: number | null;
  resale_platform: string | null;
  sold_at: string | null;
  days_to_sale: number | null;
  realized_profit: number | null;
  notes: string | null;
}

export interface ListingDetail extends ListingSummary {
  description: string | null;
  other_costs: Record<string, number>;
  measurements: Record<string, unknown>;
  condition_text: string | null;
  assumptions: Record<string, unknown>;
  user_notes: string | null;
  raw: Record<string, unknown>;
  images: ImageOut[];
  snapshots: Snapshot[];
  identification_full: IdentificationFull | null;
  identification_history: IdentificationFull[];
  valuation_full: ValuationFull | null;
  comparables: Comparable[];
  analysis_runs: AnalysisRun[];
  feedback: FeedbackItem[];
  notes: NoteItem[];
  outcome: Outcome | null;
}

/* ---------- finance ---------- */
export interface AcquisitionBreakdown {
  bid: number;
  buyer_premium: number;
  sales_tax: number;
  incoming_shipping: number;
  handling_fee: number;
  other: number;
}

export interface FinanceScenario {
  bid: number;
  acquisition_total: number;
  acquisition_breakdown: AcquisitionBreakdown;
  resale_price: number;
  selling_fees: number;
  resale_costs: number;
  net_proceeds: number;
  profit: number;
  roi_pct: number;
  gross_margin_pct: number;
  net_margin_pct: number;
  break_even_bid: number;
  max_bid: number;
  max_bid_binding_constraint: string | null;
  unknown_costs: string[];
  assumed_costs: Record<string, number>;
  complete: boolean;
  notes: string[];
  meta?: {
    scenario_weights?: number[];
    evidence_quality?: string;
    identification_confidence?: number;
    confidence_haircut_pct?: number;
    label?: string;
    estimated_months_to_sell?: number;
    holding_cost?: number;
  };
}

export interface SensitivityCell {
  resale_price: number;
  incoming_shipping: number;
  profit: number;
  max_bid: number;
  roi_pct: number;
}

export interface FinanceResponse {
  platform: string;
  bid_used: number;
  valuation: {
    method: string;
    is_speculative: boolean;
    evidence_quality: EvidenceQuality;
    n_sold_comps: number;
    conservative: number | null;
    expected: number | null;
    optimistic: number | null;
    notes: string[];
  };
  scenarios: { conservative: FinanceScenario; expected: FinanceScenario; optimistic: FinanceScenario };
  risk_adjusted: FinanceScenario;
  thresholds: { min_profit_usd: number; min_roi_pct: number; max_capital_at_risk_usd: number; bid_increment: number };
  assumptions_used: { assumed_costs: Record<string, number>; listing_overrides: Record<string, number>; request_overrides: Record<string, number> };
  sensitivity: SensitivityCell[];
}

export interface FinanceOverrides {
  incoming_shipping?: number;
  outgoing_shipping?: number;
  sales_tax_pct?: number;
  cleaning_repair_cost?: number;
  packaging_cost?: number;
  min_profit_usd?: number;
  min_roi_pct?: number;
  max_capital_at_risk_usd?: number;
  platform?: string;
}

export interface FinanceQuery {
  bid?: number | null;
  platform?: string | null;
  resale_price?: number | null;
  overrides?: FinanceOverrides;
  sensitivity?: boolean;
}

/* ---------- status / settings / analytics ---------- */
export type ComponentState = "live" | "needs_config" | "demo" | "available" | "disabled" | string;

export interface StatusResponse {
  version: string;
  components: Record<string, { state: ComponentState; detail: string }>;
  providers: { provider: string; configured: boolean; triage_model: string; deep_model: string; note: string }[];
  sold_data_providers: SoldDataProvider[];
  counts: { demo_listings: number; live_listings: number };
  budget: { daily_budget_usd: number; per_listing_budget_usd: number };
}

export interface SoldDataProvider {
  name: string;
  sold_data: boolean;
  available: boolean;
  note: string;
}

export interface PlatformConfig {
  label: string;
  final_value_fee_pct: number;
  per_order_fee: number;
  payment_processing_pct: number;
  payment_processing_fixed: number;
  listing_fee: number;
  seller_pays_shipping: boolean;
  note: string;
}

export interface SettingsObject {
  platforms: Record<string, PlatformConfig>;
  default_platform: string;
  acquisition: {
    buyer_premium_pct: number;
    sales_tax_pct: number;
    default_incoming_shipping: number | null;
    default_handling_fee: number | null;
    bid_increment: number;
  };
  resale: {
    clothing_outgoing_shipping: number;
    jewelry_outgoing_shipping: number;
    packaging_cost: number;
    default_cleaning_cost: number;
    holding_cost_per_month: number;
  };
  thresholds: { min_profit_usd: number; min_roi_pct: number; max_capital_at_risk_usd: number };
  risk: {
    scenario_weights_by_evidence: Record<string, number[]>;
    identification_confidence_haircut: number;
    estimated_months_to_sell: Record<string, number>;
  };
  ranking: {
    weights: Record<string, number>;
    profit_reference_usd: number;
    roi_reference_pct: number;
    feedback_adjustments: Record<string, number>;
  };
  analysis: {
    auto_escalate_min_triage_interest: number;
    exclude_keywords: string[];
    boost_keywords: string[];
    min_current_bid: number;
    max_current_bid: number;
  };
  notifications: { reminder_minutes_before_end: number; enable_console_reminders: boolean };
  model_pricing_usd_per_1m: Record<string, number[]>;
}

export interface SettingsResponse {
  settings: SettingsObject;
  defaults: SettingsObject;
  env: {
    triage_provider: string;
    triage_model: string | null;
    deep_provider: string;
    deep_model: string | null;
    daily_budget_usd: number;
    per_listing_budget_usd: number;
    max_zoom_calls: number;
    enable_unofficial_sgw_api: boolean;
    imap_host: string | null;
    imap_user: string | null;
    buyer_zip: string | null;
  };
  credentials_configured: Record<string, boolean>;
  feedback_labels: string[];
}

export interface UsageRow {
  provider: string;
  model: string;
  stage: string;
  calls: number;
  tokens_in: number;
  tokens_out: number;
  est_cost_usd: number;
  avg_duration_ms: number;
  errors: number;
}

export interface AnalyticsSummary {
  items_total: number;
  items_demo: number;
  items_analyzed_deep: number;
  opportunities_by_tier: Partial<Record<Tier, number>>;
  by_domain: Record<string, Partial<Record<Tier, number>>>;
  opportunity_categories: Record<string, number>;
  avg_projected_roi_pct: number | null;
  avg_projected_profit_usd: number | null;
  identification_corrections: number;
  feedback_counts: Record<string, number>;
  purchases: number;
  sales: number;
  realized_profit_total: number;
  avg_days_to_sale: number | null;
  ai_usage: { days: number; spent_today_usd: number; daily_budget_usd: number; by_model: UsageRow[] };
  recent_runs: number;
}

export interface WatchlistResponse {
  items: ListingSummary[];
}

export interface DueReminder {
  listing_id: number;
  title: string;
  ends_at: string;
  minutes_left: number;
  user_max_bid: number | null;
  current_bid: number | null;
}

export interface Job {
  id: number;
  job_type: string;
  listing_id: number | null;
  payload: Record<string, unknown>;
  status: string;
  attempts: number;
  max_attempts: number;
  error: string | null;
  result: Record<string, unknown> | null;
  created_at: string | null;
  finished_at: string | null;
}

export interface ReferenceEntry {
  id: number;
  name: string;
  entry_type: string;
  domain: string;
  category: string | null;
  characteristics: string | null;
  identifiers: string[];
  keywords: string[];
  reference_image_urls: string[];
  price_evidence: Record<string, unknown>[];
  typical_low: number | null;
  typical_high: number | null;
  demand: string | null;
  liquidity: string | null;
  id_confidence_notes: string | null;
  source: string;
  is_demo: boolean;
  created_at: string | null;
}

export interface ReferenceIn {
  name: string;
  entry_type?: string;
  domain?: string;
  category?: string | null;
  characteristics?: string | null;
  identifiers?: string[];
  keywords?: string[];
  reference_image_urls?: string[];
  price_evidence?: Record<string, unknown>[];
  typical_low?: number | null;
  typical_high?: number | null;
  demand?: string;
  liquidity?: string;
  id_confidence_notes?: string | null;
  source?: string;
}

/* ---------- request bodies ---------- */
export interface ListingIn {
  source?: string;
  source_item_id?: string | null;
  source_url?: string | null;
  title: string;
  description?: string | null;
  category?: string | null;
  seller?: string | null;
  domain?: string | null;
  current_bid?: number | null;
  num_bids?: number | null;
  buy_now_price?: number | null;
  ends_at?: string | null;
  shipping_cost?: number | null;
  handling_fee?: number | null;
  other_costs?: Record<string, number>;
  measurements?: Record<string, unknown>;
  condition_text?: string | null;
  status?: string;
  image_urls?: string[];
}

export interface ListingPatch {
  title?: string | null;
  description?: string | null;
  category?: string | null;
  seller?: string | null;
  domain?: string | null;
  condition_text?: string | null;
  measurements?: Record<string, unknown> | null;
  other_costs?: Record<string, number> | null;
  assumptions?: Record<string, unknown> | null;
  user_notes?: string | null;
  archived?: boolean | null;
  status?: string | null;
  source_url?: string | null;
}

export interface SnapshotIn {
  current_bid?: number | null;
  num_bids?: number | null;
  ends_at?: string | null;
  shipping_cost?: number | null;
  handling_fee?: number | null;
  status?: string | null;
}

export interface AnalyzeIn {
  mode: "auto" | "prefilter" | "triage" | "deep";
  provider?: "auto" | "anthropic" | "gemini" | "demo" | null;
  model?: string | null;
  force?: boolean;
  background?: boolean;
}

export interface AnalyzeStageSummary {
  stage: string;
  run_id?: number;
  passed?: boolean;
  reasons?: string[];
  cached?: boolean;
  interest_score?: number;
  escalate?: boolean;
  headline?: string;
  confidence?: number;
  skipped?: string;
  [k: string]: unknown;
}

export type AnalyzeResponse =
  | { job_id: number; status: string }
  | { summary: { listing_id: number; stages: AnalyzeStageSummary[] }; listing: ListingDetail };

export interface CompIn {
  title: string;
  marketplace?: string;
  url?: string | null;
  sold_date?: string | null;
  price?: number | null;
  shipping_included?: boolean | null;
  shipping_amount?: number | null;
  is_sold?: boolean;
  accepted_offer?: boolean;
  comp_type?: string;
  similarity?: number;
  evidence_quality?: string;
  condition?: string | null;
  differences?: string | null;
  source?: string;
}

export interface CompPatch {
  comp_type?: string | null;
  similarity?: number | null;
  evidence_quality?: string | null;
  price?: number | null;
  is_sold?: boolean | null;
  differences?: string | null;
  condition?: string | null;
}

export interface IdentificationCorrection {
  summary: string;
  domain?: string | null;
  confidence?: number | null;
  brand_or_maker?: string | null;
  era?: string | null;
  notes?: string | null;
  demand_indicator?: string | null;
  liquidity_indicator?: string | null;
}

export interface ValuationOverride {
  expected: number;
  conservative?: number | null;
  optimistic?: number | null;
  note?: string;
}

export interface WatchIn {
  status?: WatchStatus | null;
  user_max_bid?: number | null;
  remind_minutes_before_end?: number | null;
  notes?: string | null;
  archived?: boolean | null;
}

export interface OutcomeIn {
  purchased?: boolean | null;
  purchase_price?: number | null;
  acquisition_expenses?: number | null;
  purchased_at?: string | null;
  sold?: boolean | null;
  resale_price?: number | null;
  selling_fees?: number | null;
  resale_platform?: string | null;
  sold_at?: string | null;
  notes?: string | null;
}

export interface ImportResult {
  created: number;
  updated: number;
  unchanged: number;
  ids: number[];
  errors: string[];
  parsed?: ListingIn | ListingIn[] | Record<string, unknown> | Record<string, unknown>[];
}

export interface DemoRunResponse {
  loaded: { listings: { id: number; key: string; created: boolean }[]; references_seeded: number };
  analysis: { id: number; key: string; stages: AnalyzeStageSummary[]; score: number | null; tier: Tier | null }[];
  [k: string]: unknown;
}
