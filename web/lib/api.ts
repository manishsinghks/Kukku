// API client: talks to the shared Python backend. Handles JWT access/refresh
// and SSE streaming for chat + realtime events.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8788";

const ACCESS = "jarvis_access";
const REFRESH = "jarvis_refresh";

export const tokens = {
  get access() {
    return typeof window !== "undefined" ? localStorage.getItem(ACCESS) : null;
  },
  get refresh() {
    return typeof window !== "undefined" ? localStorage.getItem(REFRESH) : null;
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

async function refreshAccess(): Promise<boolean> {
  const rt = tokens.refresh;
  if (!rt) return false;
  const r = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!r.ok) return false;
  const d = await r.json();
  tokens.set(d.access_token, d.refresh_token);
  return true;
}

// authenticated fetch with one automatic refresh-and-retry on 401
export async function api(path: string, init: RequestInit = {}): Promise<Response> {
  const doFetch = () =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        ...(init.headers || {}),
        ...(tokens.access ? { Authorization: `Bearer ${tokens.access}` } : {}),
      },
    });
  let r = await doFetch();
  if (r.status === 401 && (await refreshAccess())) r = await doFetch();
  return r;
}

export async function apiJson<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await api(path, init);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

export async function login(username: string, password: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail || "Login failed");
  }
  const d = await r.json();
  tokens.set(d.access_token, d.refresh_token);
}

export async function authStatus(): Promise<{ configured: boolean; user: string | null }> {
  const r = await fetch(`${API_BASE}/api/auth/status`);
  return r.json();
}

// Stream a chat message. Calls onToken(accumulatedText) as it streams,
// then onDone(meta) with { provider, latency_ms, files }.
export async function streamChat(
  message: string,
  onToken: (text: string) => void,
  onDone: (meta: any) => void,
  onError: (msg: string) => void,
): Promise<void> {
  const r = await api("/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!r.ok || !r.body) {
    onError("Request failed. Please try again.");
    return;
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      let ev: any;
      try {
        ev = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (ev.type === "token") onToken(ev.text);
      else if (ev.type === "done") onDone(ev);
      else if (ev.type === "error") onError(ev.message);
    }
  }
}

// Subscribe to realtime events (Telegram ↔ dashboard sync). Returns a cleanup fn.
export function subscribeEvents(onEvent: (ev: any) => void): () => void {
  const t = tokens.access;
  if (!t) return () => {};
  const es = new EventSource(`${API_BASE}/api/events?token=${encodeURIComponent(t)}`);
  es.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data));
    } catch {
      /* ignore */
    }
  };
  es.onerror = () => {}; // browser auto-reconnects
  return () => es.close();
}
