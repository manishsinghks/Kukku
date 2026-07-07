"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Zap, FolderInput, Mic, ScanText, ShieldCheck, HardDrive } from "lucide-react";
import { apiJson } from "@/lib/api";

export default function SettingsPage() {
  const [s, setS] = useState<any>(null);
  useEffect(() => { apiJson("/api/settings").then(setS).catch(() => {}); }, []);
  if (!s) return null;
  const order = s.llm_priority.split(",").filter((x: string) => ["gemini", "groq", "openrouter", "ollama", "claude"].includes(x));

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 780, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>Settings</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 8px" }}>Current configuration. Edits go through <code style={{ background: "var(--surface)", padding: "1px 6px", borderRadius: 5 }}>.env</code> + restart (safe by design).</p>

        <Card icon={<Zap size={15} />} title="AI Provider Priority">
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {order.map((p: string, i: number) => (
              <span key={p} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 500, padding: "6px 13px", borderRadius: 99,
                  background: i === 0 ? "linear-gradient(135deg,rgba(124,58,237,.3),rgba(99,102,241,.2))" : "var(--surface)",
                  border: "1px solid var(--border)", textTransform: "capitalize", color: i === 0 ? "#fff" : "var(--text-muted)" }}>
                  {i === 0 && "★ "}{p}
                </span>
                {i < order.length - 1 && <span style={{ color: "var(--text-faint)" }}>→</span>}
              </span>
            ))}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 10 }}>Failover order. First is primary; falls through on rate-limit or error.</div>
        </Card>

        <Card icon={<FolderInput size={15} />} title="Indexed Folders">
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {s.index_dirs.map((d: string) => (
              <div key={d} style={{ fontSize: 12.5, fontFamily: "'JetBrains Mono',monospace", color: "var(--text-muted)" }}>{d}</div>
            ))}
          </div>
        </Card>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 14 }}>
          <Card icon={<Mic size={15} />} title="Voice"><KV k="Whisper model" v={s.whisper_model} /><KV k="Enabled" v={s.enable_voice ? "yes" : "no"} /></Card>
          <Card icon={<ScanText size={15} />} title="OCR"><KV k="Enabled" v={s.enable_ocr ? "yes (eng+hin)" : "no"} /></Card>
          <Card icon={<HardDrive size={15} />} title="Indexing"><KV k="Max file size" v={`${s.max_file_size_mb} MB`} /><KV k="Rescan" v={`${s.rescan_interval_min} min`} /></Card>
          <Card icon={<ShieldCheck size={15} />} title="Alerts & Backup"><KV k="Battery alert" v={`< ${s.alert_battery_pct}%`} /><KV k="Disk alert" v={`> ${s.alert_disk_pct}%`} /><KV k="Auto-backup" v={s.backup_enabled ? "on" : "off"} /></Card>
        </div>
      </div>
    </div>
  );
}
function Card({ icon, title, children }: any) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass" style={{ borderRadius: 16, padding: 18, marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em",
        color: "var(--text-muted)", fontWeight: 600, marginBottom: 14 }}><span style={{ color: "var(--primary-soft)" }}>{icon}</span>{title}</div>
      {children}
    </motion.div>
  );
}
const KV = ({ k, v }: any) => (<div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13 }}>
  <span style={{ color: "var(--text-muted)" }}>{k}</span><span style={{ fontWeight: 500, fontFamily: "'JetBrains Mono',monospace", fontSize: 12.5 }}>{v}</span></div>);
