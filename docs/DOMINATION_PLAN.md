# vodfetch — Domination Plan (data-driven, batch-by-batch)

_Last updated: 2026-07-06 · Source: Ubersuggest exports (alle_kategorien / suchmaschinen / ki-modellen, "twitch downloader", en-US) + DE coverage-gap export._
_Execution languages for all NEW content: **EN (canonical) + DE + FR + ES**. Other languages EN-fallback (per owner: "es reicht, wenn wir das in EN, DE, FR, ES machen")._

---

## 0) How to use this file
Each batch below is **independently executable**. Standard per-batch flow (established pattern):
1. Author EN content into `_blog.py` / `_landing.py` (+ wire `BLOG_TO_LANDING` / `LANDING_TO_BLOGS`).
2. Validate EN (JSON-LD single @graph, meta 40–160, no heading jumps, links).
3. Translate to **DE/FR/ES** via a Workflow → `html.unescape` → merge (EN fallback for the other 10 langs).
4. Validate all langs → `build_static.py` → secret grep → deploy → verify live → `submit_indexnow.py` → commit.
Then move to the next batch. After 1–2 batches, watch GSC coverage/performance.

---

## 1) What the data says (analysis)

### A. Search engines (Google/Bing/YouTube, en-US volumes)
The money terms and their signals:

| Keyword | Vol | Note |
|---|---|---|
| twitch downloader | **12.1K** | head term (CPC $1.32) — owned by tool sites; our home targets it |
| twitch clip downloader | **5.4K (YT)** | huge on YouTube; we have `/twitch-clip-downloader` |
| twitch downloader video / twitch video downloader | **3.6K** | **CPC $3.62** (highest commercial value); we have `/twitch-video-downloader` |
| twitch chat downloader | **1.9K** | we have `/twitch-chat-downloader` |
| twitch vod downloader **extension** | **1.3K** | ⚠️ big intent we do NOT address (we removed our extension) |
| twitch downloader **mac** | **390** | ⚠️ only a combined mac+windows blog; no dedicated Mac page |
| twitchdownloader (IG hashtag) | 720 | social |
| twitch downloader app | 260 | mobile/app intent |
| twitch downloader vod | 260 | covered |
| twitch downloader clip | 170 | covered |
| twitch clip downloader mp4 | 140 | covered |
| twitch downloader **online** | 110 | web-tool intent — optimize existing |
| twitch vod downloader **mobile** | 90 | covered (iphone/android post) |
| twitch vod downloader **not working** | 50 (+ many error variants) | ⚠️ troubleshooting cluster — uncovered |
| is twitch downloader **safe** | (low but AI-echoed) | ⚠️ trust/safety — uncovered, and a perfect USP fit |
| free twitch downloader | 30 (CPC $0.76) | optimize existing |
| github / cli / gui / streamfab | 30–70 | dev intent → our `/compare` handles it |

Troubleshooting long-tail (all uncovered, collectively meaningful): `not working`, `no audio`, `not loading`, `unable to get video information`, `error 530`, `not showing full vod`, `doesn't work firefox`.

### B. AI models (ChatGPT / Gemini) — the AEO goldmine
The prompts people actually ask AI:
- "Best software to download Twitch streams quickly" / "best free tools for saving Twitch streams"
- "How to save Twitch videos offline on PC" / "…to my computer"
- "How to download Twitch videos on **Mac without software**"
- "**Is it safe** to use third-party applications for Twitch downloads"
- "How to download Twitch streams **without losing quality**"
- "Steps to download a Twitch stream **without a creator subscription**"
- "Can I download **Twitch chat along with** the video"
- "Comparison of Twitch downloader tools for **quality and speed**"
- "Apps for downloading Twitch VODs on **mobile**" / "Best **browser extensions**"
- "Is it **legal** to download Twitch streams for personal use"

**Brands the AI models currently name:** TwitchDownloader, Eklipse (Twitch VOD & Clip Downloader), StreamFab, Untwitch, VOD Saver, Video Downloader for Twitch. **vodfetch is NOT in the set.** Sentiment for the category is 80–100% positive → AI is happy to recommend Twitch downloaders; getting vodfetch cited is a pure **entity/citation** problem, not a safety-refusal problem. This is the #1 AEO objective.

### C. Coverage map — what we ALREADY own (do not duplicate)
- **Landings (9):** clip, vod, video, stream, to-mp3, clip-to-gif, chat, channel, vod-chapters.
- **Blog (19):** obs-vs-downloader, save-vod-without-obs, copyright(UrhG/DSGVO), vod-vs-youtube, repurpose-to-youtube, best-downloader, vod-with-chat, vod-1080p60, vod-before-deleted, clips-no-watermark, record-live, entire-channel, convert-to-mp4, iphone-android, clips-for-tiktok-shorts, highlights, extract-audio-mp3, mac-and-windows, is-it-legal.
- Much of the DE "Nicht abgedeckt" export is **already covered by recent work** (obs-vs, best-downloader, copyright, chat, mp3, before-deleted, youtube-repurpose) — the tool just hasn't re-crawled the new domain yet.

### D. The genuine gaps (prioritized)
1. **Extension intent** (1.3K) — uncovered, and we deliberately have no extension → capture the query honestly, convert to browser tool.
2. **Safety / "is it safe"** — uncovered; strongest USP fit (open-source, no account, no install, no watermark).
3. **Troubleshooting / "not working"** (50 + variants) — uncovered; helpful, converts frustrated users.
4. **Mac** (390) — no dedicated page.
5. **AEO citation gap** — vodfetch not named by ChatGPT/Gemini; fix via prompt-matched content + entity signals.
6. **"Online/free/app" modifiers** — optimize existing landings rather than new thin pages.

---

## 2) The batches

### 🅑 BATCH 1 — Trust & Troubleshooting (highest un-owned intent + AEO)
| # | Slug | Type | Target keyword(s) | Angle |
|---|---|---|---|---|
| 1.1 | `is-twitch-downloader-safe` | blog | "is twitch downloader safe" + AI "is it safe to use third-party apps" | Honest safety guide: what makes a downloader risky (fake buttons, permissions, malware, watermarks), why a client-side open-source browser tool is the low-risk option, a checklist. USP-perfect. |
| 1.2 | `twitch-downloader-not-working` | blog | "twitch vod downloader not working" (50) + no-audio/not-loading/error/firefox variants | Troubleshooting guide: common causes + fixes (sub-only/expired VOD, browser, ad-block, quality), and how a browser tool avoids the desktop-app failure modes. |
| 1.3 | `twitch-downloader-extension-vs-browser-tool` | blog | "twitch vod downloader extension" (1.3K) + "chrome extension" + AI "best browser extensions" | Honest comparison: extension permissions/risk vs a no-install browser tool; captures the big extension query, converts to us. |

### 🅑 BATCH 2 — Platform & beginner (device modifiers + AI prompts)
| # | Slug | Type | Target | Angle |
|---|---|---|---|---|
| 2.1 | `twitch-downloader-mac` | **landing** (embeds tool) | "twitch downloader mac" (390) + AI "on Mac without software" | Mac-specific: works in Safari/Chrome on macOS, no app, Apple-silicon fine, streams to disk. |
| 2.2 | `how-to-use-a-twitch-downloader` | blog | "how to use twitch downloader" / "what is twitch vod downloader" + AI "step-by-step" | Beginner end-to-end walkthrough (VOD, clip, live, chat, audio) — a hub that links every landing; strong internal-linking + AEO. |
| 2.3 | `download-twitch-best-quality` | blog (or merge into vod-1080p60) | AI "without losing quality" + "1080p60/4k/hd" | Source vs re-encode, how to guarantee original quality. Evaluate overlap with `download-twitch-vod-1080p60`; **merge if too close.** |

### 🅑 BATCH 3 — AEO domination (get cited by ChatGPT/Gemini)
| # | Item | What |
|---|---|---|
| 3.1 | AI-FAQ block | Add a "Common AI questions, answered" section (HTML + `/llms.txt` + `/facts`) that answers the exact top prompts (best free tool, save offline on PC, Mac without software, is it safe, without a subscription, chat with video, without losing quality, quality-and-speed comparison) with vodfetch as a **factual** answer. |
| 3.2 | Comparison framing | Ensure `best-twitch-downloader` + `/compare` answer "comparison for **quality and speed**" and "best free" prompts (add explicit speed/quality/free framing). |
| 3.3 | Entity signals | Reinforce so AI models start naming vodfetch alongside TwitchDownloader/Eklipse/StreamFab/Untwitch: tighten `grounding`/`facts`/`dear-ai` "one-line answer", add the competitor set to comparison context. |

### 🅑 BATCH 4 — On-page & internal-linking polish
- Optimize titles/meta/copy of existing landings for high-value modifiers where data shows volume: **video (3.6K, CPC $3.62), online (110), free, app (260), mac (390)**.
- Wire every new Batch-1/2 piece into `BLOG_TO_LANDING` / `LANDING_TO_BLOGS` and the relevant landing "related guides".
- Re-run the link-graph + on-page audits (scripts in scratchpad) to keep 0 orphans / 0 heading jumps / 0 broken links.

---

## 3) Prioritization rationale
- **Batch 1 first**: biggest uncovered intent (extension 1.3K), the trust angle that is our sharpest differentiator, and the troubleshooting cluster that converts frustrated users — all three double as AEO answers.
- **Batch 3 (AEO)** is arguably the highest strategic value (AI models don't name us yet) but depends partly on Batch-1 content existing to point to — do it right after Batch 1, or interleave.
- **Off-page remains the real indexing lever** (new-domain crawl budget): backlinks (Medium article live, + Product Hunt / Reddit / AlternativeTo / Show HN) + GSC "request indexing" for money pages. Content batches feed the pages; off-page gets them crawled.

## 4) Guardrails (unchanged)
- Honest per the editorial policy: no fabricated claims, no fake ratings/reviews, legal/safety content clearly caveated.
- Every piece: single JSON-LD @graph, HowTo/FAQ where apt, founder byline, no heading skips, .md mirror, hreflang, sitemap, IndexNow.
- New content = EN + DE + FR + ES (others EN-fallback).

## 5) Status log (update as batches ship)
- [x] **Batch 1 — Trust & Troubleshooting** (shipped 2026-07-06): 3 blog posts, EN+DE+FR+ES — `is-twitch-downloader-safe` (safety/malware/permissions checklist), `twitch-downloader-not-working` (troubleshooting: unable-to-get-info / no-audio / Firefox / partial-VOD), `twitch-downloader-extension-vs-browser-tool` (captures the 1.3K "extension" intent, converts to no-install tool). All honest, JSON-LD/HowTo/FAQ, wired into internal-linking maps. Live, IndexNow 842 URLs.
- [x] **Batch 2 — Platform & beginner** (shipped 2026-07-06): new landing `/twitch-downloader-mac` (390 vol + AI "Mac without software"; embeds the full tool, macOS/Safari/Chrome/Apple-silicon copy, QuickTime/Final Cut import) + new blog `/blog/how-to-use-a-twitch-downloader` (beginner hub: what a downloader is, the paste-a-link flow, VOD/clip/live/audio/chat, quality). EN+DE+FR+ES. `download-twitch-vods-on-mac-and-windows` repointed to the Mac landing. **2.3 (best-quality post) deliberately skipped** — near-total overlap with `download-twitch-vod-1080p60` + the FAQ answer (plan's own "merge if too close"). Live, IndexNow 870 URLs.
- [x] **Batch 3 — AEO domination** (shipped 2026-07-06): new `/twitch-downloader-faq` hub (18 Q&As in 5 categories, EN+DE+FR+ES, FAQPage schema, answers the exact ChatGPT/Gemini prompts) + machine-file enhancements (llms.txt "Best free / Is it safe / vs others" quick answers naming the competitor set; FAQ hub added to llms/dear-ai/ai.json/_ai_resources; grounding "Alternatives" fact naming TwitchDownloader/Untwitch/clipr/StreamFab/Eklipse/VOD Saver). Live, 800 URLs to IndexNow.
- [x] **Batch 4 — On-page & internal-linking polish** (shipped 2026-07-06): full audit of the grown 870-page site (74.9k internal links: 0 broken / 0 trailing-slash / 0 noindex / 0 orphans / 0 dead-ends / 0 dupe titles / schema clean). A 5-agent adversarial workflow adjudicated the candidates → shipped: (A) in-content link to the AEO FAQ hub from every language home page + the 5 most-relevant trust/how-to blog posts (FAQ hub went from footer-only → strong in-content inbound, the top AEO lever); (B) dropped the redundant " | Twitch Downloader" suffix from the /alternatives index title (67→47 chars, no truncation, zero translation). REJECTED as busywork: retranslating the twitch-channel-downloader title for 3 chars, and forcing modifiers into already-optimized landing titles. Live, IndexNow.

**All four batches complete.** On-page/AEO is now maxed; the remaining lever is off-page (backlinks + GSC request-indexing + time on the new domain).
