# CLAUDE.md — VODFETCH

> Kontextübergabe (Claude-Account-Wechsel). **Vollständiges Protokoll:** `/Users/alex_memberspot/ÜBERGABE ORDNER/01-VODFETCH.md` — dort steht „Wo weitermachen?".
> **Zugänge (Tokens):** `/Users/alex_memberspot/ÜBERGABE ORDNER/00-CREDENTIALS-UND-ZUGAENGE.md`

**Was:** Kostenloser, werbefreier Twitch-Downloader (VODs, Clips, Live → MP4), Downloads laufen client-seitig im Browser. Kern: Python-Paket `twitchdl/` + statischer Export via `build_static.py` → `dist/`. Netlify-Function `tw` = CORS-Proxy.

**Hosting:** Netlify Site `cozy-crumble-bff916` (ID `339599ca-2663-425a-82b0-c2964f96a65d`), Domain **vodfetch.com**. Repo: `github.com/pigeonmilkgg/vodfetch` (Branch `main`).

**Build & Deploy** (eine korrekte Zeile — die kurze 3-Zeilen-Variante ließ frühere Deploys Bing-Verify + sameAs droppen und pingte IndexNow gegen die netlify.app-Subdomain):
```bash
# 1) Build MIT allen Env-Vars (sonst fehlen Bing-msvalidate-Meta + Organization.sameAs)
TWITCHDL_BASE_URL="https://vodfetch.com" TWITCHDL_SAMEAS="https://github.com/pigeonmilkgg/vodfetch" TWITCHDL_REPO="https://github.com/pigeonmilkgg/vodfetch" TWITCHDL_BING_VERIFY="DD10C1E27169A8BD038386A868573443" ./.venv/bin/python build_static.py
# 2) Deploy: --no-build ZWINGEND (sonst fährt Netlify den netlify.toml-Build und failt) + --site (lokal nicht gelinkt)
netlify deploy --prod --dir=dist --functions=netlify/functions --no-build --site=339599ca-2663-425a-82b0-c2964f96a65d
# 3) IndexNow: TWITCHDL_BASE_URL ZWINGEND setzen (Default ist sonst die netlify.app-Subdomain → falscher Host)
TWITCHDL_BASE_URL="https://vodfetch.com" ./.venv/bin/python submit_indexnow.py
```
> Livegang läuft über CLI-Direct-Upload von `dist/`, NICHT über git push (Site baut nicht automatisch aus GitHub). GSC ist per DNS-TXT verifiziert (braucht kein Meta).

**Status:** live. Aktiver Arbeitsstrang = SEO/AEO-Content (`docs/DOMINATION_PLAN.md` = maßgebliche To-do-Liste). Batches 1–5 alle live (zuletzt Batch 5: `/twitch-converter` + `/blog/how-to-get-twitch-transcript` + DE/FR „herunterladen"/„télécharger"). On-page/AEO gilt als gemaxt; verbleibender Hebel = off-page (Backlinks + GSC-Request-Indexing + Domain-Zeit).

**Stolperfalle:** Ordner heißt `TWITCH DOWNLOADER`, Marke/Domain ist **VODFETCH**. `dist/` ist generiert — nicht von Hand editieren; vor Deploy Secret-Grep über `dist/`.
