import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { MessageCircle, Image, Megaphone, BarChart3, ShieldCheck, LogOut, Menu, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import TenantSwitcher from "./TenantSwitcher";

const NAV_ITEMS = [
  { to: "/conversations", label: "Conversations", icon: MessageCircle },
  { to: "/media", label: "Media Library", icon: Image },
  { to: "/broadcasts", label: "Broadcasts", icon: Megaphone },
  { to: "/metrics", label: "Metrics", icon: BarChart3 },
  { to: "/audit-logs", label: "Audit Logs", icon: ShieldCheck },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const nav = (
    <nav className="flex flex-1 flex-col gap-0.5 px-3">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={() => setMobileNavOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
              isActive ? "bg-signal-500 text-ink-950" : "text-ink-300 hover:bg-ink-800 hover:text-ink-50"
            }`
          }
        >
          <Icon size={16} />
          {label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="flex h-screen bg-ink-50">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 flex-col bg-ink-950 py-5 md:flex">
        <div className="mb-6 flex items-center gap-2.5 px-4 text-ink-50">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal-500">
            <MessageCircle size={16} className="text-ink-950" strokeWidth={2.5} />
          </div>
          <span className="font-display text-sm font-semibold">AI Platform</span>
        </div>
        {nav}
        <div className="mt-auto space-y-3 px-4 pt-4">
          <div className="text-xs text-ink-500">
            <p className="font-medium text-ink-300">{user?.full_name}</p>
            <p className="capitalize">{user?.role}</p>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-sm text-ink-400 hover:text-ink-100"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      {/* Mobile nav drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-30 flex md:hidden">
          <div className="w-60 flex-col bg-ink-950 py-5 flex">
            <div className="mb-6 flex items-center justify-between px-4 text-ink-50">
              <span className="font-display text-sm font-semibold">AI Platform</span>
              <button onClick={() => setMobileNavOpen(false)}>
                <X size={18} className="text-ink-400" />
              </button>
            </div>
            {nav}
          </div>
          <div className="flex-1 bg-black/40" onClick={() => setMobileNavOpen(false)} />
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-ink-200 bg-white px-4 py-3 md:px-6">
          <button className="md:hidden" onClick={() => setMobileNavOpen(true)}>
            <Menu size={20} className="text-ink-600" />
          </button>
          <TenantSwitcher />
          <div className="hidden text-sm text-ink-500 md:block">{user?.email}</div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
