/**
 * Kukku Cloud Relay — Cloudflare Worker + Durable Object (free tier).
 *
 * Telegram webhook lands here. The Mac connects OUTBOUND via long-poll (no
 * tunnel, no inbound exposure), so there is nothing to break: the Mac holds a
 * /pull request open on the RelayDO; when an update arrives the DO hands it over
 * in real time. If the Mac isn't polling (off / asleep), the Worker answers
 * general questions itself via Gemini -> Groq.
 *
 * Secrets (wrangler secret put): BOT_TOKEN, GEMINI_API_KEY, BRIDGE_SECRET,
 *                                WEBHOOK_SECRET, ALLOWED_USER_IDS,
 *                                GROQ_API_KEY (optional failover)
 * Durable Object binding: RELAY (class RelayDO)
 */

const TG = (token, method) => `https://api.telegram.org/bot${token}/${method}`;
const OFFLINE_NOTE = "\n\n_💤 Mac is offline — general answers only (no files/commands)._";
const LONGPOLL_MS = 20000; // how long a /pull is held open when idle
const ONLINE_WINDOW_MS = 30000; // Mac counts as online if it pulled within this

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json" } });

function relayStub(env) {
  return env.RELAY.get(env.RELAY.idFromName("singleton"));
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/webhook" && request.method === "POST") {
      return handleWebhook(request, env, ctx);
    }
    if (url.pathname === "/pull" && request.method === "POST") {
      if (request.headers.get("x-bridge-secret") !== env.BRIDGE_SECRET) {
        return json({ error: "unauthorized" }, 401);
      }
      return relayStub(env).fetch("https://do/pull", { method: "POST" });
    }
    if (url.pathname === "/register" && request.method === "POST") {
      // legacy no-op (kept so old setup scripts don't error)
      return json({ ok: true, note: "long-poll relay; registration not needed" });
    }
    if (url.pathname === "/health") return json({ ok: true });
    return new Response("kukku relay", { status: 200 });
  },
};

async function handleWebhook(request, env, ctx) {
  if (request.headers.get("x-telegram-bot-api-secret-token") !== env.WEBHOOK_SECRET) {
    return json({ error: "unauthorized" }, 401);
  }
  const update = await request.json();
  const msg = update.message || update.edited_message;
  const chatId = msg?.chat?.id;
  const userId = msg?.from?.id;

  // security: only the owner (mirrors the Mac-side allowlist)
  const allowed = (env.ALLOWED_USER_IDS || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (userId && allowed.length && !allowed.includes(String(userId))) {
    return json({ ok: true }); // silently drop strangers
  }

  // hand to the DO; it tells us whether the Mac is currently polling
  let online = false;
  try {
    const r = await relayStub(env).fetch("https://do/deliver", {
      method: "POST",
      body: JSON.stringify(update),
    });
    online = (await r.json()).online;
  } catch (e) {
    console.log(`deliver failed: ${e.message}`);
  }
  if (online) return json({ ok: true, via: "mac" });

  // Mac offline -> answer here
  if (chatId && msg?.text) {
    ctx.waitUntil(answerOffline(env, chatId, msg.text));
  } else if (chatId) {
    ctx.waitUntil(
      sendMessage(env, chatId,
        "💤 My Mac is offline right now — I can only answer text questions. Voice, files and commands will work again once it's back on.")
    );
  }
  return json({ ok: true, via: "cloud" });
}

/** Durable Object: a real-time mailbox between the webhook and the Mac's poll. */
export class RelayDO {
  constructor(state, env) {
    this.queue = []; // {at, update}
    this.waiters = []; // resolver fns for held-open /pull requests
    this.lastPullAt = 0;
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname === "/deliver") {
      const update = await request.json();
      const online = this.waiters.length > 0 || Date.now() - this.lastPullAt < ONLINE_WINDOW_MS;
      if (online) {
        this.queue.push({ at: Date.now(), update });
        const wake = this.waiters.shift();
        if (wake) wake();
      }
      return json({ online });
    }

    if (url.pathname === "/pull") {
      this.lastPullAt = Date.now();
      if (this.queue.length === 0) {
        await new Promise((resolve) => {
          this.waiters.push(resolve);
          setTimeout(resolve, LONGPOLL_MS);
        });
      }
      const now = Date.now();
      // drop anything stale (Mac was away) so old commands never fire late
      const updates = this.queue.filter((x) => now - x.at < 45000).map((x) => x.update);
      this.queue = [];
      return json({ updates });
    }

    return new Response("relay-do", { status: 200 });
  }
}

const SYSTEM_PROMPT =
  "You are Kukku, a personal Telegram assistant. The owner's Mac " +
  "(which holds their files and local tools) is currently offline, so you " +
  "can only answer general questions from knowledge. Be concise and helpful. " +
  "If asked about their files, laptop, or local commands, say the Mac is " +
  "offline and that part will work when it's back.";

async function openaiChat(baseUrl, apiKey, model, text) {
  const r = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model,
      max_tokens: 1024,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: text.slice(0, 4000) },
      ],
    }),
    signal: AbortSignal.timeout(30000),
  });
  if (!r.ok) throw new Error(`${model} -> HTTP ${r.status}`);
  const data = await r.json();
  return data?.choices?.[0]?.message?.content?.trim() || null;
}

async function answerOffline(env, chatId, text) {
  await fetch(TG(env.BOT_TOKEN, "sendChatAction"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, action: "typing" }),
  }).catch(() => {});

  const providers = [
    {
      name: "gemini",
      url: "https://generativelanguage.googleapis.com/v1beta/openai",
      key: env.GEMINI_API_KEY,
      model: env.GEMINI_MODEL || "gemini-2.5-flash",
    },
    {
      name: "groq",
      url: "https://api.groq.com/openai/v1",
      key: env.GROQ_API_KEY,
      model: env.GROQ_MODEL || "llama-3.3-70b-versatile",
    },
  ].filter((p) => p.key);

  let reply = null;
  for (const p of providers) {
    try {
      reply = await openaiChat(p.url, p.key, p.model, text);
      if (reply) break;
    } catch (e) {
      console.log(`offline answer via ${p.name} failed: ${e.message}`);
    }
  }
  if (!reply) reply = "⚠️ Couldn't reach any AI service just now — try again in a minute.";
  await sendMessage(env, chatId, reply.slice(0, 3900) + OFFLINE_NOTE, "Markdown");
}

async function sendMessage(env, chatId, text, parseMode) {
  const body = { chat_id: chatId, text };
  if (parseMode) body.parse_mode = parseMode;
  const r = await fetch(TG(env.BOT_TOKEN, "sendMessage"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok && parseMode) {
    await fetch(TG(env.BOT_TOKEN, "sendMessage"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
  }
}
