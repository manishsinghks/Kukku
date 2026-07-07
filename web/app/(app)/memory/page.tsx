"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, Plus, Trash2, Link2, Download } from "lucide-react";
import { apiJson, API_BASE, tokens } from "@/lib/api";

export default function MemoryPage() {
  const [memories, setMemories] = useState<any[]>([]);
  const [aliases, setAliases] = useState<any[]>([]);
  const [text, setText] = useState("");

  const load = () => apiJson("/api/memory/export").then((d: any) => { setMemories(d.memories || []); setAliases(d.aliases || []); }).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add() {
    const c = text.trim();
    if (!c) return;
    setText("");
    await apiJson("/api/memory", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ content: c }) }).catch(() => {});
    load();
  }
  async function del(id: number) {
    await apiJson(`/api/memory/${id}`, { method: "DELETE" }).catch(() => {});
    setMemories((m) => m.filter((x) => x.id !== id));
  }
  function exportJson() {
    const blob = new Blob([JSON.stringify({ memories, aliases }, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "kukku-memory.json"; a.click();
  }

  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 760, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 4 }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Memory</h1>
          <button className="ghostBtn" style={{ marginLeft: "auto" }} onClick={exportJson}><Download size={14} /> Export</button>
        </div>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 18px" }}>Facts Kukku remembers across Telegram and here — one shared brain.</p>

        <div className="glass" style={{ borderRadius: 14, padding: 8, display: "flex", gap: 8, marginBottom: 22 }}>
          <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()}
            placeholder="Remember that…" style={{ flex: 1, background: "none", border: "none", outline: "none", color: "var(--text)", fontSize: 14, padding: "8px 12px" }} />
          <button className="sendBtn" onClick={add}><Plus size={17} /></button>
        </div>

        <SectionTitle icon={<Brain size={14} />} t={`Memories (${memories.length})`} />
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 22 }}>
          <AnimatePresence>
            {memories.map((m) => (
              <motion.div key={m.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, height: 0 }}
                className="glass" style={{ borderRadius: 12, padding: "11px 14px", display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ flex: 1, fontSize: 13.5 }}>{m.content}</span>
                <button className="tinyBtn" onClick={() => del(m.id)}><Trash2 size={14} /></button>
              </motion.div>
            ))}
          </AnimatePresence>
          {memories.length === 0 && <Empty t="No memories yet." />}
        </div>

        <SectionTitle icon={<Link2 size={14} />} t={`Aliases (${aliases.length})`} />
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {aliases.map((a) => (
            <div key={a.name} className="glass" style={{ borderRadius: 12, padding: "11px 14px", fontSize: 13.5 }}>
              <b>{a.name}</b> → <span style={{ color: "var(--text-muted)", fontFamily: "'JetBrains Mono',monospace", fontSize: 12.5 }}>{a.value}</span>
            </div>
          ))}
          {aliases.length === 0 && <Empty t="No aliases yet." />}
        </div>
      </div>
      <style jsx global>{`
        .ghostBtn { padding: 7px 12px; font-size: 12.5px; border: 1px solid var(--border); background: var(--surface);
          color: var(--text-muted); border-radius: 8px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
        .ghostBtn:hover { color: var(--text); }
        .tinyBtn { background: none; border: none; color: var(--text-faint); cursor: pointer; padding: 4px; border-radius: 7px; }
        .tinyBtn:hover { color: var(--err); background: var(--surface-hover); }
        .sendBtn { width: 38px; height: 38px; border-radius: 11px; border: none; cursor: pointer; display: grid; place-items: center;
          color: #fff; background: linear-gradient(135deg,#7c3aed,#6366f1); }
      `}</style>
    </div>
  );
}
const SectionTitle = ({ icon, t }: any) => (<div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 11,
  textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", fontWeight: 600, marginBottom: 10 }}>
  <span style={{ color: "var(--primary-soft)" }}>{icon}</span>{t}</div>);
const Empty = ({ t }: any) => <div style={{ fontSize: 13, color: "var(--text-faint)", padding: "6px 2px" }}>{t}</div>;
