// vodfetch Medien-Proxy — Cloudflare Worker.
//
// Ersetzt die Netlify-Function netlify/functions/tw.js. Grund: Cloudflare berechnet
// KEINE Egress-Bandbreite (Netlifys teurer Posten), Free-Tier 100k req/Tag, danach
// 5$/Monat für 10M. Der Worker STREAMT die Antwort (kein 5,4-MB-Cap, kein Base64).
//
// Nur Twitch-MEDIEN-Hosts (Usher-Playlists, HLS-Segmente, Clip-MP4s), die selbst
// kein CORS senden. GraphQL läuft NICHT hierüber — der Client spricht gql.twitch.tv
// direkt an (ACAO:*).  Aufruf: GET https://<worker>/?url=<encoded media url>

const ALLOW_EXACT = new Set(["usher.ttvnw.net"]);
const ALLOW_SUFFIX = [".ttvnw.net", ".cloudfront.net", ".twitchcdn.net", ".twitch.tv"];

// Erlaubte eigene Herkünfte (Origin- ODER Referer-Host).
const SELF_EXACT = new Set(["vodfetch.com", "www.vodfetch.com", "localhost", "127.0.0.1"]);
const SELF_SUFFIX = [".netlify.app"];

// Missbraucher-IPs (siehe proxy-cost-abuse-incident). Erweitern bei IP-Rotation.
const IP_BLOCK = new Set(["77.73.131.147"]);

// Leichte Rate-Bremse pro Isolate. Cloudflare-Bandbreite ist gratis, daher weniger
// kritisch als bei Netlify — Cloudflare-Dashboard-Rate-Limiting-Rules ergänzen bei Bedarf.
const RL = new Map(); // ip -> {n,t}
const RL_WINDOW_MS = 10_000;
const RL_MAX = 240;

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36";

function hostOf(v) { try { return new URL(v).hostname.toLowerCase(); } catch (e) { return ""; } }
function selfHost(h) { if (!h) return false; h = h.toLowerCase(); return SELF_EXACT.has(h) || SELF_SUFFIX.some((s) => h.endsWith(s)); }
function mediaAllowed(h) { h = h.toLowerCase(); if (h === "gql.twitch.tv") return false; return ALLOW_EXACT.has(h) || ALLOW_SUFFIX.some((s) => h.endsWith(s)); }

function fromOurSite(req) {
  const o = req.headers.get("origin");
  const r = req.headers.get("referer");
  if (o && selfHost(hostOf(o))) return true;
  if (r && selfHost(hostOf(r))) return true;
  return false;
}

function corsHeaders(req) {
  const o = req.headers.get("origin");
  const allow = (o && selfHost(hostOf(o))) ? o : "https://vodfetch.com";
  return {
    "Access-Control-Allow-Origin": allow,
    "Vary": "Origin",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Range, Content-Type",
    "Access-Control-Expose-Headers": "Content-Length, Content-Range, Content-Type, Accept-Ranges",
    "Access-Control-Max-Age": "86400",
  };
}

function rateLimited(ip) {
  if (!ip) return false;
  const now = Date.now();
  const e = RL.get(ip);
  if (!e || now - e.t > RL_WINDOW_MS) { RL.set(ip, { n: 1, t: now }); return false; }
  e.n++;
  if (RL.size > 5000) RL.clear();
  return e.n > RL_MAX;
}

export default {
  async fetch(request) {
    const cors = corsHeaders(request);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "GET") return new Response("method not allowed", { status: 405, headers: cors });

    const ip = request.headers.get("cf-connecting-ip") || "";
    if (IP_BLOCK.has(ip)) return new Response("forbidden", { status: 403, headers: { Vary: "Origin, Referer" } });
    if (!fromOurSite(request)) return new Response("forbidden", { status: 403, headers: { Vary: "Origin, Referer" } });
    if (rateLimited(ip)) return new Response("rate limited", { status: 429, headers: { ...cors, "Retry-After": "30" } });

    const target = new URL(request.url).searchParams.get("url");
    if (!target) return new Response("missing url", { status: 400, headers: cors });

    let u;
    try { u = new URL(target); } catch (e) { return new Response("bad url", { status: 400, headers: cors }); }
    if (u.protocol !== "https:") return new Response("https only", { status: 400, headers: cors });
    if (!mediaAllowed(u.hostname)) return new Response("host not allowed", { status: 403, headers: cors });

    const fwd = { "User-Agent": UA };
    const range = request.headers.get("range");
    if (range) fwd["Range"] = range;

    let upstream;
    try {
      upstream = await fetch(target, { method: "GET", headers: fwd, redirect: "follow" });
    } catch (e) {
      return new Response("upstream error", { status: 502, headers: cors });
    }

    // Antwort STREAMEN (kein Buffern, kein Größenlimit).
    const out = new Headers(cors);
    out.set("Content-Type", upstream.headers.get("content-type") || "application/octet-stream");
    const cr = upstream.headers.get("content-range"); if (cr) out.set("Content-Range", cr);
    const ar = upstream.headers.get("accept-ranges"); if (ar) out.set("Accept-Ranges", ar);
    const cl = upstream.headers.get("content-length"); if (cl) out.set("Content-Length", cl);
    out.set("Cache-Control", "no-store");

    return new Response(upstream.body, { status: upstream.status, headers: out });
  },
};
