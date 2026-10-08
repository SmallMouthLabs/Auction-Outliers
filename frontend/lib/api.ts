import type {
  AnalyticsSummary, AnalyzeIn, AnalyzeResponse, ApiErrorBody, CompIn, CompPatch, Comparable, DemoRunResponse,
  DueReminder, FinanceQuery, FinanceResponse, IdentificationCorrection, ImageOut, ImportResult, Job, ListingDetail,
  ListingIn, ListingPatch, ListingsResponse, OutcomeIn, ReferenceEntry, ReferenceIn, SettingsObject, SettingsResponse,
  SnapshotIn, SoldDataProvider, StatusResponse, ValuationOverride, WatchIn, WatchlistResponse, ListingSummary,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").replace(/\/$/, "");

/** Resolve a relative image path such as "/api/images/1" to an absolute backend URL. */
export function imageUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  body?: ApiErrorBody;
  constructor(status: number, message: string, code?: string, body?: ApiErrorBody) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.body = body;
  }
  get isProviderNotConfigured() {
    return this.status === 424 || this.code === "provider_not_configured";
  }
}

function formatDetail(body: ApiErrorBody | undefined, status: number): string {
  if (!body) return `Request failed (${status})`;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((e) => `${e.loc.filter((x) => x !== "body").join(".")}: ${e.msg}`).join("; ");
  }
  return `Request failed (${status})`;
}

type Query = Record<string, string | number | boolean | null | undefined>;

function qs(q?: Query): string {
  if (!q) return "";
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === null || v === "") continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export async function request<T>(path: string, init: RequestInit & { query?: Query } = {}): Promise<T> {
  const { query, ...rest } = init;
  const headers = new Headers(rest.headers || {});
  if (rest.body && !(rest.body instanceof FormData) && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}${qs(query)}`, { ...rest, headers, cache: "no-store" });
  } catch (e) {
    throw new ApiError(0, `No response from backend for ${path} (${(e as Error).message}). Either the backend at ${API_BASE} is not running, or it crashed with an unhandled 500 (no CORS headers) - check the backend log.`, "network");
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: unknown = undefined;
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (!res.ok) {
    const body = (typeof data === "object" && data) ? (data as ApiErrorBody) : undefined;
    throw new ApiError(res.status, formatDetail(body, res.status), body?.code, body);
  }
  return data as T;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

/* ---------------- typed helpers ---------------- */
export const api = {
  // system
  status: () => request<StatusResponse>("/api/status"),
  health: () => request<{ ok: boolean; version: string }>("/api/health"),
  analytics: () => request<AnalyticsSummary>("/api/analytics/summary"),
  settings: () => request<SettingsResponse>("/api/settings"),
  /** NOTE: PUT and reset return only { settings } (not the full GET shape). */
  putSettings: (patch: Partial<SettingsObject>) => request<{ settings: SettingsObject }>("/api/settings", { method: "PUT", ...json(patch) }),
  resetSettings: () => request<{ settings: SettingsObject }>("/api/settings/reset", { method: "POST" }),
  soldDataProviders: () => request<{ providers: SoldDataProvider[] }>("/api/providers/sold-data"),

  // demo
  demoRun: () => request<DemoRunResponse>("/api/demo/run", { method: "POST" }),
  demoLoad: () => request<Record<string, unknown>>("/api/demo/load", { method: "POST" }),
  demoClear: () => request<{ removed: unknown }>("/api/demo", { method: "DELETE" }),

  // listings
  listings: (q: Query) => request<ListingsResponse>("/api/listings", { query: q }),
  listing: (id: number | string) => request<ListingDetail>(`/api/listings/${id}`),
  createListing: (body: ListingIn, opts: { fetch_images?: boolean; analyze?: boolean } = {}) =>
    request<{ listing: ListingDetail; created: boolean; changed: boolean }>("/api/listings", { method: "POST", ...json(body), query: opts }),
  patchListing: (id: number, body: ListingPatch) => request<ListingDetail>(`/api/listings/${id}`, { method: "PATCH", ...json(body) }),
  deleteListing: (id: number) => request<{ ok: boolean }>(`/api/listings/${id}`, { method: "DELETE" }),
  snapshot: (id: number, body: SnapshotIn) => request<ListingDetail>(`/api/listings/${id}/snapshot`, { method: "POST", ...json(body) }),
  uploadImages: (id: number, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return request<{ images: ImageOut[] }>(`/api/listings/${id}/images`, { method: "POST", body: fd });
  },
  addImageUrls: (id: number, urls: string[]) => request<{ images: ImageOut[] }>(`/api/listings/${id}/image-urls`, { method: "POST", ...json({ urls }) }),
  deleteImage: (id: number, imageId: number) => request<{ ok: boolean }>(`/api/listings/${id}/images/${imageId}`, { method: "DELETE" }),

  // imports
  importCsv: (file: File, opts: { fetch_images?: boolean; analyze?: boolean } = {}) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<ImportResult>("/api/listings/import/csv", { method: "POST", body: fd, query: opts });
  },
  importEmail: (input: { file?: File; html?: string }, opts: { fetch_images?: boolean; analyze?: boolean } = {}) => {
    const fd = new FormData();
    if (input.file) fd.append("file", input.file);
    if (input.html) fd.append("html", input.html);
    return request<ImportResult>("/api/listings/import/email", { method: "POST", body: fd, query: opts });
  },
  importPage: (input: { file?: File; html?: string; url?: string }, opts: { fetch_images?: boolean; analyze?: boolean } = {}) => {
    const fd = new FormData();
    if (input.file) fd.append("file", input.file);
    if (input.html) fd.append("html", input.html);
    if (input.url) fd.append("url", input.url);
    return request<ImportResult>("/api/listings/import/page", { method: "POST", body: fd, query: opts });
  },

  // analysis
  analyze: (id: number, body: AnalyzeIn) => request<AnalyzeResponse>(`/api/listings/${id}/analyze`, { method: "POST", ...json(body) }),
  correctIdentification: (id: number, body: IdentificationCorrection) =>
    request<ListingDetail>(`/api/listings/${id}/identification`, { method: "POST", ...json(body) }),
  revertIdentification: (id: number) => request<ListingDetail>(`/api/listings/${id}/identification/user`, { method: "DELETE" }),

  // comps + valuation
  addComp: (id: number, body: CompIn) => request<Comparable | ListingDetail>(`/api/listings/${id}/comps`, { method: "POST", ...json(body) }),
  importComps: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<unknown>(`/api/listings/${id}/comps/import`, { method: "POST", body: fd });
  },
  patchComp: (id: number, compId: number, body: CompPatch) => request<unknown>(`/api/listings/${id}/comps/${compId}`, { method: "PATCH", ...json(body) }),
  deleteComp: (id: number, compId: number) => request<unknown>(`/api/listings/${id}/comps/${compId}`, { method: "DELETE" }),
  searchComps: (id: number, body: { query: string; provider: string; save: boolean; limit?: number }) =>
    request<{ results: CompIn[]; saved: boolean; note: string }>(`/api/listings/${id}/comps/search`, { method: "POST", ...json(body) }),
  overrideValuation: (id: number, body: ValuationOverride) => request<ListingDetail>(`/api/listings/${id}/valuation/override`, { method: "POST", ...json(body) }),
  recalcValuation: (id: number) => request<ListingDetail>(`/api/listings/${id}/valuation/recalculate`, { method: "POST" }),

  // finance
  finance: (id: number, body: FinanceQuery) => request<FinanceResponse>(`/api/listings/${id}/finance`, { method: "POST", ...json(body) }),

  // feedback / notes / outcome
  addFeedback: (id: number, label: string, note?: string) => request<ListingDetail>(`/api/listings/${id}/feedback`, { method: "POST", ...json({ label, note: note || null }) }),
  deleteFeedback: (id: number, fbId: number) => request<ListingDetail>(`/api/listings/${id}/feedback/${fbId}`, { method: "DELETE" }),
  addNote: (id: number, text: string, flagged = false) => request<ListingDetail>(`/api/listings/${id}/notes`, { method: "POST", ...json({ text, flagged }) }),
  patchNote: (id: number, noteId: number, body: { text?: string; flagged?: boolean; resolved?: boolean }) =>
    request<ListingDetail>(`/api/listings/${id}/notes/${noteId}`, { method: "PATCH", ...json(body) }),
  putOutcome: (id: number, body: OutcomeIn) => request<ListingDetail>(`/api/listings/${id}/outcome`, { method: "PUT", ...json(body) }),

  // watchlist
  watchlist: (include_archived = false) => request<WatchlistResponse>("/api/watchlist", { query: { include_archived } }),
  putWatch: (id: number, body: WatchIn) => request<ListingSummary>(`/api/watchlist/${id}`, { method: "PUT", ...json(body) }),
  removeWatch: (id: number) => request<{ ok: boolean }>(`/api/watchlist/${id}`, { method: "DELETE" }),
  dueReminders: () => request<{ due: DueReminder[] }>("/api/watchlist/reminders/due"),

  // jobs
  jobs: (status?: string) => request<{ items: Job[] }>("/api/jobs", { query: { status, limit: 100 } }),
  retryJob: (id: number) => request<{ id: number; status: string }>(`/api/jobs/${id}/retry`, { method: "POST" }),
  processJobs: () => request<{ processed: unknown }>("/api/jobs/process", { method: "POST" }),

  // reference
  references: (q?: string, domain?: string) => request<{ items: ReferenceEntry[] }>("/api/reference", { query: { q, domain } }),
  createReference: (body: ReferenceIn) => request<ReferenceEntry>("/api/reference", { method: "POST", ...json(body) }),
  updateReference: (id: number, body: ReferenceIn) => request<ReferenceEntry>(`/api/reference/${id}`, { method: "PUT", ...json(body) }),
  deleteReference: (id: number) => request<{ ok: boolean }>(`/api/reference/${id}`, { method: "DELETE" }),
  seedReferences: () => request<unknown>("/api/reference/seed", { method: "POST" }),
  listingReferences: (id: number) => request<{ matches: unknown[] }>(`/api/listings/${id}/references`),
};

export function ebaySoldSearchUrl(query: string): string {
  return `https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(query)}&LH_Sold=1&LH_Complete=1`;
}
