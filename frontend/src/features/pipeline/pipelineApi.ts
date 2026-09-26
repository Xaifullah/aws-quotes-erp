import { apiClient } from "../../shared/apiClient";

export interface PipelineStatus {
  raw_count: number;
  processed_count: number;
  last_scraped_at: string | null;
  last_processed_at: string | null;
}

export async function fetchPipelineStatus(token: string): Promise<PipelineStatus> {
  return apiClient.request<PipelineStatus>("/status", { token });
}
