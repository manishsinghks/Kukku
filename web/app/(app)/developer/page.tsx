"use client";
import { useEffect, useState } from "react";
import { Terminal, Activity, ScrollText } from "lucide-react";
import { apiJson } from "@/lib/api";

export default function DeveloperPage() {
  const [tab, setTab] = useState<"activity" | "logs">("activity");
  const [activity, setActivity] = useState<any[]>([]);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    apiJson("/api/activity?limit=80").then((d: any) => setActivity(d.requests || [])).catch(() => {});
    const load = () => apiJson("/api/logs/tail?lines=200").then((d: any) => setLogs(d.lines || [])).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const tag = (k: string) => k === "denied" ? "var(--err)" : k === "voice" ? "var(--warn)" : "var(--primary-soft)";
  const fmt = (ts: number) => new Date(ts * 1000).toLocaleTimeString();

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header style={{ padding: "16px 28px", borderBottom: "1px solid var(--border)" }}>
        <h1 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 2px" }}>Developer Panel</h1>
        <p style={{ fontSize: 12.5, color: "var(--text-muted)", margin: 0 }}>Live activity & logs from the running backend.</p>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className={`seg${tab === "activity" ? " on" : ""}`} onClick={() => setTab("activity")}><Activity size={14} /> Activity</button>
          <button className={`seg${tab === "logs" ? " on" : ""}`} onClick={() => setTab("logs")}><ScrollText size={14} /> Logs</button>
        </div>
      </header>
      <div style={{ flex: 1, overflowY: "auto", padding: "18px 28px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          {tab === "activity" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              {activity.map((r, i) => (
                <div key={i} className="glass" style={{ borderRadius: 10, padding: "10px 13px", display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: tag(r.kind), width: 54, textTransform: "uppercase" }}>{r.kind}</span>
                  <span style={{ flex: 1, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.request}</span>
                  {r.duration_ms ? <span style={{ fontSize: 11, color: "var(--text-faint)", fontFamily: "'JetBrains Mono',monospace" }}>{r.duration_ms}ms</span> : null}
                  <span style={{ fontSize: 11, color: "var(--text-faint)" }}>{fmt(r.ts)}</span>
                </div>
              ))}
              {activity.length === 0 && <Empty />}
            </div>
          ) : (
            <pre style={{ background: "#0b0b12", border: "1px solid var(--border)", borderRadius: 12, padding: 16,
              fontSize: 11.5, fontFamily: "'JetBrains Mono',monospace", color: "var(--text-muted)", lineHeight: 1.55,
              overflowX: "auto", whiteSpace: "pre-wrap", margin: 0 }}>
              {logs.length ? logs.join("\n") : "no logs"}
            </pre>
          )}
        </div>
      </div>
      <style jsx global>{`
        .seg { display: inline-flex; align-items: center; gap: 6px; padding: 7px 13px; border-radius: 9px; font-size: 12.5px;
          background: var(--surface); border: 1px solid var(--border); color: var(--text-muted); cursor: pointer; }
        .seg.on { background: linear-gradient(135deg,rgba(124,58,237,.3),rgba(99,102,241,.2)); color: #fff; border-color: rgba(124,58,237,.5); }
      `}</style>
    </div>
  );
}
const Empty = () => <div style={{ fontSize: 13, color: "var(--text-faint)", padding: "8px 2px" }}>No activity yet.</div>;
