"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bell, ShieldAlert, Activity } from "lucide-react";
import { apiJson, subscribeEvents } from "@/lib/api";

export default function NotificationsPage() {
  const [denied, setDenied] = useState<any[]>([]);
  const [recent, setRecent] = useState<any[]>([]);
  const [live, setLive] = useState<any[]>([]);

  useEffect(() => {
    apiJson("/api/notifications").then((d: any) => { setDenied(d.denied_access || []); setRecent(d.recent || []); }).catch(() => {});
    const off = subscribeEvents((ev) => {
      if (ev.type === "message" && ev.role === "user") setLive((p) => [{ text: ev.content, source: ev.source, ts: ev.ts }, ...p].slice(0, 20));
    });
    return off;
  }, []);
  const fmt = (ts: number) => new Date(ts * 1000).toLocaleString();

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 780, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>Notifications</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 20px" }}>Live activity and security alerts.</p>

        <Section icon={<Activity size={14} />} title={`Live incoming (${live.length})`}>
          {live.length === 0 ? <Muted t="Waiting for messages… send one from Telegram to see it appear here live." /> :
            live.map((l, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className="glass" style={row}>
                <span style={pill(l.source === "telegram" ? "var(--secondary)" : "var(--primary)")}>{l.source}</span>
                <span style={{ flex: 1, fontSize: 13 }}>{l.text}</span>
                <span style={{ fontSize: 11, color: "var(--text-faint)" }}>{fmt(l.ts)}</span>
              </motion.div>
            ))}
        </Section>

        {denied.length > 0 && (
          <Section icon={<ShieldAlert size={14} />} title={`Rejected access (${denied.length})`} danger>
            {denied.map((d, i) => (
              <div key={i} className="glass" style={{ ...row, borderColor: "rgba(251,113,133,.3)" }}>
                <span style={pill("var(--err)")}>denied</span>
                <span style={{ flex: 1, fontSize: 13 }}>user {d.user_id}: {d.request}</span>
                <span style={{ fontSize: 11, color: "var(--text-faint)" }}>{fmt(d.ts)}</span>
              </div>
            ))}
          </Section>
        )}

        <Section icon={<Bell size={14} />} title="Recent activity">
          {recent.slice(0, 15).map((r, i) => (
            <div key={i} className="glass" style={row}>
              <span style={pill("var(--primary)")}>{r.kind}</span>
              <span style={{ flex: 1, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.request}</span>
              <span style={{ fontSize: 11, color: "var(--text-faint)" }}>{fmt(r.ts)}</span>
            </div>
          ))}
        </Section>
      </div>
    </div>
  );
}
const row: any = { borderRadius: 11, padding: "10px 13px", display: "flex", alignItems: "center", gap: 12, marginBottom: 5 };
const pill = (c: string): any => ({ fontSize: 10.5, fontWeight: 600, textTransform: "uppercase", color: c, background: "var(--surface)",
  padding: "3px 9px", borderRadius: 99, border: "1px solid var(--border)", flexShrink: 0 });
function Section({ icon, title, children, danger }: any) {
  return (<div style={{ marginBottom: 24 }}>
    <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em",
      color: danger ? "var(--err)" : "var(--text-muted)", fontWeight: 600, marginBottom: 10 }}>
      <span style={{ color: danger ? "var(--err)" : "var(--primary-soft)" }}>{icon}</span>{title}</div>
    {children}</div>);
}
const Muted = ({ t }: any) => <div style={{ fontSize: 13, color: "var(--text-faint)", padding: "6px 2px" }}>{t}</div>;
