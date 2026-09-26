import { useCallback, useState } from "react";
import { login as loginRequest, register as registerRequest } from "./authApi";

const TOKEN_STORAGE_KEY = "quotes-app-token";

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function useAuth() {
  const [token, setToken] = useState<string | null>(readStoredToken);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    setError(null);
    try {
      const newToken = await loginRequest(username, password);
      setToken(newToken);
      try {
        localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
      } catch {
        // ignore storage failures (private browsing, quota, etc.)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    setError(null);
    try {
      await registerRequest(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  return { token, error, login, register, logout };
}
