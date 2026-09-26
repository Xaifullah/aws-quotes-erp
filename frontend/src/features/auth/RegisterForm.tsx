import { useState } from "react";
import type { FormEvent } from "react";
import "./AuthForm.css";

interface RegisterFormProps {
  onRegister: (username: string, password: string) => Promise<void>;
  error: string | null;
}

export function RegisterForm({ onRegister, error }: RegisterFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setSuccess(false);
    try {
      await onRegister(username, password);
      setSuccess(true);
      setUsername("");
      setPassword("");
    } catch {
      // error is surfaced via the `error` prop
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h2 className="auth-form-heading">Create an account</h2>
      <p className="auth-form-subheading">Takes a few seconds — no email needed.</p>
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="auth-field">
          <label htmlFor="register-username">Username</label>
          <input
            id="register-username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="auth-field">
          <label htmlFor="register-password">Password</label>
          <input
            id="register-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        {error && <p className="auth-message is-error">{error}</p>}
        {success && <p className="auth-message is-success">Registered — you can log in now.</p>}
        <button type="submit" className="auth-submit" disabled={submitting}>
          {submitting ? "Registering…" : "Register"}
        </button>
      </form>
    </div>
  );
}
