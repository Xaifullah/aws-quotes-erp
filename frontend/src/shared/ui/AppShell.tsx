import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import type { SidebarNavItem } from "./Sidebar";
import "./AppShell.css";

interface AppShellProps {
  navItems: SidebarNavItem[];
  username: string;
  onLogout: () => void;
  children: ReactNode;
}

export function AppShell({ navItems, username, onLogout, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar navItems={navItems} username={username} onLogout={onLogout} />
      <div className="app-shell-main">{children}</div>
    </div>
  );
}
