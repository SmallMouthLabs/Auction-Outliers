"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export interface UseApiOptions {
  /** Poll interval in ms (0 = none). Polling pauses when the tab is hidden. */
  pollMs?: number;
  enabled?: boolean;
}

export interface UseApiResult<T> {
  data: T | undefined;
  error: ApiError | null;
  loading: boolean;
  refreshing: boolean;
  refresh: () => Promise<T | undefined>;
  setData: (updater: T | ((prev: T | undefined) => T | undefined)) => void;
}

/**
 * Minimal SWR-like hook: fetches on mount and whenever `deps` change,
 * optional polling, manual refresh, and local mutation via setData.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = [], opts: UseApiOptions = {}): UseApiResult<T> {
  const { pollMs = 0, enabled = true } = opts;
  const [data, setDataState] = useState<T | undefined>(undefined);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [refreshing, setRefreshing] = useState(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const seq = useRef(0);
  const hasData = useRef(false);

  const run = useCallback(async () => {
    const id = ++seq.current;
    if (hasData.current) setRefreshing(true); else setLoading(true);
    try {
      const d = await fetcherRef.current();
      if (id !== seq.current) return undefined;
      hasData.current = true;
      setDataState(d);
      setError(null);
      return d;
    } catch (e) {
      if (id !== seq.current) return undefined;
      setError(e instanceof ApiError ? e : new ApiError(0, (e as Error).message));
      return undefined;
    } finally {
      if (id === seq.current) { setLoading(false); setRefreshing(false); }
    }
  }, []);

  useEffect(() => {
    if (!enabled) { setLoading(false); return; }
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, run, ...deps]);

  useEffect(() => {
    if (!enabled || !pollMs) return;
    const t = setInterval(() => { if (document.visibilityState === "visible") void run(); }, pollMs);
    return () => clearInterval(t);
  }, [enabled, pollMs, run]);

  const setData = useCallback((updater: T | ((prev: T | undefined) => T | undefined)) => {
    setDataState((prev) => (typeof updater === "function" ? (updater as (p: T | undefined) => T | undefined)(prev) : updater));
  }, []);

  return { data, error, loading, refreshing, refresh: run, setData };
}

/** Ticks every `ms` so countdowns re-render. */
export function useNow(ms = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return now;
}
