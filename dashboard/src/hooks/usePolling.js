import { useEffect, useRef, useState } from "react";

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
  const timerRef = useRef(null);

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || "unreachable");
          setLoading(false);
        }
      }
    }

    poll();
    timerRef.current = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(timerRef.current);
    };
  }, [url, intervalMs, enabled]);

  return { data, error, loading };
}
