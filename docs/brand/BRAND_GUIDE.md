<div align="center">
  <img src="../../assets/brand/logo-mark.svg" width="96" height="96" alt="Kukku" />
  <h1>Kukku — Brand Guide</h1>
  <p><em>Local by design. Personal by default.</em></p>
</div>

> A single source of truth for Kukku's product identity: voice, logo, colour,
> type, and the small design system that makes every surface feel handcrafted.
> Design north stars: **Linear, Raycast, Arc, Notion, Cursor, Apple.**
> Design language: **modern · minimal · elegant · premium · friendly · timeless.**

---

## 1. Brand essence

| | |
|---|---|
| **Name** | Kukku |
| **What it is** | A private, local-first personal AI that runs on your Mac and answers on Telegram and a web dashboard. |
| **Personality** | Warm, calm, competent. A trusted companion — not a chatbot, not a robot. |
| **Feeling** | "It's mine, it's here, and it just works." |
| **Anti-patterns** | ❌ robot mascots · ❌ neon rainbow gradients · ❌ circuit-board/brain clichés · ❌ "AI sparkle" overload · ❌ cold sci-fi blue. |

The name *Kukku* is a nickname — affectionate, short, human. The brand leans into
that: **premium software with a warm heart.**

---

## 2. Taglines

Ten candidates, why each works, and the recommendation.

| # | Tagline | Why it works |
|---|---|---|
| 1 | **Local by design. Personal by default.** | Two-beat, symmetrical, ownable. States the two things nobody else says at once: it runs locally *and* it's yours. Reads like a Linear/Apple line. |
| 2 | **Always on. Always yours.** | Emotional and short. Pairs perfectly with the "presence dot" in the logo. Great for hero/app-store. |
| 3 | **The assistant that lives on your machine.** | Clearest one-liner for a cold audience — instantly explains local-first without jargon. |
| 4 | **Your files. Your Mac. Your assistant.** | Rule-of-three ownership triad; hammers privacy and the file-search superpower. |
| 5 | **A private AI that never leaves home.** | "Home" is warm; "never leaves" is the privacy promise in plain words. |
| 6 | **Talk to your laptop. It finally listens.** | Friendly, a little cheeky; leads with the Telegram/voice experience. |
| 7 | **Your second brain, on your first machine.** | Clever inversion; targets the notes/memory/"second-brain" crowd. |
| 8 | **The AI that works where your files live.** | Concrete differentiator vs. cloud chatbots — it's *next to your data*. |
| 9 | **Personal AI, without the cloud tax.** | Names the pain (privacy + cost of cloud AI) in a memorable phrase. |
| 10 | **Quietly brilliant. Entirely yours.** | Premium, understated, "timeless" register; great for a banner subhead. |

**Recommended:** **#1 — "Local by design. Personal by default."**
It is distinctive, non-generic, and carries the entire positioning (local-first +
personal) in six words. Use **#2 "Always on. Always yours."** as the short
emotional sibling for app icons, social, and the animated presence-dot moments.

---

## 3. Logo

### The concept — "The K and the presence dot"
A geometric **monoline K** with softly rounded joints (friendly, not sharp)
reaches up toward a single **warm apricot dot**. The dot is the signature: it
represents Kukku's *presence* — always there, attentive, one glance away. It is
the one element that is unmistakably Kukku.

**Why it works**
- **Ownable** — the reaching-K + dot is not a chat bubble, robot, or brain.
- **Scales** — a bold monoline stroke and one dot survive down to 16 px.
- **Systemic** — the dot detaches and lives on its own as a loading spinner,
  notification badge, favicon, and "listening" indicator.
- **Warm + premium** — indigo says *software you trust*; the apricot dot says
  *made for a human*.

### Assets (in `assets/brand/`)
| File | Use |
|---|---|
| `logo-mark.svg` | Primary app tile / mark (512, gradient squircle) |
| `logo-lockup.svg` | Horizontal mark + "Kukku" wordmark |
| `logo-monochrome.svg` | One-colour (`currentColor`) mark for any background |
| `favicon.svg` | Bolder mark tuned for 16–32 px |

### Clear space & sizing
- Clear space = the height of the dot on all sides.
- Minimum: mark 16 px; lockup 96 px wide.
- Never: recolour the tile arbitrarily, add shadows/bevels, rotate, stretch,
  outline the wordmark differently, or place the mark on a busy photo without the
  solid tile.

---

## 4. App icons

One mark, correct container per platform. Export from `logo-mark.svg`.

| Target | Spec |
|---|---|
| **macOS** | Squircle, Apple's superellipse mask, ~22% corner. Provide `.icns` at 16→1024. Keep a small margin — don't fill edge-to-edge. |
| **Windows** | `.ico` bundle 16/32/48/256, square with the same 24% rounded tile baked in. |
| **Android adaptive** | 108×108 dp: foreground = K + dot only (no tile), background = flat Iris `#5B4DE0`. Safe zone 66 dp. |
| **PWA / maskable** | 512 & 192 PNG + a maskable variant with 20% safe padding so Android circles don't clip the K. |
| **Favicon** | `favicon.svg` + 32/16 PNG fallback + `apple-touch-icon` 180. |
| **Social / avatar** | 512 tile, centered, used for GitHub org, npm, X, etc. |

---

## 5. Colour system

Refined, not neon. One confident hue (**Iris**) + one warm signal (**Apricot**),
on sophisticated neutrals. Warm accent = friendly; restrained palette = premium.

### Brand & semantic
| Token | Hex | Use |
|---|---|---|
| **Iris** (primary) | `#6A5AF9` | Primary actions, links, active nav, the tile |
| **Iris Deep** | `#5B4DE0` | Gradients, pressed states, Android bg |
| **Iris Top** | `#7A6BFF` | Top stop of the tile gradient only |
| **Apricot** (accent) | `#FF9E64` | The presence dot, highlights, "live" moments — sparingly |
| **Sage** (success) | `#3FB984` | Success, online, indexed |
| **Amber** (warning) | `#F5B34A` | Warnings, low battery/disk |
| **Rose** (danger) | `#F06A6A` | Errors, destructive, denied access |

### Dark theme (default)
| Role | Hex |
|---|---|
| Background | `#0B0B0F` |
| Surface | `#15151C` |
| Surface hover | `#1D1D26` |
| Border | `#26262F` |
| Border strong | `#33333F` |
| Text | `#ECECF2` |
| Text muted | `#9B9BA8` |
| Text faint | `#63636F` |

### Light theme
| Role | Hex |
|---|---|
| Background | `#FBFBFD` |
| Surface | `#FFFFFF` |
| Surface hover | `#F3F3F7` |
| Border | `#E7E7EC` |
| Border strong | `#D6D6DE` |
| Text | `#1A1A22` |
| Text muted | `#6C6C7A` |
| Text faint | `#9A9AA6` |

**Usage rules**
- One dominant hue per screen. Apricot is a *spice*, never a second theme.
- Gradients: only same-hue, 2-stop (`Iris Top → Iris Deep`). No hue-to-hue neon.
- Contrast: body text ≥ 4.5:1, large text ≥ 3:1, both themes.

---

## 6. Typography

| Role | Typeface | Why |
|---|---|---|
| **Display / headings** | **General Sans** (Fontshare, free) | Geometric-humanist with quiet personality — premium without shouting; distinct from the Inter-everywhere look. |
| **Body / UI** | **Inter** | The workhorse. Superb at small sizes, huge language coverage (incl. Devanagari via Inter/Noto). Already in the app — continuity. |
| **Code / metrics** | **JetBrains Mono** | Clear `0/O`, `1/l`; already used for the monitor rings and code. |

Alternative unified stack for a Vercel/Cursor register: **Geist + Geist Mono**.

**Scale (1.25 ratio):** 12 · 13.5 · 15 · 18 · 22 · 28 · 36 · 48.
Headings 600, `letter-spacing:-0.02em`. Body 400/500, `line-height:1.55`.

---

## 7. Design system

**Spacing (4 pt):** 4 · 8 · 12 · 16 · 20 · 24 · 32 · 48 · 64.
**Radius:** xs 8 · sm 10 · md 12 (cards) · lg 16 · xl 22 · pill 999. Tiles 26.
**Elevation (dark):**
- sm `0 1px 2px rgba(0,0,0,.4)`
- md `0 8px 24px rgba(0,0,0,.35)`
- lg `0 24px 60px rgba(0,0,0,.5)`
- glow (primary) `0 0 0 1px rgba(106,90,249,.4), 0 8px 30px rgba(106,90,249,.25)`

| Component | Spec |
|---|---|
| **Card** | Surface bg, 0.5px border, radius 12, padding 16–20, optional `glass` blur(18px). |
| **Button (primary)** | Iris fill, white text, radius 12, height 40, weight 600; hover lift 1px; focus = 2px Iris-soft ring. |
| **Button (ghost)** | Transparent, 1px border, muted text → text on hover. |
| **Input** | Surface bg, 1px border, radius 10, focus ring Iris-soft; placeholder = text-faint. |
| **Dialog** | Radius 16, lg shadow, scrim `rgba(0,0,0,.5)` + blur(2px); Esc + backdrop close. |
| **Table** | 13px, 0.5px row lines, sticky header on surface, hover row = surface-hover. |
| **Badge** | Pill, 11px/600, 2×8 padding, semantic tint at ~18% + solid text. |
| **Tag** | Pill, surface bg, 1px border, text-faint; active = Iris tint. |
| **Skeleton** | Surface-hover block, radius = element, shimmer 1.4s ease. |
| **Loading** | The **presence dot** pulses (opacity 0.4↔1, 1.2s) — reuse the brand, don't add spinners. |
| **Animation** | Durations 160/240/400 ms; ease `cubic-bezier(0.16,1,0.3,1)`. Respect `prefers-reduced-motion`. |

---

## 8. Icon library

**Lucide** — and it's already integrated in the dashboard.
- Consistent 1.5 px stroke matches the monoline logo.
- 1,400+ icons, MIT, tree-shakeable, first-class React.
- Rounded caps/joins echo the K's friendly joints.
Rules: 1.5–1.8 px stroke, size 16–20 in UI, never mix icon sets, decorative
icons get `aria-hidden`, meaningful ones get a label.

---

## 9. Product positioning

**What makes Kukku unique:** it's a *personal* AI that runs **on your machine**,
sees **your files**, remembers **your context**, and reaches you where you already
are (**Telegram** + a private dashboard) — free, private, and always on.

**Why use it:** find anything on your Mac by meaning, get answers and files on your
phone, keep a shared memory across devices — without shipping your data to a cloud.

**Audience:** developers, power users, privacy-minded professionals, and tinkerers
on macOS who live in their files and their terminal.

**Versus…**
| | How Kukku differs |
|---|---|
| **ChatGPT** | Runs locally, sees your files, remembers you, free — not a stateless cloud chat. |
| **Cursor** | Cursor lives in the editor for code; Kukku lives across your *whole machine and phone* for life + files. |
| **Raycast** | Raycast is a launcher; Kukku is a conversational assistant with memory, OCR, voice, and a bot you carry in your pocket. |
| **Telegram bots** | Most are thin cloud wrappers; Kukku is a full local brain that *happens* to answer on Telegram. |
| **Cloud "personal AI"** | Kukku keeps data on your Mac, works on free model tiers, and is fully self-hosted and open-source. |

---

## 10. Marketing copy

- **GitHub description (≤120 chars):**
  *Private, local-first personal AI for your Mac — answers on Telegram + a web dashboard. Files, OCR, voice, memory.*
- **GitHub topics:** `personal-ai` · `local-first` · `privacy` · `telegram-bot` · `macos` · `ai-assistant` · `semantic-search` · `self-hosted` · `nextjs` · `fastapi` · `rag` · `ocr`
- **Short (1 line):** Your private, local-first AI assistant — on your Mac, answering on Telegram and the web.
- **Elevator pitch:** Kukku is a personal AI that lives on your Mac. It finds your files by meaning, reads your screenshots, transcribes your voice notes, remembers what matters, and answers you on Telegram or a private dashboard — all locally, on free model tiers, fully yours.
- **30-second pitch:** Cloud assistants can't see your files and won't keep your data private. Kukku runs on your own machine: ask it in plain language — on Telegram from your phone or a beautiful local dashboard — and it searches your laptop by *meaning*, reads text inside screenshots, transcribes voice notes, runs safe local commands, and remembers context across both. It fails over across free LLM providers, so it's genuinely free, and every byte stays on your Mac. One brain, two front doors, zero cloud tax.
- **Long description:** *(the hero README — now adopted as the root [`README.md`](../../README.md).)*

---

## 11. Screenshots plan

Shoot at 1440×900, dark theme, seeded with realistic-but-clean data, cursor
hidden, consistent window chrome. Priority order:

1. **Chat (hero)** — a streaming reply mid-flight, provider badge visible, one
   Hinglish message to show range. *The money shot.*
2. **System Monitor** — CPU/RAM/DISK rings + provider metrics. Most visually
   striking; great for the social preview.
3. **Universal Search** — one query, mixed results (files + OCR + memory).
4. **Memory** — the "second brain" list with aliases.
5. **File Explorer / OCR** — "find the screenshot where Docker failed."
6. **Developer** — live activity feed + log tail (credibility for devs).
7. **Mobile drawer** — the responsive dashboard on a phone frame (proves polish).

Store in `docs/images/`. Wrap each in a rounded 12px frame with a subtle Iris glow.

---

## 12. 60-second demo (scene by scene)

| t | Scene | On screen | Voice/caption |
|---|---|---|---|
| 0–5s | **Cold open** | Kukku mark; the presence dot pulses, then "Local by design. Personal by default." | "Meet Kukku." |
| 5–14s | **Ask from your phone** | Telegram: *"send me my resume"* → file arrives. | "Ask in plain language, from anywhere." |
| 14–24s | **Search by meaning** | Dashboard Search: *"the screenshot where Docker failed"* → OCR hit. | "It finds things by meaning — even text inside images." |
| 24–34s | **Voice + Hinglish** | Voice note *"aaj ka weather batao"* → reply in Hinglish. | "Talk to it. In your language." |
| 34–42s | **Memory** | *"remember I prefer window seats"* → Memory panel updates. | "It remembers what matters." |
| 42–50s | **Live sync** | Telegram message appears instantly in the dashboard. | "One brain. Every device." |
| 50–57s | **Local & private** | Monitor: everything on `127.0.0.1`, providers all free-tier. | "All on your Mac. Nothing in the cloud." |
| 57–60s | **Close** | Mark + `github.com/manishsinghks/Kukku` + "Always on. Always yours." | — |

Format: 1920×1080, 30fps, captioned (silent-friendly), Iris/apricot accents only.

---

## 13. Banners & social

| Asset | Size | Composition |
|---|---|---|
| **GitHub social preview** | 1280×640 | Left: mark + "Kukku" + tagline; right: floating dashboard screenshot at a slight angle. Dark `#0B0B0F` bg, one soft Iris glow bottom-left. |
| **Repo cover / hero** | 1600×500 | Centered lockup + tagline + one-line value prop + three tiny feature chips. |
| **Open Graph** | 1200×630 | Same as social preview, safe margins 80px, text ≥ 40px. |
| **X / Twitter** | 1600×900 | Screenshot-forward variant; mark in a corner, tagline as caption. |

Keep 60% negative space. Never crowd. One glow, never two.

---

## 14. Brand guidelines — do / don't

**Do:** keep one dominant hue per surface · let the presence dot carry the brand ·
use generous whitespace · animate with restraint · write plainly and warmly.

**Don't:** add robot/brain/sparkle clichés · stack multiple neon gradients ·
recolour or bevel the mark · use pure black `#000` or pure white surfaces in dark
mode · let apricot become a second theme · use drop shadows on the logo.

**Voice:** confident, warm, concrete. Short sentences. "Your Mac," "your files,"
"yours." Never salesy, never robotic. A calm expert who happens to be a friend.
