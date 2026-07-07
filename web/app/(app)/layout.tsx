"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  MessageSquare, Search, Brain, FolderOpen, ScanText, Workflow,
  Terminal, Activity, Settings, Bell, Sparkles, LogOut,
} from "lucide-react";
import { AuthProvider, useAuth } from "@/lib/auth";

const NAV = [
  { group: "Assistant", items: [
    { href: "/chat", label: "AI Chat", icon: MessageSquare },
    { href: "/search", label: "Universal Search", icon: Search },
    { href: "/memory", label: "Memory", icon: Brain },
  ]},
  { group: "Workspace", items: [
    { href: "/files", label: "File Explorer", icon: FolderOpen },
    { href: "/ocr", label: "OCR Search", icon: ScanText },
    { href: "/automation", label: "Automation", icon: Workflow },
    { href: "/developer", label: "Developer", icon: Terminal },
  ]},
  { group: "System", items: [
    { href: "/monitor", label: "System Monitor", icon: Activity },
    { href: "/notifications", label: "Notifications", icon: Bell },
    { href: "/settings", label: "Settings", icon: Settings },
  ]},
];

function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  return (
    <aside className="glass" style={{ width: 244, display: "flex", flexDirection: "column",
      borderRadius: 0, borderTop: "none", borderBottom: "none", borderLeft: "none", padding: "18px 12px", flexShrink: 0 }}>
      <Link href="/chat" style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 8px 18px", textDecoration: "none", color: "inherit" }}>
        <div style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center",
          background: "linear-gradient(135deg,#7c3aed,#6366f1 55%,#ec4899)", boxShadow: "0 0 16px rgba(124,58,237,.4)" }}>
          <Sparkles size={18} color="#fff" />
        </div>
        <div style={{ fontSize: 15.5, fontWeight: 600, letterSpacing: "-0.02em" }}>Kukku OS</div>
      </Link>

      <nav style={{ flex: 1, overflowY: "auto" }}>
        {NAV.map((sec) => (
          <div key={sec.group} style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.09em",
              color: "var(--text-faint)", padding: "0 10px 6px", fontWeight: 600 }}>{sec.group}</div>
            {sec.items.map((it) => {
              const active = pathname === it.href;
              const Icon = it.icon;
              return (
                <Link key={it.href} href={it.href} className={`navItem${active ? " active" : ""}`}>
                  <Icon size={17} strokeWidth={active ? 2.2 : 1.8} />
                  <span>{it.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12, display: "flex", alignItems: "center", gap: 10, padding: "12px 8px 0" }}>
        <div style={{ width: 30, height: 30, borderRadius: 9, display: "grid", placeItems: "center",
          background: "rgba(124,58,237,.2)", color: "var(--primary-soft)", fontSize: 13, fontWeight: 600 }}>
          {(user || "J")[0].toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{user || "…"}</div>
          <div style={{ fontSize: 11, color: "var(--text-faint)" }}>Owner</div>
        </div>
        <button onClick={logout} title="Log out" className="iconBtn"><LogOut size={16} /></button>
      </div>

      <style jsx global>{`
        .navItem { display: flex; align-items: center; gap: 11px; padding: 9px 10px; border-radius: 10px;
          color: var(--text-muted); font-size: 13.5px; font-weight: 500; text-decoration: none;
          transition: background .16s, color .16s; margin-bottom: 1px; }
        .navItem:hover { background: var(--surface-hover); color: var(--text); }
        .navItem.active { background: linear-gradient(135deg, rgba(124,58,237,.28), rgba(99,102,241,.18));
          color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,.06); }
        .iconBtn { background: none; border: none; color: var(--text-faint); cursor: pointer; padding: 6px;
          border-radius: 8px; display: grid; place-items: center; transition: color .16s, background .16s; }
        .iconBtn:hover { color: var(--err); background: var(--surface-hover); }
      `}</style>
    </aside>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const { loading, user } = useAuth();
  if (loading)
    return (
      <div className="ambient" style={{ minHeight: "100dvh", display: "grid", placeItems: "center" }}>
        <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.4, repeat: Infinity }}
          style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading Kukku…</motion.div>
      </div>
    );
  if (!user) return null; // AuthProvider redirects to /login
  return (
    <div className="ambient" style={{ display: "flex", height: "100dvh", overflow: "hidden" }}>
      <Sidebar />
      <main style={{ flex: 1, position: "relative", zIndex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {children}
      </main>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <Shell>{children}</Shell>
    </AuthProvider>
  );
}
