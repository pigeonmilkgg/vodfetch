// Schlanker, zustandsloser CORS-Proxy — NUR für Twitch-Hosts (SSRF-sicher).
// Erlaubt dem Browser, Usher-Playlists und HLS-Segmente / Clip-MP4s zu laden,
// die selbst keine CORS-Header senden. Pro Aufruf nur ein kleiner Range/Segment.

const ALLOW_EXACT = new Set([
  "gql.twitch.tv",
  "usher.ttvnw.net",
]);
const ALLOW_SUFFIX = [
  ".ttvnw.net",
  ".cloudfront.net",
  ".twitchcdn.net",
  ".twitch.tv",
];

// Nur die eigene Site darf den Proxy cross-origin nutzen. Same-Origin-GETs senden
// keinen Origin-Header (das /api/tw-Redirect ist ein 200-Rewrite) — die bleiben erlaubt.
// Fremde Websites, die /api/tw hotlinken, senden immer einen Origin → 403.
const ORIGIN_EXACT = new Set([
  "https://vodfetch.com",
  "https://www.vodfetch.com",
  "https://cozy-crumble-bff916.netlify.app",
]);
const ORIGIN_SUFFIX = ["--cozy-crumble-bff916.netlify.app"]; // Deploy-Previews
const ORIGIN_DEV = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;

function originAllowed(origin) {
  if (!origin) return true; // same-origin / non-browser: kein Origin-Header
  try {
    const o = origin.toLowerCase();
    if (ORIGIN_EXACT.has(o)) return true;
    if (ORIGIN_DEV.test(o)) return true;
    const host = new URL(o).hostname;
    return ORIGIN_SUFFIX.some((s) => host.endsWith(s));
  } catch (e) {
    return false;
  }
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "https://vodfetch.com",
    "Vary": "Origin",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Client-Id, Client-ID, Range",
    "Access-Control-Expose-Headers": "Content-Length, Content-Range, Content-Type, Accept-Ranges",
  };
}

function allowed(host) {
  host = host.toLowerCase();
  if (ALLOW_EXACT.has(host)) return true;
  return ALLOW_SUFFIX.some((s) => host.endsWith(s));
}

exports.handler = async (event) => {
  const origin = (event.headers && (event.headers.origin || event.headers.Origin)) || "";
  if (!originAllowed(origin)) {
    return { statusCode: 403, headers: { "Vary": "Origin" }, body: "origin not allowed" };
  }
  const CORS = corsHeaders(origin);
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };

  const target = event.queryStringParameters && event.queryStringParameters.url;
  if (!target) return { statusCode: 400, headers: CORS, body: "missing url" };

  let u;
  try { u = new URL(target); } catch (e) { return { statusCode: 400, headers: CORS, body: "bad url" }; }
  if (u.protocol !== "https:") return { statusCode: 400, headers: CORS, body: "https only" };
  if (!allowed(u.hostname)) return { statusCode: 403, headers: CORS, body: "host not allowed" };

  const headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36" };
  if (event.headers && (event.headers.range || event.headers.Range))
    headers["Range"] = event.headers.range || event.headers.Range;

  const method = event.httpMethod === "POST" ? "POST" : "GET";
  let body;
  if (method === "POST") {
    headers["Content-Type"] = "application/json";
    const cid = event.headers["client-id"] || event.headers["client-ID"] || event.headers["Client-ID"];
    if (cid) headers["Client-ID"] = cid;
    else if (u.hostname.toLowerCase() === "gql.twitch.tv") headers["Client-ID"] = "kimne78kx3ncx6brgo4mv6wki5h1ko";
    body = event.isBase64Encoded ? Buffer.from(event.body || "", "base64").toString("utf8") : event.body;
  }

  let resp;
  try {
    resp = await fetch(target, { method, headers, body });
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
