"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, Clock, Repeat, Trash2, Plus } from "lucide-react";
import { apiJson } from "@/lib/api";

export default function AutomationPage() {
  const [items, setItems] = useState<any[]>([]);
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"once" | "daily">("once");
  const [when, setWhen] = useState("");
  const [daily, setDaily] = useState("09:00");
  const [err, setErr] = useState("");

  const load = () => apiJson("/api/reminders").then((d: any) => setItems(d.reminders || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add() {
    setErr("");
    const body: any = { text: text.trim() };
    if (!body.text) return;
    if (mode === "daily") body.daily_time = daily;
    else { if (!when) { setErr("Pick a date & time"); return; } body.when = when; }
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/api/reminders`, {
        method: "POST", headers: { "content-type": "application/json", Authorization: `Bearer ${localStorage.getItem("jarvis_access")}` },
        body: JSON.stringify(body),
      });
      if (!r.ok) { const d = await r.json().catch(() => ({})); setErr(d.detail || "Failed"); return; }
      setText(""); setWhen(""); load();
    } catch { setErr("Failed"); }
  }
  async function del(id: number) {
    await apiJson(`/api/reminders/${id}`, { method: "DELETE" }).catch(() => {});
    setItems((x) => x.filter((r) => r.id !== id));
  }

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 760, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>Automation Center</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 20px" }}>Reminders fire on Telegram at the scheduled time — same scheduler, zero AI cost.</p>

        <div className="glass" style={{ borderRadius: 16, padding: 16, marginBottom: 24 }}>
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Remind me to…"
            style={{ width: "100%", background: "rgba(255,255,255,.04)", border: "1px solid var(--border)", borderRadius: 10,
              padding: "10px 13px", color: "var(--text)", fontSize: 14, outline: "none", marginBottom: 12 }} />
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <button className={`seg${mode === "once" ? " on" : ""}`} onClick={() => setMode("once")}><Clock size={14} /> One-time</button>
            <button className={`seg${mode === "daily" ? " on" : ""}`} onClick={() => setMode("daily")}><Repeat size={14} /> Daily</button>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {mode === "once" ? (
              <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className="dtInput" />
            ) : (
              <input type="time" value={daily} onChange={(e) => setDaily(e.target.value)} className="dtInput" />
            )}
            <button className="addBtn" onClick={add}><Plus size={16} /> Add reminder</button>
          </div>
          {err && <div style={{ color: "var(--err)", fontSize: 12.5, marginTop: 10 }}>{err}</div>}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <AnimatePresence>
            {items.map((r) => (
              <motion.div key={r.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, height: 0 }}
                className="glass" style={{ borderRadius: 12, padding: "13px 15px", display: "flex", alignItems: "center", gap: 13 }}>
                <div style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center",
                  background: "rgba(124,58,237,.16)", color: "var(--primary-soft)", flexShrink: 0 }}>
                  {r.recurrence === "daily" ? <Repeat size={16} /> : <Bell size={16} />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>{r.text}</div>
                  <div style={{ fontSize: 12, color: "var(--text-faint)", fontFamily: "'JetBrains Mono',monospace" }}>
                    {r.recurrence === "daily" ? `Daily at ${r.daily_time}` : r.when}
                  </div>
                </div>
                <button className="tinyBtn" onClick={() => del(r.id)}><Trash2 size={15} /></button>
              </motion.div>
            ))}
          </AnimatePresence>
          {items.length === 0 && <div style={{ fontSize: 13, color: "var(--text-faint)", padding: "8px 2px" }}>No active reminders.</div>}
        </div>
      </div>
      <style jsx global>{`
        .seg { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 10px; font-size: 13px;
          background: var(--surface); border: 1px solid var(--border); color: var(--text-muted); cursor: pointer; }
        .seg.on { background: linear-gradient(135deg,rgba(124,58,237,.3),rgba(99,102,241,.2)); color: #fff; border-color: rgba(124,58,237,.5); }
        .dtInput { background: rgba(255,255,255,.04); border: 1px solid var(--border); border-radius: 10px; padding: 9px 12px;
          color: var(--text); font-size: 13.5px; outline: none; color-scheme: dark; }
        .addBtn { display: inline-flex; align-items: center; gap: 6px; padding: 9px 16px; border-radius: 10px; border: none; cursor: pointer;
          font-size: 13.5px; font-weight: 500; color: #fff; background: linear-gradient(135deg,#7c3aed,#6366f1); margin-left: auto; }
        .tinyBtn { background: none; border: none; color: var(--text-faint); cursor: pointer; padding: 5px; border-radius: 8px; }
        .tinyBtn:hover { color: var(--err); background: var(--surface-hover); }
      `}</style>
    </div>
  );
}
