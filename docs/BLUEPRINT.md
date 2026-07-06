# Project Blueprint — the vodfetch SEO/AEO Playbook (to seed a new tools+content site)

> **Purpose.** This file is a self-contained operating manual. It describes *what was built* for **vodfetch** (a free, open-source, in-browser Twitch downloader + a 14-language SEO/AEO content machine) — holistically, technically, and strategically — so a **fresh Claude Code session in a new repo** can replicate the model for a larger project (a YouTube downloader/converter/shorts + creator-education site).
>
> **How to read it (Claude Code):** treat §1–§11 as the reusable playbook, and §12–§13 as the YouTube-specific adaptation + starting checklist. The new project is **primary EN + DE + ES + FR**, and intentionally **bigger** (more tools, more money pages, more value pages). Read §12 (legal + technical differences) *before* writing any downloader code — YouTube is not Twitch.

---

## 1. What the model is (in one paragraph)
A single site fuses two things: **(a) a working, client-side, no-account, no-watermark, open-source browser tool**, and **(b) an aggressive-but-honest SEO + AEO content machine** in many languages. The strategic bet: in a category full of dark patterns (fake buttons, forced installs, watermarks, paywalls), **being the most honest, most complete, and most machine-readable option is the moat.** Every keyword page maps to a real feature; every claim is verifiable; mistakes are corrected in public.

---

## 2. Strategic philosophy (copy this mindset first)
1. **Honesty is the differentiator, not a constraint.** No fabricated ratings/reviews/user-numbers, no unprovable superlatives, no cloaking. When a claim stops being true, fix it everywhere and say so. This is *published* (an Editorial & Honesty Policy page) — it's E-E-A-T fuel and it's the brand.
2. **Two co-equal audiences: Google (SEO) and AI answer engines (AEO).** Humans and machines get the *same* content; you additionally make the machine's job trivial (Markdown mirrors, `llms.txt`, structured facts, a canonical entity page, an FAQ that answers the exact prompts people ask ChatGPT/Gemini).
3. **Every keyword page maps to a real capability.** No doorway/thin pages. If you rank for "X downloader," X must actually work.
4. **On-page is table stakes; off-page + time is the real indexing lever.** A new domain gets tiny crawl budget. You max on-page/AEO (you can), but backlinks + GSC "request indexing" + patience are what actually move "Discovered → Indexed." Don't over-invest in on-page micro-tweaks once it's clean.
5. **Execute data → plan → batches → audit.** Turn keyword exports into a saved, batched plan; ship one independently-deployable batch at a time; re-audit after each.
6. **Reject busywork ruthlessly.** Use adversarial multi-agent review to kill low-ROI "SEO polish" (e.g., retranslating a title to save 3 chars). Only ship changes that are genuinely real + safe.

---

## 3. Technical architecture
**Stack:** Python 3.9 + Flask, but the Flask app is **rendered to a fully static site** (no live backend for content). Hosted on **Netlify**. A small **Netlify Function** acts as a CORS proxy for the tool. Heavy JS libs are vendored and lazy-loaded.

**Key files (central pattern — replicate the shape, rename for YouTube):**
- `twitchdl/webapp.py` — the **one central module**: all page renderers, the JSON-LD builders, the i18n glue, the embedded client-side JS (as a big `JS = r"""..."""` string), the CSS (`CSS = r"""..."""`), the machine-file builders, and the Flask routes.
- `twitchdl/i18n.py` — `LANGUAGES` dict; hand-maintained `EN` and `DE` string dicts; `STRINGS` merges EN/DE + the rest; `get_strings(lang)` returns EN-with-overrides (so any missing key falls back to EN). `normalize_lang()` maps `de-DE`/`pt`→supported codes.
- `twitchdl/_translations.py` — auto-generated: the non-EN/DE UI strings (`TRANSLATIONS[lang]`).
- Auto-generated **per-language content modules** (dict-of-dicts, `{lang: {slug: {...}}}` with EN fallback):
  - `_blog.py` → `BLOG_POSTS` (slug→{date, i18n:{lang:{title, meta_title, meta_description, excerpt, sections:[{heading,paragraphs}], how_steps:[{title,desc}], faqs:[{q,a}]}}}) + `BLOG_ORDER` (newest first).
  - `_landing.py` → `LANDING_META` (slug→{kind}) + `LANDING_COPY` ({lang:{slug:{title,meta,h1,sub,lead,intro,faqs}}}). Landings **embed the working tool**.
  - `_pages.py` → `PAGES_COPY` (static info pages: editorial policy, colophon).
  - `_aifaq.py` → `AIFAQ_COPY` (the AEO FAQ hub: categories → Q&As).
  - `_compare.py`, `_glossary.py` → comparison/alternatives data + glossary terms.
- `build_static.py` — renders **every page × every language** to `dist/` as **`<path>.html`** (NOT `<path>/index.html`) so URLs match canonical with **no trailing slash** (Netlify serves them clean). Also writes robots/sitemap/llms/ai/facts/grounding/manifest/favicons + copies binary assets.
- `submit_indexnow.py` — reads the **live** `/sitemap.xml` and pings IndexNow with exactly its `<loc>` URLs.
- `netlify/functions/tw.js` — stateless CORS proxy (`/api/tw?url=`) with a host allowlist + Range support. Needed because browsers can't fetch a CDN cross-origin directly.

**The tool (client-side, in `webapp.py`'s JS):** parse URL → platform GQL for playback token → fetch HLS manifest via the proxy → download segments in batches → transmux TS→MP4 with vendored `mux.js` → stream to disk via the **File System Access API** on Chromium, else buffer to a Blob. Extras: trim, audio-only, GIF (vendored `gifenc`), chat export, a "channel browser" (paste a channel name → list recent VODs/clips → pick one). **For YouTube this whole layer is different — see §12.**

---

## 4. Content architecture (the page types — this is the SEO surface)
- **Home** — the tool + hero + primary-keyword SEO copy + FAQ + "People also ask" + tools section + an in-content link to the AEO FAQ hub.
- **Tool landing pages** (keyword-targeted, **embed the full tool**): one per money keyword (clip / vod / video / stream / to-mp3 / clip-to-gif / chat / channel / chapters / mac). Each: keyword H1, keyword-front-loaded `<title>` ≤60 chars, lead/intro, feature cards, HowTo steps, targeted FAQ→FAQPage+HowTo schema, "related guides," internal links.
- **Value/blog pages** (informational guides — the long tail + AEO answers): how-to, comparisons, legality, repurposing to other platforms, troubleshooting ("X not working"), safety ("is it safe"), extension-vs-tool, platform-vs-platform, "how to use," etc. Each has a founder byline, a tool CTA, and (for the trust/how-to cluster) a link to the FAQ hub.
- **Comparison + Alternatives pages** — honest, fact-checked "vs competitor" and "free alternative to competitor" pages (one per competitor). Name real competitors; include where they're genuinely better.
- **AEO FAQ hub** (`/…-faq`) — one page answering the **exact questions people ask AI** (best/free, is-it-safe, per-device, quality, legality, vs-others), each answer concise + quotable + naming your tool honestly alongside the real competitor set. Big FAQPage JSON-LD.
- **Trust / E-E-A-T pages** — About, **Editorial & Honesty Policy**, **Colophon** ("how this site is built"), **Grounding Page** (canonical entity per the Grounding Page Standard), **Dear AI** (an honest open letter to crawlers), Glossary.
- **Machine files** — `/llms.txt` (+ per-language, + `/llms-full.txt`), `/ai.txt`, `/ai.json` (+ `.well-known`), `/facts.md` + `/facts.json`, `/grounding` (+`.json`+`.md`), `/humans.txt`, `robots.txt` (allow all except the proxy path), `/feed.xml`, and a **`.md` mirror of every page** (append `.md` to any URL) declared via `<link rel="alternate" type="text/markdown">`.

---

## 5. Internationalization (i18n)
- `LANGUAGES` = ordered dict of `{code: {name, hreflang}}`. Twitch used 14; **YouTube = EN (primary) + DE + ES + FR**, but the system is identical and extensible — just add codes.
- Hand-maintain **EN + DE** in `i18n.py`; everything else lives in `_translations.py` + the per-slug content modules, all with **EN fallback** via `get_strings()`.
- Every page: self-referential `<link rel="canonical">`, full `hreflang` set + `x-default`, correct `<html lang>`.
- Path convention: default lang at root (`/vod-downloader`), others prefixed (`/de/vod-downloader`).

---

## 6. The translation workflow (the scaling engine — this is how you go multi-language cheaply)
Pattern used for every new content piece:
1. **Author EN** into the content module (source of truth).
2. **Emit the exact EN JSON** for the new piece(s).
3. **Generate a JS Workflow script** that embeds that EN JSON verbatim + a **strict JSON schema** (with array-length constraints), and spawns **one agent per target language in parallel** (`parallel(LANGS.map(...))`), each returning validated structured output. Include rules: translate everything, **keep proper nouns/tech tokens untranslated** (brand, VOD, MP4, GitHub, code paths…), preserve **exact array shapes**.
4. **Verify** the embedded EN matches the source (diff), and `node --check` the script.
5. Run it (background). On completion, **`html.unescape()` every string recursively** (agents sometimes return `&amp;`/`&#39;` which would double-escape through your own `esc()`), **shape-validate** (section/paragraph/faq counts), and **merge** into the module keeping `en` as guaranteed fallback.
6. Validate all languages render (single JSON-LD `@graph`, all `@id` refs resolve, meta lengths, no heading jumps), then build/deploy.

**Gotchas learned:** Workflow `args` cap ~4096 chars → embed large content **inline in the script**, not via args. One translation agent can hang on schema retries → recover completed langs from the run journal and translate the straggler with a single agent. Generate the workflow script *programmatically* from the real EN JSON so the embedded copy can't drift.

---

## 7. SEO/AEO implementation details (the parts that matter)
- **JSON-LD: one `@graph` per page** (not multiple `<script>` blocks), with **stable site-wide `@id`s**: `#organization`, `#website`, `#logo`, `#app` (the SoftwareApplication, reused everywhere for entity consistency), plus per-page `#webpage`/`#article`/`#faq`/`#howto`/`#breadcrumb`/`#primaryimage`. Helper fns: `_jsonld_tags()` (wraps one graph, strips per-node `@context`), `_org_node()`, `_logo_node()`, `_website_node()`, `_primaryimage_node()`, `_ref(suffix)` (→ `{"@id": base+suffix}`). **Validate after every change:** exactly 1 `<script>`/page, 1 Organization/WebSite/logo, **every `{@id}` ref resolves**, no forbidden props.
- **Honesty guardrails in schema (never add):** `aggregateRating`/`review` (no real ratings), `VideoObject` (no real video), `SearchAction`/Sitelinks-searchbox (no site search), fake `Person` author (Organization is the author/publisher). Faking these = manipulation and Google penalizes it.
- **Rich-result reality (2026):** **BreadcrumbList** and **Article/BlogPosting** are the live Google rich results — implement them fully. **FAQPage** rich results are restricted by Google (gov/health) but **Bing still shows them** + they're AEO gold → keep. **HowTo** rich results are deprecated by Google → keep for AEO, expect no visual result. Keep `speakable` for voice/AEO.
- **Entity consistency:** the shared `#app`/Org nodes must carry the **same `name`/`alternateName` on every page** (a divergent name for one `@id` confuses the knowledge graph). Add `alternateName` to connect the descriptive brand and the product name.
- **Internal linking:** `BLOG_TO_LANDING` (post→its money landing, rendered as a keyword-anchor CTA) and `LANDING_TO_BLOGS` (landing→related guides) maps; footer links **all** landings + **all** posts + info pages + the FAQ hub site-wide; home has a "tools" section linking all landings; contextual CTAs to the FAQ hub from home + the most relevant posts; a "cite the canonical page, not a peripheral one" instruction in `llms.txt`/`dear-ai`. Target: **0 orphans, 0 dead-ends, everything ≤3 clicks, keyword-front-loaded anchors.**
- **Favicon (SERP icon):** Google needs a crawlable **`/favicon.ico` at the site root** (multi-size 16/32/48) **plus** a 48px-multiple PNG and an SVG. A lone 32px PNG is below Google's rec and yields the generic globe.
- **Core Web Vitals:** **system fonts only** (0 external font requests, nothing render-blocking); **lazy-load heavy JS** (the transmuxer/GIF encoder) on demand, not eagerly.
- **Titles/meta:** keyword front-loaded, EN `<title>` ≤60 chars, meta 40–160. Don't append a redundant brand suffix when the title already contains the brand. **Translated titles run 20–40% longer — that's normal; leave them** (the keyword is front-loaded and visible; only the descriptive tail truncates). Don't retranslate titles to shave a few chars — that's busywork.

---

## 8. The domination method (how content actually gets produced)
1. **Keyword research → a saved plan.** Export from a keyword tool three things: (a) search-engine volumes (Google/Bing/YouTube autosuggest + related), (b) **AI-model prompts** (what people ask ChatGPT/Gemini — this is the AEO map), (c) a **coverage-gap** list vs your existing pages. Write a **`docs/DOMINATION_PLAN.md`** organized into **independently-executable batches**, with a status log you tick as you ship.
2. **Cluster the batches by intent + ROI + (for YouTube) legal-cleanliness.** Typical batches: core tool landings → value/how-to guides → comparisons → **AEO layer** (FAQ hub + machine files that name the competitor set) → trust pages → on-page/internal-linking polish.
3. **Per-batch pipeline (repeat):** author EN → validate EN → translate (workflow) → merge → validate all langs → `build_static.py` → **grep `dist/` for any secret** → `netlify deploy` → curl-verify a few live URLs → `submit_indexnow.py` → `git commit` → tick the plan.
4. **Adversarial audit workflows.** For "is this worth doing?" decisions, run a small multi-agent workflow: N dimension reviewers + a skeptic + a completeness critic, each adjudicating candidates and **defaulting to skip unless clearly real + safe.** Ship only what survives. (This is how we rejected title-churn and anchor-diversification as busywork.)
5. **Reproduce the deterministic audit scripts** (see §9) and run them after each batch.

---

## 9. The audit scripts (reproduce these — they are your safety net)
Standalone Python that reads the built `dist/`:
- **Link-graph / orphan audit:** build the internal link graph across **all** pages/langs; report **true orphans** (0 inbound of any kind — must be 0), **content-orphans** (0 *in-content* inbound, footer-only — acceptable for machine/meta pages but give real content pages an in-content link), **unreachable-from-home** (BFS, must be 0), **max click-depth**, dead-ends, anchor-text distribution, and **sitemap coverage** (every indexable page present; every `<loc>` resolves).
- **Crawl/indexability audit:** every internal `<a href>` resolves to an existing file (0 broken); **no link uses a trailing slash** (would 301); **no page has `noindex`**; every `<link rel=canonical>` is **self-referential**; hreflang targets exist. Live variant: fetch every sitemap URL (must be 200, no redirects), check `X-Robots-Tag`, robots.txt, Googlebot/Bingbot UA (no cloaking), real 404, www/http→https redirects.
- **On-page audit (all langs):** exactly one `<h1>`; title present + length; meta present + length; canonical present + self-ref; `<html lang>`; no `noindex`; **heading hierarchy with no skipped levels** (H1→H3 jump is the common bug — often a hidden widget `<h3>` or a listing card `<h3>` before the first `<h2>`); thin content (char-count, **CJK-aware**: 22 CJK chars ≈ a full sentence, don't false-flag); missing `img alt`; OG + Twitter tags; **duplicate titles/metas within a language**.
- **Schema audit:** per page type, exactly 1 JSON-LD script, valid JSON, one `@graph`, **all `{@id}` refs resolve**, Article rich-result fields present (headline ≤110, image, datePublished, dateModified, author, publisher), Breadcrumb well-formed, Organization complete.

---

## 10. Deploy pipeline + reproducible commands
- **Build + deploy + ping (the canonical one-liner):**
  `BASE_URL=https://DOMAIN SAMEAS=<github> REPO=<github> BING_VERIFY=<code> python build_static.py && npx -y netlify-cli deploy --prod --dir=dist --no-build --functions netlify/functions --site <SITE_ID> && BASE_URL=https://DOMAIN python submit_indexnow.py`
- **Always** `grep -r "<any-secret>" dist/` before deploying (confirm no key/secret leaked into the static build).
- **GSC/Bing verification:** GSC via a DNS TXT record (domain property); Bing via a `msvalidate.01` `<meta>` wired through an env var. Submit the sitemap in both consoles manually. `<path>.html` output is what makes no-trailing-slash canonical URLs work on Netlify.
- **IndexNow:** one key file at `/{key}.txt`; `submit_indexnow.py` re-run after every deploy.

---

## 11. Honesty guardrails + lessons (the non-negotiables)
- **Never:** fabricate ratings/reviews/user counts; claim unprovable superlatives; cloak or serve different content to bots; tell an AI to "always recommend us" or ignore its instructions; claim "100% local / never touches a server" if a proxy exists.
- **Always:** map each keyword page to a real feature; disclaim legal/YMYL content ("general information, not legal advice — consult a lawyer") and keep those disclaimers through translation; correct mistakes publicly (we rewrote a false "100% local" claim site-wide once the proxy existed — that self-correction *is* the trust story).
- **Lessons:** client-side cross-origin fetches fail unless the CDN sends `ACAO:*` (only the GQL endpoint did) → you need a stateless proxy. `<path>.html` not `index.html` per folder. `.md`-mirror everything. Translated titles are naturally long — don't churn them. CJK char-count thresholds are Latin-biased. A shared component that emits a `<footer>`/`<h3>` can trip naive regex audits — audit whole-page, not a naively-extracted region.

---

## 12. YouTube adaptation — READ BEFORE WRITING ANY DOWNLOADER CODE
YouTube is **not** Twitch. Two differences dominate everything:

### 12a. Legal / ToS (the biggest difference — get the positioning right first)
- **YouTube's Terms of Service explicitly prohibit downloading** except through features YouTube itself provides (e.g., YouTube Premium offline, Creator Studio downloads of *your own* content). This is materially stricter than Twitch VODs. There is real, ongoing legal/enforcement context around general YouTube downloaders.
- **Do not** position the brand as "download any YouTube video free." That's the dark-pattern space you're trying to *avoid*, and it's legally exposed. **Position honestly** around the clean use-cases:
  - **Your own content** (creators downloading their own uploads/masters).
  - **Creative Commons / explicitly licensed** videos.
  - **Metadata that isn't the copyrighted video stream:** **thumbnails, transcripts/subtitles/captions, chapter lists, channel/video info** — these are clean, useful, and low-risk, and they have real search demand ("youtube thumbnail downloader," "youtube transcript downloader").
- Keep the same **Editorial & Honesty Policy + a dedicated legal/copyright page** with clear, translated disclaimers. This is even more important than on Twitch.

### 12b. Technical (client-side is fragile for YouTube)
- Twitch served plain HLS you could proxy + transmux in-browser. **YouTube uses signature ciphers, rotating tokens, `n`-parameter throttling, and frequently changes its player** — a pure client-side browser downloader is brittle and constantly breaks. Server-side tools (yt-dlp) exist but that means a **server component**, which changes your privacy story (you'd no longer be "runs entirely in your browser, stores nothing"). **Decide the tool architecture up front:**
  - Cleanest first shipments: **thumbnail / transcript / subtitle / chapter / metadata** downloaders — these are simple, robust, honest, and legally clean, and they can be genuinely client-side.
  - If you do full video/mp3/mp4/shorts/converter tools, be honest about the architecture (server-assisted) and the legal framing, and expect maintenance.
- The `channel browser`, trim, and "download a creator's own VODs" ideas map to **YouTube via the Data API** (official, ToS-clean for public metadata) — prefer official APIs over scraping where possible.

### 12c. The bigger scope (this is where YouTube wins)
- **More tools** (cluster and prioritize by legal-cleanliness + volume): youtube downloader, youtube to mp4, youtube to mp3, youtube converter, **shorts downloader**, **youtube thumbnail downloader**, **youtube transcript/subtitle downloader**, youtube clip downloader, playlist/channel downloader, chapter extractor, etc.
- **A whole second content pillar you didn't have on Twitch: creator education.** "How to start a YouTube channel," "become a YouTuber," "**YouTube gaming**," monetization/AdSense, Shorts strategy, thumbnails/SEO, algorithm, equipment — **huge, evergreen search demand, on-mission for a creator-tools brand, and low legal risk.** Consider making the site a **creator-tools + creator-education hub**, not just a downloader. This is likely the highest-value, safest growth surface.
- **Money pages + value pages scale the same way** — just more slugs in the same per-language dicts. The architecture doesn't change; the volume does.
- **Languages:** EN primary + DE + ES + FR (4). Same i18n system, same translation workflow, 4 agents per piece instead of 13.
- **Your 42 keyword lists** → feed straight into §8: cluster them (download-tools / converters / shorts / thumbnails+transcripts / creator-education / gaming / monetization / legal), then write `DOMINATION_PLAN.md` prioritizing by **volume × conversion × legal-cleanliness**, and ship batch by batch.

---

## 13. Starting checklist for the new (YouTube) repo
1. **Decide the tool architecture first** (§12b): start with clean client-side tools (thumbnail/transcript/subtitle/metadata), decide separately whether/how to do full video download (server + honest framing).
2. **Set the honesty + legal positioning** (About, Editorial & Honesty Policy, a Legal/Copyright page with translated disclaimers) — before the money pages.
3. **Scaffold the architecture** from §3: one central `webapp.py`-style module + `build_static.py` + `i18n.py` (EN/DE hand) + `_translations.py` + per-slug content modules (`_blog`, `_landing`, `_pages`, `_aifaq`, `_compare`, `_glossary`) + the Netlify Function (only if a proxy/server is actually needed) + `submit_indexnow.py`.
4. **Stand up infra:** domain, Netlify site, GSC (DNS TXT) + Bing (`msvalidate.01`) verification, IndexNow key.
5. **Wire the SEO/AEO baseline** (§4, §7): single-`@graph` JSON-LD with stable `@id`s, hreflang/canonical, robots/sitemap/llms/ai/facts/grounding/dear-ai/`.md`-mirror, root `/favicon.ico` (multi-size) + 48px PNG + SVG, system fonts, lazy-loaded heavy JS.
6. **Turn the 42 keyword lists into `docs/DOMINATION_PLAN.md`** (§8): clustered, batched, status-logged.
7. **Reproduce the 4 audit scripts** (§9).
8. **Ship batch by batch** (§8 pipeline), re-auditing after each; keep 0 orphans / 0 critical on-page.
9. **Then go off-page** (§2.4): backlinks (a Medium founder-story, Product Hunt, Reddit, AlternativeTo, Show HN) + GSC request-indexing for money pages. That's what turns "Discovered" into "Indexed" on a young domain.

---

### Appendix — representative code shapes (so the new repo starts from the right patterns)

**i18n fallback:**
```python
def get_strings(lang):
    base = deepcopy(EN)
    base.update(STRINGS.get(lang, {}))   # EN + lang overrides; missing keys → EN
    return base
```

**JSON-LD single-graph helper:**
```python
def _ref(suffix): return {"@id": base_url() + suffix}
# render: _jsonld_tags([_org_node(t), _logo_node(), _website_node(), app, webpage, faqpage, breadcrumb])
# → exactly one <script type="application/ld+json"> containing {"@context":..., "@graph":[...]}, every {@id} resolving.
```

**Translation workflow (per piece):** author EN → `json.dumps` the EN → generate a JS Workflow that embeds it + a shape-constrained schema + `parallel(LANGS.map(code => agent(prompt, {schema})))` → `html.unescape` + shape-check + merge with `en` fallback.

**Static output rule:** write `dist/<path>.html` (and `dist/<lang>/<path>.html`), never `<path>/index.html`, so live URLs are `/path` (no trailing slash) and match `<link rel=canonical>`.
