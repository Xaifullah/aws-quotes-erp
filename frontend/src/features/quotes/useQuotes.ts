import { useCallback, useEffect, useState } from "react";
import { fetchQuotes } from "./quotesApi";
import type { Quote } from "./quotesApi";

export function useQuotes(token: string | null) {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setQuotes(await fetchQuotes(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quotes");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  return { quotes, loading, error, reload: load };
}
