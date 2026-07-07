"use client";
import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Search, FileText, Brain, Link2, Loader2 } from "lucide-react";
import { apiJson } from "@/lib/api";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const deb = useRef<any>(null);

  useEffect(() => {
    if (!q.trim()) { setRes(null); return; }
    clearTimeout(deb.current);
    deb.current = setTimeout(async () => {
      setBusy(true);
      try { setRes(await apiJson(`/api/search?q=${encodeURIComponent(q.trim())}`)); } catch {}
      setBusy(false);
    }, 300);
    return () => clearTimeout(deb.current);
  }, [q]);

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 780, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>Universal Search</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 18px" }}>One bar across files, screenshots (OCR), memory & aliases — by meaning.</p>

        <div className="glass" style={{ borderRadius: 14, padding: "4px 4px 4px 16px", display: "flex", alignItems: "center", gap: 10 }}>
          {busy ? <Loader2 size={18} className="spin" style={{ color: "var(--primary-soft)" }} /> : <Search size={18} color="var(--text-faint)" />}
          <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus placeholder="Search everything…"
            style={{ flex: 1, background: "none", border: "none", outline: "none", color: "var(--text)", fontSize: 15, padding: "12px 0" }} />
        </div>

        {res && (
          <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 20 }}>
            <Section title="Files" icon={<FileText size={14} />} items={res.files}
              render={(f: any) => (<><div style={{ fontWeight: 500, fontSize: 13.5 }}>{f.name}</div>
                <div style={{ fontSize: 11.5, color: "var(--text-faint)", fontFamily: "'JetBrains Mono',monospace" }}>{f.path}</div>
                {f.snippet && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{f.snippet.slice(0, 140)}</div>}</>)} />
            <Section title="Memory" icon={<Brain size={14} />} items={res.memories}
              render={(m: any) => <div style={{ fontSize: 13.5 }}>{m.content}</div>} />
            <Section title="Aliases" icon={<Link2 size={14} />} items={res.aliases}
              render={(a: any) => <div style={{ fontSize: 13.5 }}>{a.name} → <span style={{ color: "var(--text-muted)" }}>{a.value}</span></div>} />
          </div>
        )}
      </div>
      <style jsx global>{`.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

function Section({ title, icon, items, render }: any) {
  if (!items?.length) return null;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 11, textTransform: "uppercase",
        letterSpacing: "0.08em", color: "var(--text-muted)", fontWeight: 600, marginBottom: 8 }}>
        <span style={{ color: "var(--primary-soft)" }}>{icon}</span>{title} <span style={{ color: "var(--text-faint)" }}>({items.length})</span></div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map((it: any, i: number) => (
          <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
            className="glass" style={{ borderRadius: 12, padding: "11px 14px" }}>{render(it)}</motion.div>
        ))}
      </div>
    </div>
  );
}
