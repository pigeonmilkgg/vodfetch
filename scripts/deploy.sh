#!/usr/bin/env bash
# Kanonischer Build+Deploy+IndexNow-Lauf für vodfetch.com.
# Kodiert die eine korrekte Befehlsfolge aus CLAUDE.md — frühere Abkürzungen haben
# Bing-Verify/sameAs gedroppt und IndexNow gegen die netlify.app-Subdomain gepingt.
#
# Nutzung:  ./scripts/deploy.sh            # Build + Secret-Grep + Deploy + IndexNow
#           ./scripts/deploy.sh --build-only
set -euo pipefail
cd "$(dirname "$0")/.."

SITE_ID="339599ca-2663-425a-82b0-c2964f96a65d"
export TWITCHDL_BASE_URL="https://vodfetch.com"
export TWITCHDL_SAMEAS="https://github.com/pigeonmilkgg/vodfetch"
export TWITCHDL_REPO="https://github.com/pigeonmilkgg/vodfetch"
export TWITCHDL_BING_VERIFY="DD10C1E27169A8BD038386A868573443"

# Lokale Secrets + Config laden (u.a. TWITCHDL_PROXY_BASE für den Cloudflare-Worker)
if [ -f .env ]; then set -a; . ./.env; set +a; fi

if [ -n "${TWITCHDL_PROXY_BASE:-}" ]; then
  echo "==> Medien-Proxy: Cloudflare Worker ($TWITCHDL_PROXY_BASE)"
else
  echo "==> Medien-Proxy: Netlify-Fallback /api/tw (TWITCHDL_PROXY_BASE nicht gesetzt)"
fi

echo "==> Build (alle Env-Vars gesetzt)"
./.venv/bin/python build_static.py

echo "==> Secret-Grep über dist/"
FOUND=""
for VAL in "${TWITCH_HELIX_CLIENT_SECRET:-}" "${TWITCH_HELIX_CLIENT_ID:-}" "${NETLIFY_AUTH_TOKEN:-}"; do
  if [ -n "$VAL" ] && grep -rqF "$VAL" dist/; then FOUND="$VAL"; fi
done
if grep -rqiE "client_secret|BEGIN (RSA|OPENSSH) PRIVATE KEY" dist/; then FOUND="pattern:client_secret/private-key"; fi
if [ -n "$FOUND" ]; then
  echo "ABBRUCH: Secret im Build gefunden ($FOUND) — dist/ NICHT deployen." >&2
  exit 1
fi
echo "    sauber."

if [ "${1:-}" = "--build-only" ]; then echo "==> --build-only: fertig."; exit 0; fi

echo "==> Deploy (Direct-Upload, --no-build zwingend)"
netlify deploy --prod --dir=dist --functions=netlify/functions --no-build --site="$SITE_ID"

echo "==> Live-Verify"
for P in "/" "/sitemap.xml" "/llms.txt"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://vodfetch.com$P")
  echo "    $P -> $CODE"
  [ "$CODE" = "200" ] || { echo "ABBRUCH: $P liefert $CODE" >&2; exit 1; }
done

echo "==> IndexNow (Base-URL zwingend gesetzt)"
TWITCHDL_BASE_URL="https://vodfetch.com" ./.venv/bin/python submit_indexnow.py

echo "==> Fertig."
