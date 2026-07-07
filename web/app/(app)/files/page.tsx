"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FileText, FileCode, Image as ImageIcon, Database, File, Download, FolderOpen, Search } from "lucide-react";
import { apiJson, API_BASE, tokens } from "@/lib/api";

const TYPES = ["all", "document", "code", "image", "data"];
const iconFor = (t: string) => ({ document: FileText, code: FileCode, image: ImageIcon, data: Database }[t] || File);

export default function FilesPage() {
  const [files, setFiles] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [type, setType] = useState("all");

  const load = () => {
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (type !== "all") params.set("type", type);
    apiJson(`/api/files/list?${params}`).then((d: any) => setFiles(d.files || [])).catch(() => {});
  };
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [q, type]);

  function download(path: string) {
    window.open(`${API_BASE}/api/files/download?path=${encodeURIComponent(path)}`, "_blank");
  }
  async function reveal(path: string) {
    await fetch(`${API_BASE}/api/files/reveal`, { method: "POST",
      headers: { "content-type": "application/json", Authorization: `Bearer ${tokens.access}` },
      body: JSON.stringify({ path }) });
  }
  const fmtSize = (b: number) => !b ? "" : b > 1e9 ? (b / 1e9).toFixed(1) + " GB" : b > 1e6 ? (b / 1e6).toFixed(1) + " MB" : Math.round(b / 1e3) + " KB";

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>File Explorer</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 18px" }}>Every file Kukku has indexed — download or reveal in Finder.</p>

        <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div className="glass" style={{ borderRadius: 11, padding: "2px 2px 2px 12px", display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 200 }}>
            <Search size={16} color="var(--text-faint)" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by name…"
              style={{ flex: 1, background: "none", border: "none", outline: "none", color: "var(--text)", fontSize: 13.5, padding: "9px 0" }} />
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {TYPES.map((t) => (
              <button key={t} onClick={() => setType(t)} className={`seg${type === t ? " on" : ""}`}>{t}</button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          {files.map((f, i) => {
            const Icon = iconFor(f.file_type);
            return (
              <motion.div key={f.path} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: Math.min(i * 0.01, 0.3) }}
                className="row">
                <Icon size={17} color="var(--primary-soft)" style={{ flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{f.name}</div>
                  <div style={{ fontSize: 11, color: "var(--text-faint)", fontFamily: "'JetBrains Mono',monospace", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{f.path}</div>
                </div>
                <span style={{ fontSize: 11.5, color: "var(--text-faint)", flexShrink: 0 }}>{fmtSize(f.size)}</span>
                <button className="tinyBtn" title="Reveal in Finder" onClick={() => reveal(f.path)}><FolderOpen size={15} /></button>
                <button className="tinyBtn" title="Download" onClick={() => download(f.path)}><Download size={15} /></button>
              </motion.div>
            );
          })}
          {files.length === 0 && <div style={{ fontSize: 13, color: "var(--text-faint)", padding: "8px 2px" }}>No files match.</div>}
        </div>
      </div>
      <style jsx global>{`
        .seg { padding: 8px 13px; border-radius: 9px; font-size: 12.5px; text-transform: capitalize; background: var(--surface);
          border: 1px solid var(--border); color: var(--text-muted); cursor: pointer; }
        .seg.on { background: linear-gradient(135deg,rgba(124,58,237,.3),rgba(99,102,241,.2)); color: #fff; border-color: rgba(124,58,237,.5); }
        .row { display: flex; align-items: center; gap: 12px; padding: 10px 13px; border-radius: 11px; border: 1px solid transparent; transition: background .15s, border-color .15s; }
        .row:hover { background: var(--surface); border-color: var(--border); }
        .tinyBtn { background: none; border: none; color: var(--text-faint); cursor: pointer; padding: 6px; border-radius: 8px; flex-shrink: 0; }
        .tinyBtn:hover { color: var(--primary-soft); background: var(--surface-hover); }
      `}</style>
    </div>
  );
}
