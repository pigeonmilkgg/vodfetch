#!/usr/bin/env bash
# Deployt den Medien-Proxy als Cloudflare Worker und schreibt seine URL nach .env
# (TWITCHDL_PROXY_BASE), sodass der nächste ./scripts/deploy.sh die Site auf 100%
# Cloudflare umstellt (keine Netlify-Bandbreite mehr).
#
# Einmalige Vorbereitung (dein Browser, ich kann das nicht):
#   npx wrangler login          # öffnet Cloudflare-OAuth im Browser
# Dann:
#   ./scripts/deploy-worker.sh  # deployt + schreibt die URL in .env
#   ./scripts/deploy.sh         # baut + deployt die Site mit dem Worker
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Cloudflare-Login prüfen"
if ! npx --yes wrangler whoami >/dev/null 2>&1; then
  echo "NICHT eingeloggt. Bitte einmalig ausführen:  npx wrangler login" >&2
  exit 1
fi

echo "==> Worker deployen"
DEPLOY_OUT="$(cd cloudflare && npx --yes wrangler deploy 2>&1)"
echo "$DEPLOY_OUT"

# URL aus der Wrangler-Ausgabe ziehen (…workers.dev)
URL="$(printf '%s\n' "$DEPLOY_OUT" | grep -oE 'https://[a-z0-9._-]*workers\.dev' | head -1)"
if [ -z "$URL" ]; then
  echo "WARN: Worker-URL nicht automatisch erkannt. Bitte aus der Ausgabe oben kopieren und" >&2
  echo "      in .env als TWITCHDL_PROXY_BASE=... eintragen." >&2
  exit 1
fi

echo "==> Worker live: $URL"

# .env aktualisieren/erzeugen
touch .env
if grep -q '^TWITCHDL_PROXY_BASE=' .env; then
  # bestehenden Wert ersetzen (portabel, ohne sed -i Eigenheiten)
  grep -v '^TWITCHDL_PROXY_BASE=' .env > .env.tmp || true
  mv .env.tmp .env
fi
printf 'TWITCHDL_PROXY_BASE=%s\n' "$URL" >> .env
echo "==> .env aktualisiert: TWITCHDL_PROXY_BASE=$URL"

# Schnelltest: Worker antwortet (403 ohne Origin ist ERWÜNSCHT = Schutz aktiv)
echo "==> Smoke-Test (403 ohne Origin = korrekt):"
curl -s -o /dev/null -w "   no-origin -> %{http_code}\n" "$URL/?url=https%3A%2F%2Fusher.ttvnw.net%2Fvod%2F1.m3u8" || true
curl -s -o /dev/null -w "   with-origin -> %{http_code} (Upstream-Code, nicht 403)\n" -H "Origin: https://vodfetch.com" "$URL/?url=https%3A%2F%2Fusher.ttvnw.net%2Fvod%2F1.m3u8" || true

echo "==> Fertig. Jetzt:  ./scripts/deploy.sh   (baut die Site mit dem Worker)"
