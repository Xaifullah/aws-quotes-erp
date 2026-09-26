import { apiClient } from "../../shared/apiClient";

export interface Quote {
  id: string;
  text: string;
  author: string;
  tags: string[];
  processed_at: string;
}

interface QuotesResponse {
  quotes: Quote[];
}

export async function fetchQuotes(token: string): Promise<Quote[]> {
  const response = await apiClient.request<QuotesResponse>("/quotes", { token });
  return response.quotes;
}
