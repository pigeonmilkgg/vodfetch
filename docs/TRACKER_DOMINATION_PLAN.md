# vodfetch — TRACKER Domination Plan (stats/tracker expansion)

_Created: 2026-07-06 · Sources: 5 Ubersuggest exports of twitchtracker.com (US/DE/UK) + sullygnome.com (US/DE) in `/Users/alex_memberspot/Downloads/TWITCH TRACKER/`, live competitor teardowns (twitchtracker, sullygnome, streamscharts, twitchmetrics, twitchstats, livecounts, twitchtools), Semrush domain data (US), and a code-level feasibility audit of this repo._
_This file extends `DOMINATION_PLAN.md` (Batches 1–5, all shipped). Tracker batches are numbered **T0–T6** to avoid collision. Same execution rules: new content EN (canonical) + DE + FR + ES, EN-fallback for the other 10; per-batch pipeline per DOMINATION_PLAN §0._

---

## 0) The thesis in one paragraph

TwitchTracker & SullyGnome own "all things Twitch stats" with one asset we can never buy: **a decade of minutes-level polling history**. But the recon shows their traffic splits into (a) history-dependent pages we must NOT fake, and (b) a large, soft slice — live lookups, records, rankings snapshots, chat logs, clip browsing, download-adjacent intent — that needs **no history at all** and that they serve badly or not at all. They are also structurally locked out of the answer-engine era: Cloudflare-403 AI crawlers on their richest pages, AJAX-invisible tables, zero JSON-LD, English-only, no open data, **and no download buttons anywhere**. Our play: ship the honest no-history slice as client-side tools + evergreen facts pages (our exact architecture), make every stats surface end in a download CTA (the one action no competitor offers), extend the machine-file suite so AI engines cite *us* for Twitch facts — and **start collecting our own history today**, so that in 6–12 months we can honestly contest "tracker" semantics with "since 2026" data. Compete on **citability now, history later**.

---

## 1) What the data says

### A. The market (Semrush, US)

| Domain | Organic traffic/mo | AS | Traffic architecture |
|---|---|---|---|
| twitchtracker.com | 216,283 (47.4K kws) | 61 | **HUB site:** home 35.8% + /subscribers 19.6% (42.5K!) + /statistics 9.8% + /channels/* 7.2% ≈ 73% on a handful of URLs; streamer profiles ~25%; /games/* only 1.9% |
| streamscharts.com | 197,276 (~175K clean; 11.5% is one adult-name outlier) | 54 | **PROGRAMMATIC site:** /channels/* profiles = 70.8% across 33K kws; /tools/* = 4.8% (9.5K/mo — the stats→tools bridge, proven) |
| sullygnome.com | 18,194 (6.7K kws) | 40 | **The failure mode:** 69.6% homepage; page-1 on the same head terms as TT yet **12× less traffic** — long tail without authority doesn't convert (1,894 /channel kws → 2,879 visits/mo) |

Validated head volumes (US): "twitch tracker" 40,500 · "twitch stats" 18,100 · "twitch sub count" 12,100 · "twitch statistics" 9,900 · "top twitch streamers" 6,600 · "twitch analytics" 2,900. Whole niche ≈ $0 CPC — a stats layer buys **audience and entity authority**, not ad-market value. The audience's money moment is the download — which is our product.

**Lesson:** a weeks-old ~900-URL domain cannot play the programmatic game yet (that archetype pays at tens of thousands of indexed pages + AS 50+). Hub/tool/facts pages win with a single URL each. Sequence accordingly.

### B. The five keyword exports (clusters, total volume)

**twitchtracker US (5,000 rows):** streamer entity 871K · game stats 338K · steam charts/player counts 276K (Steam intent!) · subs 120K · per-streamer clips 108K · stats head terms 93K · bio (age/height) 70K · games directory 64K · rankings 61K · records/peak viewers 37K (one competitor URL) · follower checkers 29K · net worth 18K · **VOD/download funnel 6.6K**.

**twitchtracker DE (1,648 rows):** entity 318K · streams-history/"Archiv" 80K · rankings 77K · stats head 75K · subs 75K · clips 47K · **"twitch clips download" family 5,200 — TT ranks pos 17–53 with pages that cannot download anything**.

**twitchtracker UK (1,780 rows):** entity 173K · steam charts 78K · game stats 55K · **chat logs: "logs twitch" 880 + "chat log(s) twitch" 2×720 at SD 24–30, TT ranks top-10 by accident with no log tool**.

**sullygnome US (2,181 rows):** entity 115K · games directory 65K · **teams/"streamer communities" 57K (single keyword "streamer communities" = 40,500 @ SD 35, SG pos 26)** · rankings 51K · game pages 47K · subs 43K · follower/followage 22.5K @ SD 16–40 · username/channel search 6.8K @ SD 16–24 · Partner how-to 5.1K (SG answers with a data table, pos 25–33).

**sullygnome DE (244 rows):** stats head 17K · sub/follower tools 17K · entity 12K · **Twitch Recap 7,770 @ SD 26–33 (SG ranks via an accidentally-named category)** · chat logs/logger 3.3K · German rankings 1.4K. Zero download-intent keywords — SG's traffic is pure stats.

### C. Competitor blind spots (verified, exploitable)

1. **No downloads anywhere.** Every incumbent lists VODs/clips but only links to twitch.tv. Meanwhile they *rank* for download intent: "twitch clip(s) download" 1,760 US + 5,200 DE (TT pos 17–53), "twitch archive" 720 (TT pos 7 on /clips), "twitch logger" 5,400 US (TT pos 4). Bottom-of-funnel traffic served by pages that cannot act.
2. **AEO vacuum.** TT/streamscharts/twitchstats serve Cloudflare 403s to AI fetchers on their crown-jewel pages; SG's tables render as AJAX "Loading…" (invisible to crawlers/LLMs); no JSON-LD, no llms.txt, no .md mirrors, no licensed data exports anywhere. Our machine-file suite has zero competition in this niche.
3. **English-only, all of them.** All "[lang] twitch stats/rankings" demand (DE/FR/ES) is served in the wrong language. We ship 14 languages.
4. **No honesty/methodology layer.** Sub counts full of "?" cells and undisclosed error bars; SG's methodology page is why researchers cite it — nobody else has one.
5. **Dated, ad-heavy UX** vs our system-font, zero-tracker, fast static pages.
6. livecounts.io proves a **zero-backend live counter** works as a product; streamscharts' /tools/ subfolder (9.5K/mo) proves the **stats↔tools bridge** carries real traffic. We build the bridge from the tools side — with the stronger tool.

### D. Technical ground truth (verified in code + live on 2026-07-06)

- **`gql.twitch.tv` serves `Access-Control-Allow-Origin: *`** — client-side stats queries run DIRECT from the visitor's browser with the public client-id: **zero proxy invocations, zero shared-IP rate-limit coupling, zero secrets.** Verified live: `user(login){followers{totalCount}}` (shroud → 11,299,959), `game(name){viewersCount, streams(sort:VIEWER_COUNT)}` (Fortnite → 33K viewers + box art + top streams).
- The client JS already ships most building blocks: channel browse (profile, partner status, 24 recent VODs paginated, top clips ALL_TIME), live-status detection, VOD metadata + chapters, clip metadata, cursor-paginated chat export.
- **The proxy (`tw.js`) is currently an open Twitch proxy** (ACAO:* with no Origin/Referer check) — must be hardened before we raise the site's profile.
- Build-time programmatic pages need the **official Helix API** (client-credentials app token = the project's **first real secret**; lives in local untracked `.env` next to the existing TWITCHDL_* vars — no CI exists, so no CI secret problem). 800 points/min ⇒ a full top-1000-streamers + top-500-games snapshot ≈ 2–4 min of API time.
- **History** = GitHub Actions cron (6–12h) → Helix → compact daily JSON rollups committed under `data/` — decoupled from deploys, public, versioned, ~MBs/year. GH cron is best-effort and auto-disables after 60 days of repo inactivity → needs self-monitoring.
- Honesty rule collision to respect everywhere: **never pre-render volatile numbers as "live"** — every static stat carries a visible as-of timestamp; live numbers only via client-side fetch.

---

## 2) The batches

### 🅣 BATCH T0 — Infrastructure prerequisites (do first; mostly S, flywheel M)
| # | Item | What / why |
|---|---|---|
| T0.1 | **Harden `tw.js`** | Add Origin/Referer allowlist (vodfetch.com + netlify.app preview). It is an open Twitch proxy today; a higher-profile stats product increases abuse discovery. All NEW stats GQL goes direct to gql.twitch.tv (CORS-open, verified) — proxy stays for media hosts only. |
| T0.2 | **Twitch dev app + Helix secret** | Register app; client-id/secret → local untracked `.env`. Keep the mandatory pre-deploy secret-grep over `dist/`. Unblocks T4/T5 build-time snapshots + T0.4. |
| T0.3 | **`scripts/deploy.sh`** | Encode the canonical build+deploy+IndexNow one-liner (documented regression trap: dropped Bing verify/sameAs, wrong IndexNow host). Must exist before any cron/CI ever touches deploys. |
| T0.4 | **START THE HISTORY FLYWHEEL** | GitHub Actions cron every 6–12h → Helix (top 500 games, top ~1000 streams overall + per DE/FR/ES/EN, follower totals for the curated T5 roster) → daily JSON rollups committed to `data/`. **Decoupled from deploys — no pages consume it yet.** Self-monitoring freshness check + failure notification. Rationale: the incumbents' only real moat is history; SullyGnome started Aug 2015; every week of delay is a week less of "since 2026" depth. The clock starts when collection starts. |

### 🅣 BATCH T1 — Zero-engineering content wins (all S; existing features + blog machine)
| # | Slug | Type | Target / evidence |
|---|---|---|---|
| T1.1 | `twitch-chat-log` | **landing** (fronts the EXISTING chat→.txt export) | Best keyword-to-existing-feature match in all 5 exports: UK "logs twitch" 880 + "chat log(s) twitch" 2×720 (SD 24–30); DE "twitch logger" 880 + "twitch logs/log" 3×720; US "twitch logger" 5,400 (TT pos 4, by accident). Copy honestly scoped: per-VOD chat replay export, NOT justlog-style cross-channel user logs. Cross-link with `/twitch-chat-downloader` (distinct intent framing to avoid cannibalization). |
| T1.2 | `twitch-username-checker` | **micro-tool page** | "twitch username check(er)" 1,300–1,890 @ SD 16–18, incumbents pos 29–43 via homepages — the cheapest SERP in all five exports. One `user(login)` GQL call. Becomes the search box feeding T2/T5. Copy caveat: missing user ≠ guaranteed claimable. |
| T1.3 | Watch-past/deleted-streams **hub consolidation** | blog upgrade | 6,570-vol US funnel cluster ("how to watch past streams on twitch" 390, "twitch vod finder" 170, "twitch archive" 720+340) where TT ranks pos 7–40 with pages that can't answer. Expand the existing before-deleted guide into the canonical hub; hard links into `/twitch-vod-downloader`. |
| T1.4 | `how-to-become-twitch-partner` + `how-to-raid-on-twitch` | blog ×2 | 5,110 + 1,900 vol; SG ranks pos 20–33 with data tables that never answer the question. Pure existing blog format. |
| T1.5 | `twitch-recap-how-to-see-and-save` | blog (**publish by November**) | 7,770-vol DE cluster @ SD 26–33, won accidentally by an SG category named "Twitch Recap". Seasonal Jan/Feb spike. Honest scope: view your Recap + save your favorite streamer's highlights with the downloader (NOT "download the Recap itself"). |
| T1.6 | Clip landing copy pass | on-page | Work "clip search"/"clips manager" phrasing into H2s/FAQ of `/twitch-clip-downloader` now (1,900 combined vol, TT pos 4–5 with a weak page) — accrues relevance ahead of T2.2. |
| T1.7 | Seed machine files with record facts | AEO | Add sourced Twitch records (most-viewed stream, peak concurrent, announced sub record) to facts.json/grounding/llms.txt before the T3 page even ships. Announce the upcoming stats section + methodology URL in llms.txt/dear-ai/ai.json on day one. |

### 🅣 BATCH T2 — Client-side live tools (M; direct GQL, zero infra, zero secrets)
| # | Slug | What / evidence |
|---|---|---|
| T2.1 | `twitch-follower-count` | Type a channel → live follower total, avatar, partner status, account age, live status, **followage calculator**; optional auto-refresh counter mode (livecounts pattern). Rendered as an extractable answer sentence: "As of {timestamp}, {name} has {n} followers." Per-result CTA: "Browse & download {name}'s VODs and clips." Most winnable tool cluster in the recon: US 22,540 vol @ SD 16–40 (incumbents pos 12–43) + ~8–10K TT US + DE 4,460 + UK ~1,170. Follower totals are genuinely public — 100% honest, unlike sub counts. Copy rule: "live count, checked now" — never "tracking over time" until T6. |
| T2.2 | Clip **search & manager** upgrade | Extend `/twitch-clip-downloader` into a clip browser: channel → top clips by LAST_DAY/WEEK/MONTH/ALL_TIME (same `criteria` arg as the shipped ALL_TIME query — **test period variants before shipping copy**), plus a global "top Twitch clips today/this week" section. Every row = watch + one-click download. Targets "twitch clip search" 1,180 + "clips manager" 720 + the download-intent keywords that are literally our product ("twitch clip(s) download" 1,760 US / 5,200 DE, TT stuck pos 17–53). One page, expanded — no separate URL unless GSC shows the need. |

### 🅣 BATCH T3 — Facts, records & transparency layer (M; the AEO/citation play)
| # | Slug | What / evidence |
|---|---|---|
| T3.1 | `twitch-records` (+ DE „Twitch Zuschauer-Rekorde") | Evergreen sourced facts hub: most-viewed stream ever, peak-concurrent table, longest streams, announced sub/follower records. Every fact: source link + as-of date. FAQPage JSON-LD, .md mirror, facts wired into facts.json/grounding. 37,130-vol US cluster concentrated on ONE competitor URL (/channels/peak-viewers); "streaming record" alone 22,200 @ $5.08 CPC; records are stable facts — perfect for a no-database static site, and the niche's press/AI-citation magnet. Quarterly review checklist (a stale record = honesty failure). |
| T3.2 | Sub-count truth hub | Pair: "Twitch sub counts explained — why every tracker shows estimates" (why Twitch hides subs, how gifted-sub inference works, incumbents' own "?"-cells/error disclaimers) + sourced "most-subbed streamers of all time" records list (announced records only). Honest capture of the informational tail ("how many subs does kai cenat have" 2×2,400) of a 120K-vol US cluster we structurally refuse to serve as a leaderboard. **Never publish our own estimates.** |
| T3.3 | `methodology` / transparency page | What we snapshot, when, from which API, known error sources — and what we **refuse** to publish and why (sub estimates, history we didn't collect, net worth). Methodology transparency is the citation currency of this niche (it's why researchers cite SG). Converts the incumbents' data-honesty gaps into our trust fuel. |
| T3.4 | `/data/` open datasets | Deploy-time snapshots (top-500 streamers by followers, top-200 games by viewers) as CSV + JSON, schema.org Dataset JSON-LD, explicit reuse license, stable URLs, as-of stamps. The niche has NO free machine-readable data (SG's CSVs are crawl-blocked + unlicensed; only paid APIs exist). Licensed open data = the path of least resistance for AI engines, journalists, and backlinks — the off-page lever the project currently lacks. |

### 🅣 BATCH T4 — Rankings & the German flank (M; deploy-time snapshots + one live page)
| # | Slug | What / evidence |
|---|---|---|
| T4.1 | `most-followed-twitch-streamers` | Top-100 by follower count, rebuilt each deploy (Helix snapshot, minutes of API time), prominent as-of stamp, ItemList JSON-LD, CSV twin in /data. Framed strictly as "most followed" — never "most watched" (that needs watch-time history we don't have). US rankings ~61K + follower cluster 29K; long-tail + AEO play, not a head-term assault (TT holds 113 top-3 positions there). |
| T4.2 | DE ranking pair: „Die größten Twitch-Streamer Deutschlands" (listicle) + „Top deutsche Streamer — live" | ~14K/mo German ranking volume ("deutsche streamer" 6,600 @ SD 31, "twitcher deutsch" 2,400, "deutsche streamerinnen" 880 @ SD 23) + SG's 1,420-vol DE listicle cluster (SG stuck pos 25–56). Live page: client-side GQL streams(language=de) sorted by viewers, timestamped. **Every competitor is English-only — the entire non-EN ranking demand is uncontested.** FR/ES twins only after DE shows indexation. |
| T4.3 | `twitch-top-games` | ONE page: "Top games on Twitch right now" — pre-rendered top-50 shell (deploy snapshot, as-of stamp) + client-side live refresh (verified GQL). Each row: "download VODs/clips of top {game} streamers" CTA. 64,290-vol US cluster sits on a single competitor URL; SG holds pos 1 on generic "trending games" (1,900, $0.95) with a plain table. **Explicitly NO per-game page factory** — the /game/* archetype is the weakest in the niche at every incumbent (TT 1.9% of traffic from 5,380 kws). |
| T4.4 | `streamer-communities-twitch-teams` guide | One definitive editorial guide (what teams are, how to find/join a community) with live team-roster examples via Helix Get Teams. "streamer communities" = 40,500 vol @ SD 35 (largest single-keyword prize in any export, SG pos 26) + ~16K team long tail. Intent is fuzzy (Discord vs Twitch teams — cover both meanings); one page is the right-sized bet, NOT a /team/* page factory (SG's earns 2.2% of its traffic). |

### 🅣 BATCH T5 — Entity pilot: `/streamer/{login}` (L; the seed of the only archetype that can 10× the site)
- **Exactly 50–150 curated pages** at launch. Roster selected by **archive/VOD/clip-intent evidence**, not bare-name head queries: gronkh ("gronkh archiv" 780 DE), jerma ("jerma stream archive" 320 + "jerma logs" 140), wubby (720), staiy ("staiy vod" 480), lacari ("lacari vod" 210), caseoh, pokimane… plus recon names (jynxzi, cinna, caedrel, properpeach…).
- Each page: pre-rendered SEO shell (name, avatar, partner status, created date, follower snapshot + as-of stamp, **unique curated FAQ prose** — SG's one good AEO pattern; thin API-field-only pages are the failure mode) + client-hydrated live status/viewers, recent VODs **with download buttons**, top-clips gallery **with download buttons** (T2.2 component), recently-played games from VOD metadata, "usually streams" schedule module. ProfilePage/Person JSON-LD in the @graph, .md mirror.
- **Language-matched, not hreflang-parity:** "gronkh archiv" is a German query, "wubby stream archive" an English one — one language per streamer page (EN + native where warranted), no ×4 multiplication of the indexation burden.
- Why: streamer entity + streams-history + clips clusters sum to **>700K vol US / >445K DE / >235K UK** with incumbents at pos 6–36 and SD mostly 24–42; the /{streamer}/streams pattern is literally "find past broadcasts" — we answer it better by adding the download. But Semrush proves the archetype only pays at scale we can't index yet → **pilot at survivable scale, expansion gated on GSC evidence (>70% of pilot indexed before adding names).**
- Data: build-time Helix snapshot for shells (official API for anything systematic — ToS posture; unofficial GQL stays user-initiated only, mirroring the downloader); client-side GQL for everything volatile.

### 🅣 BATCH T6 — "Since 2026": the history-powered layer (**gated on T0.4 reaching 3–6 months of clean data**; ~2027)
- First honest history pages: **follower-growth leaderboards** ("fastest growing this month" from our own daily deltas), **trending games** computed from our own snapshots, **month-stamped auto-refreshing ranking titles** ("Top German streamers, February 2027" — TT's proven freshness-by-design pattern), streamer-page mini-charts (inline SVG at build — protect our LCP advantage).
- Every chart axis starts at our own day zero and says so ("tracked by vodfetch since 2026") — stated plainly on /methodology. Series gaps render as visible gaps.
- Upgrade `/twitch-statistics` into the head-term hub (live platform snapshot + our growing archive) only here — earlier it under-delivers on the "statistics" promise (honesty collision at SD 58–63 against TT's pos-1 with charts back to 2012).
- This is when vodfetch may honestly use "tracker" language — and when every post-2026 entrant permanently lacks what we have.

---

## 3) Hard NOs (unanimous across all three strategy lenses — rejection is the strategy too)

| Rejected | Why |
|---|---|
| **Live sub-count leaderboard / per-streamer sub counters** | The niche's #1 non-brand archetype (TT /subscribers = 42.5K visits/mo) — and structurally impossible to serve honestly: Twitch exposes no public sub API; every competitor number is scraped/inferred (their own "?" cells admit it). Publishing estimates = spending the honesty moat. We capture the informational tail instead (T3.2). |
| **Streamer net worth / earnings pages** | 18K US + 4.2K + 2K vol at tempting SD 17–33, but every number is fabrication by definition — a direct Editorial-Policy violation. At most a "how streamer revenue works" explainer, later, maybe. |
| **Streamer bio pages (age/height/real name)** | 70K US + 41K UK vol, incumbents rank without answering — but it's hand-maintained celebrity gossip: E-E-A-T burden, permanent staleness risk, zero tool moat, zero funnel. |
| **Steam charts / player-count vertical** | ~628K vol across exports — the biggest trap in the recon. It's **Steam** intent, not Twitch: incumbents rank pos 24–65 there and visibly bleed (0 of 470 kws in top 3). A Steam tool dilutes the "VODFETCH = Twitch" entity right as AI models form it. |
| **Mass programmatic streamer rollout now** (thousands of pages) | The archetype pays only at tens of thousands of indexed pages + AS 50+ (streamscharts). SG proves the failure mode: 1,894 /channel kws → 2,879 visits/mo. Pilot 50–150, gate on GSC. |
| **Per-stream detail pages** (/{login}/streams/{id}) | The incumbents' genuinely defensible layer — minutes-level polling of every live channel, stored forever. Real ingestion infra, years before pages have content; indexation suicide for a young domain. |
| **Per-game stats page factory** | Weakest archetype at every incumbent (TT /games/* = 1.9% of traffic from 5,380 kws; SG /game/ near-dead). Historical charts need the DB we don't have. One live top-games page + CTAs (T4.3) is the honest slice. |
| **"How to stream on Twitch" creator education** | SD 60–73, Twitch's own docs + saturated creator industry own it; creator-side intent with no funnel. The two winnable creator posts (Partner, raid) are in T1. |
| **Scraping TT/SG for history backfill** | No APIs, explicit no-scraping stances, fatal optics for an honesty brand. Our history starts at our own day zero — stated on /methodology. |
| **Separate stats brand/domain, Kick/multi-platform expansion** | TT's brand queries are 0.08% of its traffic — the moat is inventory, not brand. Splitting domains splits link equity + the @graph entity. The project deliberately pivoted TO Twitch-only; streamscharts owns the Kick flank. |
| **"TwitchTracker/SullyGnome alternative" compare pages (now)** | Their brand-nav volume is tiny (1.7K / ~300), and claiming stats parity before shipping stats features would be dishonest. Revisit after T2–T4 are live. |

---

## 4) Guardrails (stats-specific extensions of the honesty policy)

1. **As-of timestamps on every static number.** Never pre-render a volatile metric as "live"; live numbers only via client-side fetch. (Extends the content-must-match-tool-output rule.)
2. **Official Helix for anything systematic** (build snapshots, cron collection — app token, our first real secret, in local `.env` / GH Actions secrets, never in `dist/`); unofficial GQL only for user-initiated lookups, exactly like the downloader today.
3. **No estimates, ever:** no sub numbers, no net worth, no "average viewers" we didn't measure ourselves. What we refuse to publish is itself published (methodology page).
4. **Tracker semantics are earned, not claimed:** no "tracker/tracking/history/growth" copy until T6's own data exists.
5. **Indexation gates:** each programmatic expansion (streamer roster, game hubs, FR/ES ranking twins) requires GSC evidence from the previous tranche (>70% indexed). GSC request-indexing + IndexNow (with TWITCHDL_BASE_URL set!) for every new URL.
6. **Language discipline:** curated pages EN+DE+FR+ES as usual; entity pages language-matched only (no hreflang parity for locale-bound streamer queries).
7. **Performance discipline:** no chart libraries on the critical path — build-time inline SVG; keep the LCP advantage over the ad-heavy incumbents.
8. Same per-batch pipeline as always: author → validate → translate → build → **secret-grep over dist/ (now doubly mandatory)** → deploy → verify live → IndexNow → commit → tick this log.

---

## 5) Sequencing & success criteria

**Order:** T0 (infra + flywheel) immediately → T1 (content quick wins) → T2 (tools) → T3 (facts/AEO) → T4 (rankings/DE) → T5 (entity pilot) → T6 (gated, 2027). T0.4 runs in parallel with everything from day one. T1.5 (Recap) must be live by November.

**What success looks like:**
- 90 days: T0–T3 live; chat-log/username/follower pages indexed and ranking top-20 in their soft SERPs; /data + records cited in at least one AI answer (spot-check ChatGPT/Gemini/Perplexity for "most viewed twitch stream", "how many followers does X have", "twitch chat log").
- 6 months: T4–T5 live; ≥70% of the streamer pilot indexed; measurable GSC clicks on "{name} vods/archive/clips" queries; first backlinks from the open datasets.
- 12 months: T6 unlocked with 6+ months of own history; vodfetch named by AI models both as downloader AND as a Twitch-facts source — the two entities reinforcing each other.

**The flywheel, in one line:** stats pages create entity queries → entity pages surface VODs/clips → every row has a download button → downloader usage grows the brand AI models cite → citations feed the stats layer's authority.

---

## 6) Status log (update as batches ship)
- [x] **T0 — Infra prerequisites** (shipped 2026-07-06): tw.js hardened (Origin/Referer allowlist, echoed ACAO + Vary, 5 local handler tests green — foreign origins 403, same-origin/previews/localhost pass); `scripts/deploy.sh` (canonical env vars + secret-grep gate + live-verify + IndexNow); `.env.example` + `.gitignore` (.env); history flywheel: `scripts/collect_snapshot.py` (official Helix only, graceful SKIP without secrets, daily JSON rollups + follower CSV series) + `.github/workflows/collect-stats.yml` (2×/day cron, commits to data/) + curated 115-channel roster (EN/DE/FR/ES). **OWNER ACTION NEEDED:** register the Twitch dev app (see .env.example) and add TWITCH_HELIX_CLIENT_ID/SECRET as GitHub Actions repo secrets — until then the cron runs as green SKIP and collects nothing.
- [x] **T1 — Content wins + first tracker tool** (shipped 2026-07-06, live + IndexNow 968 URLs): new landing `/twitch-chat-log` (custom HowTo steps, honest per-VOD scope) + new landing `/twitch-username-checker` (first non-downloader tool: new checker card UI, client-side GQL direct to gql.twitch.tv with proxy fallback, result links into the channel browser via `/?url={login}&go=1`; un_* i18n EN/DE hand-written + FR/ES translated; JS `gqlStats()` helper + guarded tail listeners) + 3 blog posts (`how-to-become-twitch-partner` with web-verified 25h/12days/75-avg numbers, `how-to-raid-on-twitch`, `twitch-recap-how-to-see-and-save` with verified Dec-2-2025/annual-recap facts — live well before the Jan/Feb spike) + past-streams hub expansion on `download-twitch-vod-before-deleted` (2 sections + 3 FAQs: watch-past-streams / archive / VOD-finder cluster) + clip-landing search/manager copy pass (intro + 2 FAQs, honest: channel browser = top-clips search) + machine files seeded with sourced records (Ibai La Velada V 9.3M+ peak 07/2025, Kai Cenat 1M+ active subs 09/2025 + most-followed since 07/2025, chat-log + username-checker quick answers; `_ai_resources` links both tools). All EN+DE+FR+ES (translation workflow, shape-validated). Build 969 pages (+70), dist audit **0 errors** (link graph 64,256 edges, 0 broken/0 orphans), all-lang render checks 98 pages, proxy hardening verified live (foreign Origin→403), checker GQL verified against production API.
- [ ] **T2 — Client-side live tools** (follower count + followage, clip search/manager)
- [ ] **T3 — Facts & transparency layer** (records EN/DE, sub-count truth hub, methodology, /data datasets)
- [ ] **T4 — Rankings & German flank** (most-followed, DE pair, top-games, teams guide)
- [ ] **T5 — Streamer entity pilot** (50–150 curated, gated expansion)
- [ ] **T6 — "Since 2026" history layer** (gated on T0.4 ≥3–6 months)
