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

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Client-Id, Client-ID, Range",
  "Access-Control-Expose-Headers": "Content-Length, Content-Range, Content-Type, Accept-Ranges",
};

function allowed(host) {
  host = host.toLowerCase();
  if (ALLOW_EXACT.has(host)) return true;
  return ALLOW_SUFFIX.some((s) => host.endsWith(s));
}

exports.handler = async (event) => {
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
