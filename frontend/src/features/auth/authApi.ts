import { apiClient } from "../../shared/apiClient";

interface AuthResponse {
  token: string;
}

export async function register(username: string, password: string): Promise<void> {
  await apiClient.request("/register", { method: "POST", body: { username, password } });
}

export async function login(username: string, password: string): Promise<string> {
  const response = await apiClient.request<AuthResponse>("/login", {
    method: "POST",
    body: { username, password },
  });
  return response.token;
}
