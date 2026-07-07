// Schlanker, zustandsloser CORS-Proxy — NUR für Twitch-MEDIEN-Hosts (SSRF-sicher).
// Erlaubt dem Browser, Usher-Playlists und HLS-Segmente / Clip-MP4s zu laden,
// die selbst keine CORS-Header senden. GraphQL (gql.twitch.tv) läuft NICHT mehr
// über diesen Proxy — der Client spricht gql.twitch.tv direkt an (ACAO:* verifiziert).
//
// MISSBRAUCHSSCHUTZ (2026-07-07): Ohne diese Prüfung konnte jedes Fremd-Script
// /api/tw als kostenlosen Twitch-Download-Proxy benutzen (No-Origin-Requests kamen
// durch) → durchgehend ~5 Invocations/s, laufende Netlify-Kosten. Jetzt gilt:
// nur Requests mit unserem Origin ODER unserem Referer werden bedient.

const ALLOW_EXACT = new Set([
  "usher.ttvnw.net",
]);
const ALLOW_SUFFIX = [
  ".ttvnw.net",
  ".cloudfront.net",
  ".twitchcdn.net",
  ".twitch.tv",
];

// Erlaubte eigene Hosts (Origin- ODER Referer-Host muss matchen).
const SELF_EXACT = new Set(["vodfetch.com", "www.vodfetch.com", "localhost", "127.0.0.1"]);
const SELF_SUFFIX = [".netlify.app"]; // Prod-Fallback-Domain + Deploy-Previews

// IP-Blocklist: Missbraucher, die den Proxy als kostenloses Download-Backend nutzen
// (Referer + UA gespooft, ~5 req/s rund um die Uhr). Diagnostiziert 2026-07-07.
// Erweitern, falls jemand IPs rotiert; dauerhafter Fix wäre CF-Workers/Bot-Management.
const IP_BLOCK = new Set([
  "77.73.131.147",
]);

// Leichte Rate-Bremse pro Function-Instanz: verhindert, dass EINE IP im selben
// Instanz-Fenster den Proxy flutet. Legitime Downloads laufen parallel, aber ein
// Dauer-Scraper wird gedrosselt. (Instanz-lokal — kein perfekter globaler Limiter.)
const RL = new Map(); // ip -> { n, t }
const RL_WINDOW_MS = 10_000;
const RL_MAX = 120; // >> als ein echter Parallel-Download braucht, << Dauer-Flut
function rateLimited(ip) {
  if (!ip || ip === "-") return false;
  const now = Date.now();
  const e = RL.get(ip);
  if (!e || now - e.t > RL_WINDOW_MS) { RL.set(ip, { n: 1, t: now }); return false; }
  e.n++;
  if (RL.size > 5000) RL.clear(); // Speicher-Leck-Schutz
  return e.n > RL_MAX;
}

function selfHost(host) {
  if (!host) return false;
  host = host.toLowerCase();
  if (SELF_EXACT.has(host)) return true;
  return SELF_SUFFIX.some((s) => host.endsWith(s));
}

function hostOf(value) {
  try { return new URL(value).hostname.toLowerCase(); } catch (e) { return ""; }
}

// Zugriff nur, wenn der Request nachweislich von unserer Seite kommt:
// Origin-Header (cross-origin fetch) ODER Referer-Header (same-origin fetch schickt
// dank Referrer-Policy strict-origin-when-cross-origin die volle URL). Ein Scraper
// ohne beide Header wird abgewiesen.
function fromOurSite(headers) {
  const origin = headers.origin || headers.Origin || "";
  const referer = headers.referer || headers.Referer || "";
  if (origin && selfHost(hostOf(origin))) return true;
  if (referer && selfHost(hostOf(referer))) return true;
  return false;
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": (origin && selfHost(hostOf(origin))) ? origin : "https://vodfetch.com",
    "Vary": "Origin",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Range",
    "Access-Control-Expose-Headers": "Content-Length, Content-Range, Content-Type, Accept-Ranges",
  };
}

function allowed(host) {
  host = host.toLowerCase();
  if (ALLOW_EXACT.has(host)) return true;
  return ALLOW_SUFFIX.some((s) => host.endsWith(s));
}

exports.handler = async (event) => {
  const headers = event.headers || {};
  const origin = headers.origin || headers.Origin || "";
  const CORS = corsHeaders(origin);

  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };

  const ip = headers["x-nf-client-connection-ip"] || headers["x-forwarded-for"] || "-";

  // Geblockte Missbraucher-IPs sofort abweisen (kein Upstream, keine Bandbreite).
  if (IP_BLOCK.has(ip)) {
    return { statusCode: 403, headers: { "Vary": "Origin, Referer" }, body: "forbidden" };
  }

  // Nur eigene Seite darf den Proxy nutzen (Origin ODER Referer von uns).
  if (!fromOurSite(headers)) {
    return { statusCode: 403, headers: { "Vary": "Origin, Referer" }, body: "forbidden" };
  }

  // Dauer-Flut einer einzelnen IP drosseln.
  if (rateLimited(ip)) {
    return { statusCode: 429, headers: { ...CORS, "Retry-After": "30" }, body: "rate limited" };
  }

  const target = event.queryStringParameters && event.queryStringParameters.url;
  if (!target) return { statusCode: 400, headers: CORS, body: "missing url" };

  let u;
  try { u = new URL(target); } catch (e) { return { statusCode: 400, headers: CORS, body: "bad url" }; }
  if (u.protocol !== "https:") return { statusCode: 400, headers: CORS, body: "https only" };
  if (!allowed(u.hostname)) return { statusCode: 403, headers: CORS, body: "host not allowed" };

  const fwd = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36" };
  if (headers.range || headers.Range) fwd["Range"] = headers.range || headers.Range;

  let resp;
  try {
    resp = await fetch(target, { method: "GET", headers: fwd });
  } catch (e) {
    return { statusCode: 502, headers: CORS, body: "upstream error: " + String(e).slice(0, 120) };
  }

  const ab = await resp.arrayBuffer();
  const buf = Buffer.from(ab);
  // Netlify-Funktionen: max ~6 MB Antwort. Segmente/Range-Chunks bleiben klar darunter.
  if (buf.length > 5_400_000) {
    return { statusCode: 413, headers: CORS, body: "chunk too large — use smaller Range" };
  }

  const out = { ...CORS, "Content-Type": resp.headers.get("content-type") || "application/octet-stream" };
  const cr = resp.headers.get("content-range");
  if (cr) out["Content-Range"] = cr;
  const ar = resp.headers.get("accept-ranges");
  if (ar) out["Accept-Ranges"] = ar;

  return { statusCode: resp.status, headers: out, body: buf.toString("base64"), isBase64Encoded: true };
};
