"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Cpu, MemoryStick, HardDrive, FileStack, Sparkles, Activity, Zap } from "lucide-react";
import { apiJson } from "@/lib/api";

function Ring({ pct, label }: { pct: number; label: string }) {
  const r = 30, c = 2 * Math.PI * r, hot = pct > 85;
  return (
    <div style={{ position: "relative", width: 76, height: 76 }}>
      <svg width="76" height="76" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="38" cy="38" r={r} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="6" />
        <motion.circle cx="38" cy="38" r={r} fill="none" stroke={hot ? "url(#hot)" : "url(#cool)"} strokeWidth="6"
          strokeLinecap="round" strokeDasharray={c} initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - Math.min(pct, 100) / 100) }} transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }} />
        <defs>
          <linearGradient id="cool" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#7c3aed" /><stop offset="100%" stopColor="#6366f1" /></linearGradient>
          <linearGradient id="hot" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#ec4899" /><stop offset="100%" stopColor="#fb7185" /></linearGradient>
        </defs>
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", fontSize: 15, fontWeight: 600,
        fontFamily: "'JetBrains Mono',monospace" }}>{Math.round(pct)}%</div>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
    className="glass" style={{ borderRadius: 18, padding: 20 }}>{children}</motion.div>;
}

export default function MonitorPage() {
  const [s, setS] = useState<any>(null);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try { const d = await apiJson("/api/status"); if (alive) setS(d); } catch {}
    };
    load();
    const t = setInterval(load, 4000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const sys = s?.system, db = s?.db, vec = s?.vector, pm = s?.provider_metrics;

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>System Monitor</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 22px" }}>Live · your Mac, the index, and the AI providers</p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
          <Card><Head icon={<Cpu size={15} />} t="CPU" />
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}><Ring pct={sys?.cpu_percent ?? 0} label="cpu" />
              <div><Meta v={`${sys?.cpu_count ?? "–"} cores`} h="processor" /></div></div></Card>
          <Card><Head icon={<MemoryStick size={15} />} t="RAM" />
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}><Ring pct={sys?.ram_percent ?? 0} label="ram" />
              <div><Meta v={`${sys?.ram_used_gb ?? "–"} / ${sys?.ram_total_gb ?? "–"} GB`} h="in use" /></div></div></Card>
          <Card><Head icon={<HardDrive size={15} />} t="Disk" />
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}><Ring pct={sys?.disk_percent ?? 0} label="disk" />
              <div><Meta v={`${sys?.disk_used_gb ?? "–"} / ${sys?.disk_total_gb ?? "–"} GB`} h="used" /></div></div></Card>
          <Card><Head icon={<FileStack size={15} />} t="Index" />
            <div style={{ fontSize: 30, fontWeight: 600, fontFamily: "'JetBrains Mono',monospace" }}>{db?.files_indexed?.toLocaleString() ?? "–"}</div>
            <Meta v={`${(db?.chunks ?? 0).toLocaleString()} embeddings`} h="files indexed" /></Card>
        </div>

        <h2 style={{ fontSize: 14, fontWeight: 600, margin: "26px 0 12px", display: "flex", alignItems: "center", gap: 8 }}>
          <Activity size={15} color="var(--primary-soft)" /> AI Providers</h2>
        <Card>
          <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginBottom: 12 }}>{s?.llm}</div>
          <div style={{ display: "grid", gap: 8 }}>
            {pm && Object.keys(pm.providers).length === 0 && <div style={{ color: "var(--text-faint)", fontSize: 13 }}>No calls yet — send a message.</div>}
            {pm && Object.entries(pm.providers).map(([name, st]: any) => (
              <div key={name} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 12px",
                borderRadius: 10, background: name === pm.active ? "rgba(124,58,237,.14)" : "var(--surface)", border: "1px solid var(--border)" }}>
                <Zap size={14} color={name === pm.active ? "var(--primary-soft)" : "var(--text-faint)"} />
                <span style={{ fontSize: 13, fontWeight: 500, flex: 1 }}>{name}</span>
                <span style={{ fontSize: 11.5, color: "var(--text-faint)", fontFamily: "'JetBrains Mono',monospace" }}>
                  {st.calls} calls · {st.avg_latency_ms}ms · {st.total_tokens} tok{st.failures ? ` · ${st.failures} fail` : ""}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

const Head = ({ icon, t }: any) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, textTransform: "uppercase",
    letterSpacing: "0.08em", color: "var(--text-muted)", fontWeight: 600, marginBottom: 14 }}>
    <span style={{ color: "var(--primary-soft)" }}>{icon}</span>{t}</div>
);
const Meta = ({ v, h }: any) => (<div><div style={{ fontSize: 13, fontFamily: "'JetBrains Mono',monospace",
  color: "var(--text-muted)" }}>{v}</div><div style={{ fontSize: 11.5, color: "var(--text-faint)", marginTop: 2 }}>{h}</div></div>);
