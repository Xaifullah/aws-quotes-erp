const BASE_URL = import.meta.env.VITE_API_URL as string;

export type HttpMethod = "GET" | "POST";

export interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  token?: string;
}

export interface ApiClient {
  request<T>(path: string, options?: RequestOptions): Promise<T>;
}

export class FetchApiClient implements ApiClient {
  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, token } = options;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.error || `Request failed with status ${response.status}`);
    }

    return response.json() as Promise<T>;
  }
}

export const apiClient: ApiClient = new FetchApiClient();
