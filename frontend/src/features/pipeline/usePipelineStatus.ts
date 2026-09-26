import { useCallback, useEffect, useState } from "react";
import { fetchPipelineStatus } from "./pipelineApi";
import type { PipelineStatus } from "./pipelineApi";

export function usePipelineStatus(token: string | null) {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setStatus(await fetchPipelineStatus(token));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pipeline status");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  return { status, error, reload: load };
}
