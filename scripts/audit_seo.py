#!/usr/bin/env python3
"""Tiefer On-Page-/AEO-Audit über dist/ — deterministisch, ohne Urteilsfragen.

Ergänzt audit_dist.py (Link-Graph, Canonicals, JSON-LD-Refs) um alles, was für
Rankings und Maschinenlesbarkeit zählt: Titel-/Description-Längen und -Dubletten,
Überschriftenstruktur, Bild-Alt, Open Graph/Twitter, Klicktiefe, Sitemap-Abgleich,
Schema-Abdeckung, Wortzahl, interne Verlinkung.

Aufruf:  python3 scripts/audit_seo.py [--fix-hints]
Exit 0 nur ohne ERROR-Befunde (WARN ist Information).
"""
from __future__ import annotations

import collections
import html
import json
import pathlib
import re
import sys
from html.parser import HTMLParser

DIST = pathlib.Path(__file__).resolve().parent.parent / "dist"
BASE = "https://vodfetch.com"

ERR: list = []
WARN: list = []
INFO: list = []


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._t = False
        self.metas: dict = {}
        self.og: dict = {}
        self.canonical = ""
        self.lang = ""
        self.h: list = []
        self._grab = None
        self.links: list = []
        self.imgs: list = []
        self.jsonld: list = []
        self._ld = False
        self._buf: list = []
        self.text_len = 0
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self._t = True
        elif tag == "meta":
            if a.get("name"):
                self.metas[a["name"].lower()] = a.get("content", "")
            if a.get("property", "").startswith("og:"):
                self.og[a["property"]] = a.get("content", "")
            if a.get("name", "").startswith("twitter:"):
                self.og[a["name"]] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href", "")
        elif tag == "a" and a.get("href"):
            self.links.append((a["href"], a.get("rel", "")))
        elif tag == "img":
            self.imgs.append(a)
        elif tag in ("script", "style", "nav", "header", "footer"):
            self._skip += 1
            if tag == "script" and a.get("type") == "application/ld+json":
                self._ld = True
                self._buf = []
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.h.append([int(tag[1]), ""])
            self._grab = len(self.h) - 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._t = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._grab = None
        elif tag in ("script", "style", "nav", "header", "footer"):
            self._skip = max(0, self._skip - 1)
            if tag == "script" and self._ld:
                self._ld = False
                self.jsonld.append("".join(self._buf))

    def handle_data(self, d):
        if self._t:
            self.title += d
        if self._grab is not None:
            self.h[self._grab][1] += d
        if self._ld:
            self._buf.append(d)
        if not self._skip:
            self.text_len += len(d.split())


def url_of(f: pathlib.Path) -> str:
    rel = f.relative_to(DIST).as_posix()
    if rel == "index.html":
        return "/"
    return "/" + rel[:-5]


def main() -> int:
    files = [f for f in sorted(DIST.rglob("*.html")) if f.name != "404.html"]
    pages: dict = {}
    for f in files:
        p = P()
        try:
            p.feed(f.read_text(encoding="utf-8"))
        except Exception as e:
            ERR.append(f"{url_of(f)}: parse {e}")
            continue
        pages[url_of(f)] = p

    # ---- Titel & Description -------------------------------------------------
    t_seen = collections.defaultdict(list)
    d_seen = collections.defaultdict(list)
    for u, p in pages.items():
        t = p.title.strip()
        d = p.metas.get("description", "").strip()
        t_seen[t].append(u)
        d_seen[d].append(u)
        if not t:
            ERR.append(f"{u}: kein <title>")
        elif len(t) > 65:
            WARN.append(f"{u}: title {len(t)} Zeichen (>65, wird gekürzt)")
        elif len(t) < 25:
            WARN.append(f"{u}: title nur {len(t)} Zeichen")
        if not d:
            ERR.append(f"{u}: keine meta description")
        elif not (110 <= len(d) <= 165):
            WARN.append(f"{u}: description {len(d)} Zeichen (Ziel 110-165)")
    for t, us in t_seen.items():
        if t and len(us) > 1:
            ERR.append(f"doppelter title {t[:50]!r}: {us[:3]}")
    for d, us in d_seen.items():
        if d and len(us) > 1:
            ERR.append(f"doppelte description: {us[:3]}")

    # ---- Überschriften -------------------------------------------------------
    for u, p in pages.items():
        h1 = [x for x in p.h if x[0] == 1]
        if len(h1) != 1:
            ERR.append(f"{u}: {len(h1)} H1")
        elif not h1[0][1].strip():
            ERR.append(f"{u}: H1 leer")
        prev = 0
        for lvl, _ in p.h:
            if prev and lvl > prev + 1:
                ERR.append(f"{u}: Sprung H{prev}->H{lvl}")
            prev = lvl
        empty = [f"H{l}" for l, txt in p.h if not txt.strip()]
        if empty:
            WARN.append(f"{u}: leere Überschriften {empty[:3]}")

    # ---- Bilder --------------------------------------------------------------
    for u, p in pages.items():
        for img in p.imgs:
            if "alt" not in img:
                ERR.append(f"{u}: <img> ohne alt ({img.get('src','?')[:50]})")
            if not img.get("loading") and "avatar" not in (img.get("class") or ""):
                INFO.append(f"{u}: <img> ohne loading=lazy")

    # ---- Open Graph / Twitter ------------------------------------------------
    need_og = ["og:title", "og:description", "og:image", "og:url", "og:type"]
    for u, p in pages.items():
        miss = [k for k in need_og if not p.og.get(k)]
        if miss:
            WARN.append(f"{u}: fehlende OG-Tags {miss}")
        if not p.og.get("twitter:card"):
            WARN.append(f"{u}: kein twitter:card")

    # ---- Klicktiefe von der Startseite ---------------------------------------
    graph = collections.defaultdict(set)
    for u, p in pages.items():
        for href, _rel in p.links:
            if href.startswith(BASE):
                href = href[len(BASE):] or "/"
            if not href.startswith("/"):
                continue
            h = href.split("#")[0].split("?")[0]
            if h in pages:
                graph[u].add(h)
    depth = {"/": 0}
    q = collections.deque(["/"])
    while q:
        cur = q.popleft()
        for nxt in graph.get(cur, ()):
            if nxt not in depth:
                depth[nxt] = depth[cur] + 1
                q.append(nxt)
    deep = {u: d for u, d in depth.items() if d > 3}
    unreach = [u for u in pages if u not in depth]
    for u in unreach:
        ERR.append(f"von der Startseite unerreichbar: {u}")
    for u, d in sorted(deep.items(), key=lambda kv: -kv[1])[:10]:
        WARN.append(f"Klicktiefe {d}: {u}")

    inbound = collections.Counter()
    for u, outs in graph.items():
        for t in outs:
            inbound[t] += 1
    for u in pages:
        if u != "/" and inbound[u] <= 1:
            WARN.append(f"nur {inbound[u]} interne(r) Link auf {u}")

    # ---- Sitemap -------------------------------------------------------------
    sm = DIST / "sitemap.xml"
    if not sm.exists():
        ERR.append("sitemap.xml fehlt")
    else:
        locs = set(re.findall(r"<loc>(.*?)</loc>", sm.read_text()))
        sm_paths = {l[len(BASE):] or "/" for l in locs if l.startswith(BASE)}
        for u, p in pages.items():
            noindex = "noindex" in p.metas.get("robots", "")
            canon_self = p.canonical.rstrip("/") == (BASE + ("" if u == "/" else u)).rstrip("/")
            if u in sm_paths and noindex:
                ERR.append(f"in Sitemap trotz noindex: {u}")
            if u in sm_paths and not canon_self:
                ERR.append(f"in Sitemap, aber canonical zeigt woanders: {u}")
            if u not in sm_paths and canon_self and not noindex:
                WARN.append(f"indexierbar, aber NICHT in der Sitemap: {u}")
        for sp in sm_paths - set(pages):
            ERR.append(f"Sitemap-Eintrag ohne Datei: {sp}")

    # ---- Schema-Abdeckung ----------------------------------------------------
    for u, p in pages.items():
        if not p.jsonld:
            ERR.append(f"{u}: kein JSON-LD")
            continue
        try:
            g = json.loads(p.jsonld[0]).get("@graph", [])
        except Exception as e:
            ERR.append(f"{u}: JSON-LD kaputt {e}")
            continue
        types = set()
        for n in g:
            t = n.get("@type")
            types |= set(t) if isinstance(t, list) else {t}
        if "BreadcrumbList" not in types and u != "/":
            WARN.append(f"{u}: keine BreadcrumbList")
        if not ({"WebPage", "CollectionPage", "ProfilePage", "AboutPage"} & types):
            WARN.append(f"{u}: kein WebPage-Typ")

    # ---- Dünne Seiten --------------------------------------------------------
    for u, p in pages.items():
        if p.text_len < 250:
            WARN.append(f"{u}: nur {p.text_len} Wörter Fließtext")

    # ---- Maschinendateien ----------------------------------------------------
    for name in ("robots.txt", "llms.txt", "llms-full.txt", "ai.txt", "ai.json",
                 "facts.md", "facts.json", "feed.xml", "site.webmanifest",
                 ".well-known/ai.json", ".well-known/llms.txt"):
        if not (DIST / name).exists():
            ERR.append(f"Maschinendatei fehlt: {name}")
    rb = (DIST / "robots.txt")
    if rb.exists():
        txt = rb.read_text()
        if f"Sitemap: {BASE}/sitemap.xml" not in txt:
            ERR.append("robots.txt: Sitemap-Zeile fehlt oder falscher Host")
        if re.search(r"^Disallow: /\s*$", txt, re.M):
            ERR.append("robots.txt: Disallow: / — Seite komplett gesperrt!")

    print(f"Seiten: {len(pages)} · Kanten: {sum(len(v) for v in graph.values())} · "
          f"max. Klicktiefe: {max(depth.values()) if depth else '-'}")
    print(f"\nERROR {len(ERR)} · WARN {len(WARN)} · INFO {len(INFO)}\n")
    for e in ERR[:60]:
        print("ERROR", e)
    for w in WARN[:40]:
        print("WARN ", w)
    if len(WARN) > 40:
        print(f"WARN  … und {len(WARN)-40} weitere")
    return 1 if ERR else 0


if __name__ == "__main__":
    sys.exit(main())
