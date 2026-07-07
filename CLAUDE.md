# CLAUDE.md — VODFETCH

> Kontextübergabe (Claude-Account-Wechsel). **Vollständiges Protokoll:** `/Users/alex_memberspot/ÜBERGABE ORDNER/01-VODFETCH.md` — dort steht „Wo weitermachen?".
> **Zugänge (Tokens):** `/Users/alex_memberspot/ÜBERGABE ORDNER/00-CREDENTIALS-UND-ZUGAENGE.md`

**Was:** Kostenloser, werbefreier Twitch-Downloader (VODs, Clips, Live → MP4), Downloads laufen client-seitig im Browser. Kern: Python-Paket `twitchdl/` + statischer Export via `build_static.py` → `dist/`. **Medien-Proxy: Cloudflare Worker `vodfetch-proxy` (`https://vodfetch-proxy.gentle-salad-3beb.workers.dev`) — kein Egress-Bandbreiten-Kosten (Netlify berechnete das → Missbrauchs-Kostenfall 2026-07-07).** Netlify-Function `tw` (`/api/tw`) bleibt nur als Fallback. GraphQL geht direkt an gql.twitch.tv (CORS-offen), nie über einen Proxy. Details: `cloudflare/README.md`, Memory `proxy-cost-abuse-incident`.

**Hosting:** Netlify Site `cozy-crumble-bff916` (ID `339599ca-2663-425a-82b0-c2964f96a65d`), Domain **vodfetch.com**. Repo: `github.com/pigeonmilkgg/vodfetch` (Branch `main`).

**Build & Deploy:** am einfachsten `./scripts/deploy.sh` — kapselt Env-Vars + Secret-Grep + Deploy + Live-Verify + IndexNow, und **erzwingt `TWITCHDL_PROXY_BASE` auf den Cloudflare-Worker** (sonst fällt ein Build still auf teure Netlify-Bandbreite zurück). Manuelle Langform (falls nötig):
```bash
# 1) Build MIT allen Env-Vars (sonst fehlen Bing-Meta/sameAs; ohne TWITCHDL_PROXY_BASE → Netlify-Fallback!)
TWITCHDL_BASE_URL="https://vodfetch.com" TWITCHDL_SAMEAS="https://github.com/pigeonmilkgg/vodfetch" TWITCHDL_REPO="https://github.com/pigeonmilkgg/vodfetch" TWITCHDL_BING_VERIFY="DD10C1E27169A8BD038386A868573443" TWITCHDL_PROXY_BASE="https://vodfetch-proxy.gentle-salad-3beb.workers.dev" ./.venv/bin/python build_static.py
# 2) Deploy: --no-build ZWINGEND + --site (lokal nicht gelinkt)
netlify deploy --prod --dir=dist --functions=netlify/functions --no-build --site=339599ca-2663-425a-82b0-c2964f96a65d
# 3) IndexNow: TWITCHDL_BASE_URL ZWINGEND setzen (Default ist sonst die netlify.app-Subdomain → falscher Host)
TWITCHDL_BASE_URL="https://vodfetch.com" ./.venv/bin/python submit_indexnow.py
```
> Worker deployen/aktualisieren (z.B. IP-Block erweitern): `./scripts/deploy-worker.sh` (einmalig `npx wrangler login`). Worker-Code: `cloudflare/worker.js`.
> Livegang läuft über CLI-Direct-Upload von `dist/`, NICHT über git push (Site baut nicht automatisch aus GitHub). GSC ist per DNS-TXT verifiziert (braucht kein Meta).

**Status:** live. Aktiver Arbeitsstrang = SEO/AEO-Content (`docs/DOMINATION_PLAN.md` = maßgebliche To-do-Liste). Batches 1–5 alle live (zuletzt Batch 5: `/twitch-converter` + `/blog/how-to-get-twitch-transcript` + DE/FR „herunterladen"/„télécharger"). On-page/AEO gilt als gemaxt; verbleibender Hebel = off-page (Backlinks + GSC-Request-Indexing + Domain-Zeit).

**Stolperfalle:** Ordner heißt `TWITCH DOWNLOADER`, Marke/Domain ist **VODFETCH**. `dist/` ist generiert — nicht von Hand editieren; vor Deploy Secret-Grep über `dist/`.
