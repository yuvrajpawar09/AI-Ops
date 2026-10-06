import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Polls `url` every `intervalMs` and exposes the latest { data, error,
 * loading }. Each panel in this dashboard owns exactly one of these, against
 * exactly one backend endpoint - see the Phase 5 write-up for why polling
 * instead of WebSockets/SSE. A failed fetch sets `error` and leaves the
 * previous `data` in place (so a single missed poll doesn't blank the UI);
 * the panel decides how to render an error state, this hook only detects it.
 */
export function usePolling(url, intervalMs, { enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const timerRef = useRef(null);
  const cancelledRef = useRef(false);

  const fetchOnce = useCallback(async () => {
    try {
      const res = await fetch(url, {
        credentials: "same-origin",
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) {
        const err = new Error(`HTTP ${res.status}`);
        err.status = res.status;
        throw err;
      }
      const json = await res.json();
      if (!cancelledRef.current) {
        setData(json);
        setError(null);
        setStatus(200);
        setLoading(false);
      }
    } catch (err) {
      if (!cancelledRef.current) {
        setError(err?.message || "unreachable");
        setStatus(err?.status ?? null);
        setLoading(false);
      }
    }
  }, [url]);

  useEffect(() => {
    if (!enabled) return undefined;
    cancelledRef.current = false;

    fetchOnce();
    timerRef.current = setInterval(fetchOnce, intervalMs);
    return () => {
      cancelledRef.current = true;
      clearInterval(timerRef.current);
    };
  }, [fetchOnce, intervalMs, enabled]);

  return { data, error, loading, status, refresh: fetchOnce };
}
