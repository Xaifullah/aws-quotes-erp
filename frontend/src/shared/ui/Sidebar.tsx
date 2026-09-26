import "./Sidebar.css";

export interface SidebarNavItem {
  id: string;
  label: string;
  active: boolean;
  onClick: () => void;
}

interface SidebarProps {
  navItems: SidebarNavItem[];
  username: string;
  onLogout: () => void;
}

export function Sidebar({ navItems, username, onLogout }: SidebarProps) {
  const initial = username.charAt(0).toUpperCase();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-mark">Q</span>
        <span className="sidebar-wordmark">Quotes</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`sidebar-nav-item${item.active ? " is-active" : ""}`}
            onClick={item.onClick}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-user">
        <span className="sidebar-avatar">{initial}</span>
        <span className="sidebar-username">{username}</span>
        <button type="button" className="sidebar-logout" onClick={onLogout} title="Log out">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M6 2H3.5A1.5 1.5 0 0 0 2 3.5v9A1.5 1.5 0 0 0 3.5 14H6M10.5 11l3-3-3-3M13 8H6"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </aside>
  );
}
