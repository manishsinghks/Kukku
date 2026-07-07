"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Send, Sparkles, Copy, Check, Loader2, Zap, Trash2, Mic, Volume2, Square } from "lucide-react";
import { apiJson, streamChat, subscribeEvents } from "@/lib/api";
import { useSpeech } from "@/lib/useSpeech";
import { useTTS } from "@/lib/useTTS";

type Msg = {
  role: "user" | "assistant";
  content: string;
  provider?: string;
  latency_ms?: number;
  streaming?: boolean;
  ts?: number;
};

function Bubble({
  m,
  ttsSupported,
  speaking,
  onToggleSpeak,
}: {
  m: Msg;
  ttsSupported: boolean;
  speaking: boolean;
  onToggleSpeak: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const isUser = m.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      style={{ display: "flex", gap: 12, justifyContent: isUser ? "flex-end" : "flex-start" }}
    >
      {!isUser && (
        <div style={{ width: 30, height: 30, borderRadius: 9, flexShrink: 0, display: "grid", placeItems: "center",
          background: "linear-gradient(135deg,#7c3aed,#6366f1)", marginTop: 2 }}>
          <Sparkles size={15} color="#fff" />
        </div>
      )}
      <div style={{ maxWidth: "76%" }}>
        <div className={isUser ? "" : "glass"} style={{
          padding: isUser ? "10px 15px" : "13px 16px", borderRadius: 16,
          borderTopRightRadius: isUser ? 4 : 16, borderTopLeftRadius: isUser ? 16 : 4,
          background: isUser ? "linear-gradient(135deg,#7c3aed,#6366f1)" : undefined,
          color: isUser ? "#fff" : "var(--text)", fontSize: 14.5, lineHeight: 1.55,
        }}>
          {isUser ? (
            <span style={{ whiteSpace: "pre-wrap" }}>{m.content}</span>
          ) : (
            <div className="md">
              {m.content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{m.content}</ReactMarkdown>
              ) : (
                <Loader2 size={15} className="spin" style={{ color: "var(--text-muted)" }} />
              )}
            </div>
          )}
        </div>
        {!isUser && !m.streaming && m.content && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6, paddingLeft: 4 }}>
            {m.provider && (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11,
                color: "var(--text-faint)", background: "var(--surface)", padding: "2px 8px", borderRadius: 99, border: "1px solid var(--border)" }}>
                <Zap size={11} color="var(--primary-soft)" /> {m.provider.split(" ")[0]}
              </span>
            )}
            {m.latency_ms != null && <span style={{ fontSize: 11, color: "var(--text-faint)" }}>{(m.latency_ms / 1000).toFixed(1)}s</span>}
            <button className="tinyBtn" onClick={() => { navigator.clipboard.writeText(m.content); setCopied(true); setTimeout(() => setCopied(false), 1200); }}>
              {copied ? <Check size={13} /> : <Copy size={13} />}
            </button>
            {ttsSupported && (
              <button className={`tinyBtn${speaking ? " speaking" : ""}`} title={speaking ? "Stop" : "Read aloud"} onClick={onToggleSpeak}>
                {speaking ? <Square size={12} /> : <Volume2 size={13} />}
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [lang, setLang] = useState("en-IN");
  const [autoSpeak, setAutoSpeak] = useState(false);
  const speech = useSpeech(lang, setInput);
  const tts = useTTS(lang);
  const autoSpeakRef = useRef(autoSpeak);
  autoSpeakRef.current = autoSpeak;
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    apiJson<{ messages: Msg[] }>("/api/chat/history?limit=100")
      .then((d) => setMessages(d.messages || []))
      .catch(() => {});
  }, []);

  // realtime: Telegram messages appear here live
  useEffect(() => {
    const off = subscribeEvents((ev) => {
      if (ev.type === "message" && ev.source === "telegram") {
        setMessages((prev) => {
          const idx = prev.length;
          if (autoSpeakRef.current && ev.role === "assistant" && ev.content) tts.speak(idx, ev.content);
          return [...prev, { role: ev.role, content: ev.content, provider: ev.provider, latency_ms: ev.latency_ms }];
        });
      }
    });
    return off;
  }, [tts]);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    if (speech.listening) speech.stop();
    if (tts.speakingId != null) tts.cancel();
    setInput("");
    setSending(true);
    let assistantIdx = 0;
    setMessages((p) => { assistantIdx = p.length + 1; return [...p, { role: "user", content: text }, { role: "assistant", content: "", streaming: true }]; });
    await streamChat(
      text,
      (acc) => setMessages((p) => { const n = [...p]; n[n.length - 1] = { ...n[n.length - 1], content: acc }; return n; }),
      (meta) => {
        setMessages((p) => { const n = [...p]; n[n.length - 1] = { role: "assistant", content: meta.text, provider: meta.provider, latency_ms: meta.latency_ms }; return n; });
        if (autoSpeakRef.current && meta.text) tts.speak(assistantIdx, meta.text);
      },
      (msg) => setMessages((p) => { const n = [...p]; n[n.length - 1] = { role: "assistant", content: `⚠️ ${msg}` }; return n; }),
    );
    setSending(false);
  }

  async function clearChat() {
    await apiJson("/api/chat/clear", { method: "POST" }).catch(() => {});
    setMessages([]);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 24px", borderBottom: "1px solid var(--border)" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 600, letterSpacing: "-0.01em" }}>AI Chat</div>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Same brain as Telegram · syncs live · English / Hindi / Hinglish</div>
        </div>
        {tts.supported && (
          <button
            className={`ghostBtn${autoSpeak ? " on" : ""}`}
            style={{ marginLeft: "auto" }}
            title="Read new replies aloud"
            onClick={() => { if (autoSpeak) tts.cancel(); setAutoSpeak((v) => !v); }}
          >
            <Volume2 size={14} /> Auto-speak{autoSpeak ? " on" : ""}
          </button>
        )}
        <button className="ghostBtn" style={{ marginLeft: tts.supported ? 0 : "auto" }} onClick={clearChat}><Trash2 size={14} /> Clear</button>
      </header>

      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "24px 24px 8px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", display: "flex", flexDirection: "column", gap: 18 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", paddingTop: 80, color: "var(--text-muted)" }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, margin: "0 auto 18px", display: "grid", placeItems: "center",
                background: "linear-gradient(135deg,#7c3aed,#6366f1 55%,#ec4899)", boxShadow: "0 0 30px rgba(124,58,237,.4)" }}>
                <Sparkles size={26} color="#fff" />
              </div>
              <div style={{ fontSize: 19, fontWeight: 600, color: "var(--text)", marginBottom: 6 }}>How can I help?</div>
              <div style={{ fontSize: 14 }}>Ask anything, find files, run commands — try “mera resume dhundo”.</div>
            </div>
          )}
          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <Bubble
                key={i}
                m={m}
                ttsSupported={tts.supported && m.role === "assistant"}
                speaking={tts.speakingId === i}
                onToggleSpeak={() => tts.toggle(i, m.content)}
              />
            ))}
          </AnimatePresence>
          <div ref={bottomRef} />
        </div>
      </div>

      <div style={{ padding: "12px 24px 22px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          {speech.supported && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, paddingLeft: 4 }}>
              {speech.listening && (
                <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.2, repeat: Infinity }}
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--accent)" }}>
                  <span style={{ width: 7, height: 7, borderRadius: 99, background: "var(--accent)" }} /> Listening…
                </motion.span>
              )}
              <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
                {[["en-IN", "EN"], ["hi-IN", "हिं"]].map(([code, label]) => (
                  <button key={code} onClick={() => setLang(code)}
                    className={`langPill${lang === code ? " on" : ""}`}>{label}</button>
                ))}
              </div>
            </div>
          )}
          <div className="glass" style={{ borderRadius: 18, padding: 8, display: "flex", alignItems: "flex-end", gap: 8 }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Message Kukku…  (Enter to send, Shift+Enter for newline)"
              rows={1}
              style={{ flex: 1, resize: "none", background: "none", border: "none", outline: "none", color: "var(--text)",
                fontSize: 14.5, fontFamily: "inherit", padding: "10px 12px", maxHeight: 160, lineHeight: 1.5 }}
            />
            {speech.supported && (
              <button title={speech.listening ? "Stop" : "Speak"} className={`micBtn${speech.listening ? " rec" : ""}`}
                onClick={() => (speech.listening ? speech.stop() : speech.start(input))}>
                <Mic size={17} />
              </button>
            )}
            <button onClick={send} disabled={!input.trim() || sending} className="sendBtn">
              {sending ? <Loader2 size={17} className="spin" /> : <Send size={17} />}
            </button>
          </div>
        </div>
      </div>

      <style jsx global>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .tinyBtn, .ghostBtn { background: none; border: 1px solid transparent; color: var(--text-faint); cursor: pointer;
          border-radius: 8px; display: inline-flex; align-items: center; gap: 6px; transition: color .16s, background .16s; }
        .tinyBtn { padding: 3px; }
        .tinyBtn:hover { color: var(--text); background: var(--surface-hover); }
        .ghostBtn { padding: 7px 12px; font-size: 12.5px; border-color: var(--border); background: var(--surface); }
        .ghostBtn:hover { color: var(--text); border-color: var(--border-strong); }
        .ghostBtn.on { color: #fff; background: rgba(124,58,237,.28); border-color: rgba(124,58,237,.5); }
        .tinyBtn.speaking { color: var(--primary-soft); }
        .tinyBtn.speaking svg { animation: ttsPulse 1.1s ease-in-out infinite; }
        @keyframes ttsPulse { 0%,100% { opacity: .55; } 50% { opacity: 1; } }
        .sendBtn { width: 40px; height: 40px; border-radius: 12px; border: none; cursor: pointer; flex-shrink: 0;
          display: grid; place-items: center; color: #fff; background: linear-gradient(135deg,#7c3aed,#6366f1);
          box-shadow: 0 4px 14px rgba(124,58,237,.35); transition: transform .16s, opacity .2s; }
        .sendBtn:hover:not(:disabled) { transform: translateY(-1px); }
        .sendBtn:disabled { opacity: .4; cursor: default; }
        .micBtn { width: 40px; height: 40px; border-radius: 12px; border: 1px solid var(--border); cursor: pointer; flex-shrink: 0;
          display: grid; place-items: center; color: var(--text-muted); background: var(--surface); transition: color .16s, background .16s, border-color .16s; }
        .micBtn:hover { color: var(--text); border-color: var(--border-strong); }
        .micBtn.rec { color: #fff; background: linear-gradient(135deg,#ec4899,#fb7185); border-color: transparent;
          box-shadow: 0 0 0 0 rgba(236,72,153,.5); animation: pulse 1.4s ease-out infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(236,72,153,.45); } 70% { box-shadow: 0 0 0 9px rgba(236,72,153,0); } 100% { box-shadow: 0 0 0 0 rgba(236,72,153,0); } }
        .langPill { font-size: 11px; padding: 3px 9px; border-radius: 99px; cursor: pointer; background: var(--surface);
          border: 1px solid var(--border); color: var(--text-faint); }
        .langPill.on { color: #fff; background: rgba(124,58,237,.28); border-color: rgba(124,58,237,.5); }
      `}</style>
    </div>
  );
}
