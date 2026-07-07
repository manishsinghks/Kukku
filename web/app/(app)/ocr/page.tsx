"use client";
import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ScanText, Loader2, FolderOpen } from "lucide-react";
import { apiJson, API_BASE, tokens } from "@/lib/api";

export default function OcrPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[] | null>(null);
  const [busy, setBusy] = useState(false);
  const deb = useRef<any>(null);

  useEffect(() => {
    if (!q.trim()) { setResults(null); return; }
    clearTimeout(deb.current);
    deb.current = setTimeout(async () => {
      setBusy(true);
      try { const d: any = await apiJson(`/api/ocr/search?q=${encodeURIComponent(q.trim())}`); setResults(d.results); } catch {}
      setBusy(false);
    }, 300);
    return () => clearTimeout(deb.current);
  }, [q]);

  async function reveal(path: string) {
    await fetch(`${API_BASE}/api/files/reveal`, { method: "POST",
      headers: { "content-type": "application/json", Authorization: `Bearer ${tokens.access}` }, body: JSON.stringify({ path }) });
  }

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 780, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>OCR Search</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 18px" }}>Search the text inside your screenshots & images (English + Hindi).</p>

        <div className="glass" style={{ borderRadius: 14, padding: "4px 4px 4px 16px", display: "flex", alignItems: "center", gap: 10 }}>
          {busy ? <Loader2 size={18} className="spin" style={{ color: "var(--primary-soft)" }} /> : <ScanText size={18} color="var(--text-faint)" />}
          <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus placeholder='e.g. "docker failed", "wifi password"…'
            style={{ flex: 1, background: "none", border: "none", outline: "none", color: "var(--text)", fontSize: 15, padding: "12px 0" }} />
        </div>

        {results && (
          <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 8 }}>
            {results.length === 0 && <div style={{ fontSize: 13, color: "var(--text-faint)" }}>No screenshots match. Add images and send /reindex to the bot.</div>}
            {results.map((r, i) => (
              <motion.div key={r.path} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                className="glass" style={{ borderRadius: 12, padding: "12px 14px", display: "flex", gap: 12, alignItems: "center" }}>
                <ScanText size={18} color="var(--primary-soft)" style={{ flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 500 }}>{r.name}</div>
                  {r.snippet && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 3 }}>…{r.snippet.slice(0, 120)}…</div>}
                </div>
                <button className="tinyBtn" title="Reveal in Finder" onClick={() => reveal(r.path)}><FolderOpen size={15} /></button>
              </motion.div>
            ))}
          </div>
        )}
      </div>
      <style jsx global>{`.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
        .tinyBtn{background:none;border:none;color:var(--text-faint);cursor:pointer;padding:6px;border-radius:8px}
        .tinyBtn:hover{color:var(--primary-soft);background:var(--surface-hover)}`}</style>
    </div>
  );
}
