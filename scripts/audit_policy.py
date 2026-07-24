#!/usr/bin/env python3
"""Misst dist/ gegen Googles Publisher-/Spam-Policies (Doorway, Scaled Content, Thin Content).

Grundlage:
  - developers.google.com/search/docs/essentials/spam-policies
    "Doorway abuse: ... creating substantially similar pages that are closer to search
     results than a clearly defined, browseable hierarchy"
    "Scaled content abuse: many pages generated primarily to manipulate rankings"
  - support.google.com/adsense/answer/10015918
    "enough unique content", "substantial value and originality", "no duplicate content
     within or across pages", "no pages with little to no content"

Kein Urteil, nur Zahlen: Wortzahl, EINZIGARTIGE Wortzahl (nach Abzug des seitenweiten
Boilerplates) und paarweise Jaccard-Ähnlichkeit innerhalb jeder Seitengruppe.
Aufruf: python3 scripts/audit_policy.py [--group landing]
"""
from __future__ import annotations

import argparse
import collections
import html
import itertools
import pathlib
import re
import statistics
import sys

DIST = pathlib.Path(__file__).resolve().parent.parent / "dist"


def visible_text(p: pathlib.Path) -> str:
    """Sichtbarer Fließtext: ohne script/style, ohne nav/header/footer (= Boilerplate-Chrome)."""
    t = p.read_text(encoding="utf-8", errors="ignore")
    t = re.sub(r"(?s)<(script|style|nav|header|footer)\b.*?</\1>", " ", t)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def shingles(text: str, n: int = 5) -> set:
    """n-Gramm-Shingles — robuster als Wortmengen: erkennt umgestellte Textbausteine."""
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


GROUPS = {
    "landing": lambda u: bool(re.fullmatch(r"/twitch-[a-z0-9-]+", u)) and u not in ("/twitch-downloader-faq",),
    "streamer": lambda u: u.startswith("/streamer/"),
    "compare": lambda u: u.startswith("/compare/"),
    "alternatives": lambda u: u.startswith("/alternatives/"),
    "blog": lambda u: u.startswith("/blog/"),
}


def url_of(f: pathlib.Path) -> str:
    rel = f.relative_to(DIST).as_posix()
    return "/" if rel == "index.html" else "/" + rel[:-5]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="")
    ap.add_argument("--pairs", type=int, default=8, help="wie viele Top-Paare zeigen")
    args = ap.parse_args()

    pages = {}
    for f in sorted(DIST.rglob("*.html")):
        if f.name == "404.html":
            continue
        pages[url_of(f)] = visible_text(f)

    # Seitenweites Boilerplate: 5-Gramme, die auf >60% ALLER Seiten vorkommen.
    df = collections.Counter()
    sh = {u: shingles(t) for u, t in pages.items()}
    for s in sh.values():
        df.update(s)
    n_pages = len(pages)
    boiler = {g for g, c in df.items() if c > 0.6 * n_pages}
    print(f"Seiten gesamt: {n_pages}  ·  seitenweite Boilerplate-Shingles: {len(boiler)}\n")

    for name, match in GROUPS.items():
        if args.group and args.group != name:
            continue
        urls = [u for u in pages if match(u)]
        if len(urls) < 2:
            continue
        words = {u: len(re.findall(r"[a-z0-9]+", pages[u].lower())) for u in urls}
        uniq = {u: sh[u] - boiler for u in urls}
        uniq_w = {u: len(uniq[u]) for u in urls}
        pairs = [(jaccard(uniq[a], uniq[b]), a, b) for a, b in itertools.combinations(urls, 2)]
        pairs.sort(reverse=True)
        js = [p[0] for p in pairs]
        print(f"=== {name}  ({len(urls)} Seiten) ===")
        print(f"  Wörter        : min {min(words.values()):>5}  median {int(statistics.median(words.values())):>5}  max {max(words.values()):>5}")
        print(f"  einzigartige  : min {min(uniq_w.values()):>5}  median {int(statistics.median(uniq_w.values())):>5}  max {max(uniq_w.values()):>5}   (5-Gramme ohne Boilerplate)")
        print(f"  Jaccard(uniq) : median {statistics.median(js):.3f}   max {max(js):.3f}")
        thin = sorted((u for u in urls if uniq_w[u] < 150), key=lambda u: uniq_w[u])
        if thin:
            print(f"  DÜNN (<150 einzigartige Shingles): {len(thin)}")
            for u in thin[:6]:
                print(f"      {uniq_w[u]:>4}  {u}")
        print(f"  ähnlichste Paare:")
        for j, a, b in pairs[:args.pairs]:
            flag = "  <-- DOORWAY-RISIKO" if j >= 0.30 else ""
            print(f"      {j:.3f}  {a}  ~  {b}{flag}")
        print()

    # Anzeigen-Dichte: Policy verlangt mehr Publisher-Content als Werbung.
    print("=== Anzeigen-Dichte ===")
    dens = []
    for u, t in pages.items():
        f = DIST / (("index" if u == "/" else u.lstrip("/")) + ".html")
        raw = f.read_text(encoding="utf-8", errors="ignore")
        n_ads = raw.count('class="adsbygoogle"')
        w = len(re.findall(r"[a-z0-9]+", t.lower()))
        dens.append((n_ads, w, u))
    worst = sorted((d for d in dens if d[0]), key=lambda d: d[1] / d[0])[:5]
    print(f"  Seiten mit manuellen Ad-Slots: {sum(1 for d in dens if d[0])} von {n_pages}")
    for n_ads, w, u in worst:
        print(f"      {n_ads} Slot(s), {w} Wörter  ->  {u}")
    if not any(d[0] for d in dens):
        print("      keine manuellen Slots im Build (nur Auto-Ads)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
