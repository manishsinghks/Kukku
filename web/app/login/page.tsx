"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sparkles, Loader2 } from "lucide-react";
import { login, authStatus, tokens } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [configured, setConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    if (tokens.access) router.replace("/chat");
    authStatus().then((s) => setConfigured(s.configured)).catch(() => setConfigured(true));
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username.trim(), password);
      router.replace("/chat");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ambient" style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: 24 }}>
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="glass"
        style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 400, borderRadius: 24, padding: 36 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 26 }}>
          <div style={{ width: 44, height: 44, borderRadius: 13, display: "grid", placeItems: "center",
            background: "linear-gradient(135deg,#7c3aed,#6366f1 55%,#ec4899)", boxShadow: "0 0 22px rgba(124,58,237,.45)" }}>
            <Sparkles size={22} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.02em" }}>Kukku OS</div>
            <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>Personal AI Operating System</div>
          </div>
        </div>

        {configured === false ? (
          <div style={{ fontSize: 13.5, color: "var(--text-muted)", lineHeight: 1.6 }}>
            No account exists yet. On your Mac, run:
            <pre style={{ background: "#0b0b12", border: "1px solid var(--border)", borderRadius: 10,
              padding: 12, marginTop: 10, fontSize: 12, color: "var(--primary-soft)", overflowX: "auto" }}>
{`cd ~/jarvis
./.venv/bin/python scripts/set_password.py`}
            </pre>
            then refresh this page.
          </div>
        ) : (
          <form onSubmit={submit}>
            <label className="field-label">Username</label>
            <input className="field" value={username} onChange={(e) => setUsername(e.target.value)}
              autoFocus autoComplete="username" placeholder="your username" />
            <label className="field-label" style={{ marginTop: 14 }}>Password</label>
            <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password" placeholder="••••••••" />
            {error && <div style={{ color: "var(--err)", fontSize: 12.5, marginTop: 12 }}>{error}</div>}
            <button className="btn-primary" type="submit" disabled={busy} style={{ marginTop: 22, width: "100%" }}>
              {busy ? <Loader2 size={16} className="spin" /> : "Sign in"}
            </button>
          </form>
        )}
      </motion.div>

      <style jsx global>{`
        .field-label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 7px; font-weight: 500; }
        .field {
          width: 100%; padding: 11px 14px; border-radius: 12px; color: var(--text); font-size: 14px;
          background: rgba(255,255,255,0.04); border: 1px solid var(--border); outline: none;
          transition: border-color .2s, box-shadow .2s;
        }
        .field::placeholder { color: var(--text-faint); }
        .field:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(124,58,237,.22); }
        .btn-primary {
          display: flex; align-items: center; justify-content: center; gap: 8px;
          padding: 12px 18px; border-radius: 12px; border: none; cursor: pointer;
          font-size: 14px; font-weight: 600; color: #fff;
          background: linear-gradient(135deg,#7c3aed,#6366f1);
          box-shadow: 0 6px 20px rgba(124,58,237,.35); transition: transform .18s, box-shadow .18s, opacity .2s;
        }
        .btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 26px rgba(124,58,237,.5); }
        .btn-primary:disabled { opacity: .7; cursor: default; }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
