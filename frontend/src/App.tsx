import { useState } from "react";
import { useAuth } from "./features/auth/useAuth";
import { LoginForm } from "./features/auth/LoginForm";
import { RegisterForm } from "./features/auth/RegisterForm";
import { QuotesDashboard } from "./features/quotes/QuotesDashboard";
import { AuthLayout } from "./shared/ui/AuthLayout";

type View = "login" | "register";

function App() {
  const { token, error, login, register, logout } = useAuth();
  const [view, setView] = useState<View>("login");

  if (token) {
    return <QuotesDashboard token={token} onLogout={logout} />;
  }

  return (
    <AuthLayout mode={view} onModeChange={setView}>
      {view === "login" ? (
        <LoginForm onLogin={login} error={error} />
      ) : (
        <RegisterForm onRegister={register} error={error} />
      )}
    </AuthLayout>
  );
}

export default App;
