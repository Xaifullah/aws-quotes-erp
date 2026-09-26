import type { ReactNode } from "react";
import "./AuthLayout.css";

interface AuthLayoutProps {
  mode: "login" | "register";
  onModeChange: (mode: "login" | "register") => void;
  children: ReactNode;
}

export function AuthLayout({ mode, onModeChange, children }: AuthLayoutProps) {
  return (
    <div className="auth-layout">
      <div className="auth-panel">
        <div className="auth-panel-brand">
          <span className="auth-panel-mark">Q</span>
          <span className="auth-panel-wordmark">Quotes</span>
        </div>
        <p className="auth-panel-tagline">
          A living archive of literature&rsquo;s sharpest lines &mdash; scraped, cleaned, and
          served fresh every hour.
        </p>
        <div className="auth-panel-pipeline">
          <span>EC2 scraper</span>
          <span aria-hidden="true">&rarr;</span>
          <span>Lambda cleanup</span>
          <span aria-hidden="true">&rarr;</span>
          <span>Your dashboard</span>
        </div>
      </div>

      <div className="auth-form-side">
        <div className="auth-card">
          <div className="auth-toggle" role="tablist" aria-label="Auth mode">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "is-active" : ""}
              onClick={() => onModeChange("login")}
            >
              Log in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={mode === "register" ? "is-active" : ""}
              onClick={() => onModeChange("register")}
            >
              Register
            </button>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
