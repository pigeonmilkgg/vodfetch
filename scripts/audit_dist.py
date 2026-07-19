#!/usr/bin/env python3
"""dist/-Audit: On-Page + Link-Graph + Schema + Canonical (mit Cross-Canonical-Support).

Teil des Deploy-Rituals: nach dem Build, vor dem Deploy laufen lassen.
Exit 0 nur, wenn keine harten Fehler gefunden werden.
"""
from __future__ import annotations
import json, pathlib, re, sys
from collections import defaultdict
from html.parser import HTMLParser

DIST = pathlib.Path(__file__).resolve().parent.parent / "dist"
BASE = "https://vodfetch.com"
ERR, WARN = [], []
def err(m): ERR.append(m)
def warn(m): WARN.append(m)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h = []; self._grab = None; self.title = ""; self._in_title = False
        self.metas = {}; self.canonical = ""; self.lang = ""; self.links = []
        self.jsonld = []; self._in_ld = False; self._ld_buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html": self.lang = a.get("lang", "")
        elif tag == "title": self._in_title = True
        elif tag == "meta":
            if a.get("name"): self.metas[a["name"].lower()] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical": self.canonical = a.get("href", "")
        elif tag == "a" and a.get("href"): self.links.append(a["href"])
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.h.append([int(tag[1]), ""]); self._grab = len(self.h) - 1
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True; self._ld_buf = []

    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"): self._grab = None
        elif tag == "script" and self._in_ld:
            self._in_ld = False; self.jsonld.append("".join(self._ld_buf))

    def handle_data(self, d):
        if self._in_title: self.title += d
        if self._grab is not None: self.h[self._grab][1] += d
        if self._in_ld: self._ld_buf.append(d)


def url_of(f):
    rel = f.relative_to(DIST).as_posix()
    if rel == "index.html": return "/"
    if rel == "404.html": return "/404"
    return "/" + rel[:-5]

def file_of(url):
    url = url.split("#")[0].split("?")[0]
    if url in ("", "/"): return DIST / "index.html"
    p = url.lstrip("/")
    for cand in (DIST / (p + ".html"), DIST / p):
        if cand.exists() and cand.is_file(): return cand
    return None

def refs_of(o):
    if isinstance(o, dict):
        if set(o.keys()) == {"@id"}: yield o["@id"]
        else:
            for v in o.values(): yield from refs_of(v)
    elif isinstance(o, list):
        for v in o: yield from refs_of(v)


def main():
    pages = sorted(DIST.rglob("*.html"))
    inbound = defaultdict(set); graph = defaultdict(set); titles = defaultdict(lambda: defaultdict(list))
    for f in pages:
        u = url_of(f); is404 = f.name == "404.html"
        p = Page()
        try: p.feed(f.read_text(encoding="utf-8"))
        except Exception as e: err(f"{u}: parse {e}"); continue
        if len([x for x in p.h if x[0] == 1]) != 1: err(f"{u}: h1 count")
        prev = 0
        for lvl, _ in p.h:
            if prev and lvl > prev + 1: err(f"{u}: heading jump h{prev}->h{lvl}")
            prev = lvl
        if not p.title.strip(): err(f"{u}: empty title")
        if not is404: titles[p.lang][p.title.strip()].append(u)
        desc = p.metas.get("description", "")
        if not is404 and not (40 <= len(desc) <= 175): (warn if desc else err)(f"{u}: meta len {len(desc)}")
        # noindex nur auf Boilerplate-Übersetzungen erlaubt (falls Mehrsprachigkeit reaktiviert wird)
        _ok_noindex = bool(re.match(r"^/[a-z-]{2,5}/(editorial-policy|how-this-site-is-built)$", u))
        if "noindex" in p.metas.get("robots", "") and not _ok_noindex: err(f"{u}: noindex")
        if not p.lang: err(f"{u}: no html lang")
        if not is404:
            self_url = BASE + ("/" if u == "/" else u)
            can = p.canonical
            if can.rstrip("/") == self_url.rstrip("/"):
                pass
            elif can.startswith(BASE):
                if file_of(can[len(BASE):]) is None: err(f"{u}: cross-canonical target missing {can}")
            else:
                err(f"{u}: bad canonical {can!r}")
        if not is404 and len(p.jsonld) != 1: err(f"{u}: {len(p.jsonld)} jsonld")
        for raw in p.jsonld:
            try: d = json.loads(raw)
            except Exception as e: err(f"{u}: invalid jsonld {e}"); continue
            g = d.get("@graph")
            if not isinstance(g, list): err(f"{u}: no @graph"); continue
            ids = {n.get("@id") for n in g if isinstance(n, dict) and n.get("@id")}
            for r in refs_of(g):
                if r not in ids: err(f"{u}: dangling @id {r}")
        for href in p.links:
            if href.startswith(("http://", "https://")):
                if href.startswith(BASE): href = href[len(BASE):] or "/"
                else: continue
            if href.startswith(("mailto:", "javascript:", "#")): continue
            c = href.split("#")[0].split("?")[0]
            if not c or c.startswith("/api/"): continue
            if c != "/" and c.endswith("/"): err(f"{u}: trailing-slash link {href}")
            tgt = file_of(c)
            if tgt is None: err(f"{u}: broken link {href}")
            elif tgt.suffix == ".html":
                tu = url_of(tgt); inbound[tu].add(u); graph[u].add(tu)
    for lang, tm in titles.items():
        for title, urls in tm.items():
            if len(urls) > 1: err(f"dup title [{lang}] {title!r}: {urls[:4]}")
    all_urls = {url_of(f) for f in pages if f.name != "404.html"}
    for u in sorted(all_urls):
        if u != "/" and not inbound.get(u): err(f"orphan: {u}")
    sm = DIST / "sitemap.xml"
    locs = set(re.findall(r"<loc>(.*?)</loc>", sm.read_text())) if sm.exists() else set()
    for loc in locs:
        if file_of(loc[len(BASE):] or "/") is None: err(f"sitemap loc missing file: {loc}")
    print(f"pages: {len(pages)} | sitemap locs: {len(locs)} | content edges: {sum(len(v) for v in graph.values())}")
    for w in WARN[:20]: print("WARN:", w)
    if ERR:
        for e in ERR[:60]: print("ERR:", e)
        print(f"FAILED: {len(ERR)} errors, {len(WARN)} warnings"); return 1
    print(f"PASSED: 0 errors, {len(WARN)} warnings"); return 0


if __name__ == "__main__":
    sys.exit(main())
