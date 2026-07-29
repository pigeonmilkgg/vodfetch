# Twitch Downloader — free, in-browser VOD / clip / live downloader

**Download Twitch VODs, clips and live streams as MP4 — right in your browser.**
No account, no watermark, no install. Free and ad-supported (standard Google AdSense units — no
pop-ups, no fake download buttons). Open-source.

### 👉 Live app: **[vodfetch.com](https://vodfetch.com)**

[![License: MIT](https://img.shields.io/badge/License-MIT-9147ff.svg)](LICENSE)

vodfetch is a free **Twitch downloader** that saves past broadcasts (VODs), highlights, clips and
live streams as clean MP4 files. It runs entirely in your browser — paste a Twitch link, pick a
quality, and download. There's no software to install and no Twitch account required.

---

## ✨ Features

- **Every Twitch format** — VODs (past broadcasts & highlights), clips, and live recordings.
- **MP4 output** in original source quality (up to 1080p60), or pick 720p / 480p / audio-only.
- **Trim a section** of a VOD — download just one moment instead of a 6-hour file.
- **Clips without watermark**, full resolution.
- **Chat export** as `.txt`, `.json`, `.srt` or `.vtt` — for VODs, and for clips whose parent VOD still exists.
- **Private by design** — no account needed, and your files are never uploaded or stored. Runs in your
  browser; media is relayed through a stateless proxy only to satisfy browser security, and nothing is
  kept. The site itself is ad-supported via Google AdSense, which sets cookies — see
  [vodfetch.com/privacy](https://vodfetch.com/privacy).
- **English**, with a deep SEO/AEO content layer (34 guides, honest comparisons, measured streamer data).
- **Installable PWA** + download history.

> For personal use. Respect Twitch's Terms of Service and copyright. vodfetch only accesses
> publicly available content and does not bypass any paywall or DRM.

## 🔧 How it works

Twitch has no official download endpoint, so vodfetch uses the public web playback path:

```
Twitch link ─► GraphQL (public playback token) ─► usher HLS playlist
            ─► HLS segments (or a clip's MP4)   ─► reassembled in your browser ─► MP4
```

Because Twitch's media hosts don't send CORS headers, the browser can't fetch them directly. A tiny,
**stateless CORS proxy** (a Cloudflare Worker, allow-listed to Twitch hosts only) relays each small
segment; the browser does the assembly and transmuxes MPEG-TS → MP4 with [mux.js](https://github.com/videojs/mux.js).
On Chromium browsers the download streams straight to disk (File System Access API), so even
multi-gigabyte VODs work; elsewhere it buffers in memory (use **Trim** or **TS** format for very large files).

There's also a **local Python backend** (the original implementation) for power users / CLI.

## 🚀 Run it yourself

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # requests, flask

# Local web app (full Python backend — real downloads, no proxy needed):
python -m twitchdl web                  # http://127.0.0.1:8800

# CLI:
python -m twitchdl info  https://twitch.tv/videos/123456789
python -m twitchdl get   https://clips.twitch.tv/SomeClip -o ~/Downloads
```

`ffmpeg` is optional for the local backend (MP4 remux; falls back to `.ts`).

## 🌐 Build & deploy the static site (Netlify)

The public site is a fully static, pre-rendered export + one serverless proxy function.

```bash
./scripts/deploy.sh          # build + secret-grep + deploy + live-verify + IndexNow
./scripts/deploy.sh --build-only     # just render dist/
```

`deploy.sh` is the canonical path: it sets every required env var (base URL, the Cloudflare Worker
proxy, AdSense client), greps `dist/` for secrets, deploys with `--no-build`, verifies the live site
and submits IndexNow. Audits worth running before shipping:

```bash
python3 scripts/audit_dist.py    # link graph, canonicals, JSON-LD refs
python3 scripts/audit_seo.py     # titles, descriptions, headings, OG, sitemap agreement
python3 scripts/audit_policy.py  # uniqueness vs Google's "substantially similar pages"
```

Optional env vars: `TWITCHDL_SAMEAS` (comma-separated entity links), `TWITCHDL_GSC_VERIFY`,
`TWITCHDL_BING_VERIFY`, `TWITCHDL_INDEXNOW_KEY`.

## 🗂️ Project layout

```
twitchdl/            Python package: GraphQL client, HLS parser, downloader engine,
                     CLI, and the Flask web app (also renders the static site + client JS).
cloudflare/          worker.js — the stateless, Twitch-only CORS proxy (zero egress cost).
netlify/functions/   tw.js — the same proxy as a fallback.
extension/           Optional MV3 browser extension (not shipped on the site).
build_static.py      Static-site generator (English; blog, streamer pages, SEO/AI files).
submit_indexnow.py   IndexNow submitter.
tests/               Unit tests (URL & HLS parsing).
```

## 🤝 Contributing

Issues and PRs welcome. Run the tests with `python -m pytest tests/ -q`.

## ⚖️ Legal

vodfetch is a tool for archiving and personal use of publicly available Twitch content. You are
responsible for complying with [Twitch's Terms of Service](https://www.twitch.tv/p/legal/terms-of-service/)
and applicable copyright law. Don't re-upload or commercially use content you don't own. "Twitch" is
a trademark of its respective owner; this project is not affiliated with or endorsed by Twitch.

## 📄 License

[MIT](LICENSE)
