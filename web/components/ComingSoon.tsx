"use client";
import { motion } from "framer-motion";

export default function ComingSoon({ title, subtitle, icon: Icon, features }: {
  title: string; subtitle: string; icon: any; features: string[];
}) {
  return (
    <div style={{ overflowY: "auto", padding: "24px 28px", height: "100%" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>{title}</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 24px" }}>{subtitle}</p>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          className="glass" style={{ borderRadius: 20, padding: 40, textAlign: "center" }}>
          <div style={{ width: 60, height: 60, borderRadius: 17, margin: "0 auto 20px", display: "grid", placeItems: "center",
            background: "linear-gradient(135deg,rgba(124,58,237,.25),rgba(99,102,241,.15))", border: "1px solid var(--border)" }}>
            <Icon size={28} color="var(--primary-soft)" />
          </div>
          <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 6 }}>Coming in the next build</div>
          <div style={{ fontSize: 13.5, color: "var(--text-muted)", maxWidth: 420, margin: "0 auto 22px" }}>
            The backend for this is being wired to the same shared engine. Planned:
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
            {features.map((f) => (
              <span key={f} style={{ fontSize: 12.5, padding: "6px 12px", borderRadius: 99, background: "var(--surface)",
                border: "1px solid var(--border)", color: "var(--text-muted)" }}>{f}</span>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
