# vodfetch Medien-Proxy → Cloudflare Worker

Der Medien-Proxy (Usher-Playlists, HLS-Segmente, Clip-MP4s — alles was kein CORS
sendet) läuft auf **Cloudflare Workers** statt auf einer Netlify-Function.

**Warum:** Cloudflare berechnet **keine Egress-Bandbreite** — genau der Posten, der auf
Netlify beim Durchleiten von Video-Bytes teuer wurde (siehe den Missbrauchsvorfall vom
2026-07-07). Free-Tier: 100.000 Requests/Tag, danach 5 $/Monat flat für 10 Mio. Der Worker
**streamt** die Antwort (kein 5,4-MB-Cap, kein Base64 wie bei der Netlify-Function).

GraphQL läuft NICHT über den Proxy — der Client spricht `gql.twitch.tv` direkt an (CORS-offen).

## Einmaliges Setup (dein Browser nötig)

```bash
npx wrangler login          # öffnet Cloudflare-OAuth im Browser (Account anlegen ist gratis)
./scripts/deploy-worker.sh  # deployt den Worker + schreibt seine URL nach .env
./scripts/deploy.sh         # baut die Site MIT dem Worker (window.TWDL_PROXY) + deployt
```

Danach geht 100 % des Medien-Traffics über Cloudflare; die Netlify-Bandbreite fällt auf ~0.
`deploy-worker.sh` trägt `TWITCHDL_PROXY_BASE=https://vodfetch-proxy.<sub>.workers.dev`
in `.env` ein; jeder weitere `./scripts/deploy.sh` nutzt den Worker automatisch.

## Architektur

- `cloudflare/worker.js` — der Streaming-Proxy (Host-Allowlist, Origin/Referer-Lock,
  IP-Block, Rate-Limit, Range/CORS). Fachlich identisch zur Netlify-Function, nur streamend.
- `cloudflare/wrangler.toml` — Worker-Config (Name `vodfetch-proxy`, `workers.dev`-Subdomain,
  kein DNS-Umzug nötig — die Domain bleibt bei Netlify/NS1).
- Client (`webapp.py`): `P()` nutzt `window.TWDL_PROXY` (aus `TWITCHDL_PROXY_BASE`), sonst
  Fallback auf `/api/tw` (Netlify). Cutover passiert beim Build.

## Fallback / Rückrollen

`netlify/functions/tw.js` bleibt als Sicherheitsnetz deployt (kostet ungenutzt nichts).
Zum Zurückrollen: `TWITCHDL_PROXY_BASE` aus `.env` entfernen und `./scripts/deploy.sh` —
der Client fällt wieder auf `/api/tw` zurück.

## Missbrauch / IP-Block

Blockierte IPs stehen in `worker.js` (`IP_BLOCK`) **und** `netlify/functions/tw.js` synchron
halten. Cloudflare-seitig lassen sich zusätzlich Dashboard-Rate-Limiting-Rules ergänzen —
aber da Bandbreite dort gratis ist, ist der Kostendruck weg. Siehe Memory
`proxy-cost-abuse-incident`.
