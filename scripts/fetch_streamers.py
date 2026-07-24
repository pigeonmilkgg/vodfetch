#!/usr/bin/env python3
"""Frischt twitchdl/_streamers.py mit gemessenen Daten aus Twitchs öffentlicher GraphQL-API auf.

Holt pro Streamer: Follower, Erstelldatum, Partner/Affiliate, Kanalbeschreibung, Team,
zuletzt bekannte Kategorie — und die meistgesehenen Clips. Clips laufen (anders als VODs)
nie ab, sind also gefahrlos in statisches HTML backbar.

Es wird NICHTS erfunden: fehlende Felder bleiben leer, und 'checked' hält fest, wann
gemessen wurde. Aufruf:  ./.venv/bin/python scripts/fetch_streamers.py [--limit N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from twitchdl._streamers import STREAMER_PAGES  # noqa: E402

GQL = "https://gql.twitch.tv/gql"
CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # Twitchs öffentliche Web-Client-ID
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
# 50 statt 12: die Seite zeigt weiterhin nur die Top-12, aber die berechnete Analyse
# (Kategorie-Verteilung, Jahre, Längen) wird über 50 Clips deutlich belastbarer.
CLIP_COUNT = 50

QUERY = """
query($l:String!,$n:Int!){ user(login:$l){
  id login displayName description createdAt
  profileImageURL(width:150)
  followers{ totalCount }
  roles{ isPartner isAffiliate }
  primaryTeam{ name displayName }
  broadcastSettings{ game{ name } }
  clips(first:$n, criteria:{period:ALL_TIME, sort:VIEWS_DESC}){ edges{ node{
    slug title viewCount createdAt durationSeconds game{ name } } } }
} }
"""


def gql(login: str) -> dict | None:
    body = json.dumps({"query": QUERY, "variables": {"l": login, "n": CLIP_COUNT}}).encode()
    req = urllib.request.Request(GQL, data=body, headers={
        "Client-ID": CLIENT_ID, "Content-Type": "application/json", "User-Agent": UA})
    for attempt in range(3):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=25).read())
            if r.get("errors"):
                print(f"  ! {login}: {r['errors'][0].get('message')}")
                return None
            return (r.get("data") or {}).get("user")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == 2:
                print(f"  ! {login}: {e}")
                return None
            time.sleep(2 * (attempt + 1))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="nur die ersten N (zum Testen)")
    ap.add_argument("--lang", default="en", help="nur Streamer dieser Seitensprache")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    logins = [k for k, v in STREAMER_PAGES.items() if v.get("lang") == args.lang]
    if args.limit:
        logins = logins[:args.limit]
    today = dt.date.today().isoformat()
    ok = fail = 0

    for i, login in enumerate(logins, 1):
        u = gql(login)
        if not u:
            fail += 1
            continue
        d = STREAMER_PAGES[login]
        d["name"] = u.get("displayName") or d["name"]
        d["followers"] = ((u.get("followers") or {}).get("totalCount")) or d.get("followers", 0)
        if u.get("createdAt"):
            d["created"] = u["createdAt"][:10]
        roles = u.get("roles") or {}
        d["partner"] = bool(roles.get("isPartner"))
        d["affiliate"] = bool(roles.get("isAffiliate"))
        # Kanalbeschreibung: der Streamer über sich selbst — als Zitat mit Quelle nutzbar
        d["desc"] = (u.get("description") or "").strip()
        team = u.get("primaryTeam") or {}
        d["team"] = (team.get("displayName") or team.get("name") or "").strip()
        d["team_slug"] = (team.get("name") or "").strip()
        bs = u.get("broadcastSettings") or {}
        d["last_game"] = ((bs.get("game") or {}).get("name") or "").strip()
        if u.get("profileImageURL"):
            d["avatar"] = u["profileImageURL"]
        clips = []
        for e in ((u.get("clips") or {}).get("edges") or []):
            n = e.get("node") or {}
            if not n.get("slug"):
                continue
            clips.append({
                "slug": n["slug"],
                "title": (n.get("title") or "").strip(),
                "views": n.get("viewCount") or 0,
                "date": (n.get("createdAt") or "")[:10],
                "secs": n.get("durationSeconds") or 0,
                "game": ((n.get("game") or {}).get("name") or "").strip(),
            })
        d["clips"] = clips
        d["checked"] = today
        ok += 1
        print(f"  {i:>3}/{len(logins)} {login:<20} {d['followers']:>11,}  clips={len(clips):>2}  "
              f"desc={len(d['desc']):>3}  team={d['team'] or '-'}")
        time.sleep(0.3)  # höflich zur API

    print(f"\nok={ok} fail={fail}")
    if args.dry_run:
        print("(dry-run — nichts geschrieben)")
        return 0
    if not ok:
        print("Keine Daten — Datei bleibt unverändert.")
        return 1

    # Generiertes Modul immer komplett neu serialisieren (repr), nie per Textersetzung.
    out = ROOT / "twitchdl" / "_streamers.py"
    header = (
        "# Auto-generated streamer entity pages (T5 pilot). Language-matched: one URL, one language per streamer.\n"
        "# Data measured live from Twitch's public GraphQL API — see 'checked'. Refresh: scripts/fetch_streamers.py\n"
        "# Clips are permanent on Twitch (VODs are not), which is why only clips are baked into the static pages.\n"
    )
    out.write_text(header + "STREAMER_PAGES = " + repr(STREAMER_PAGES) + "\n", encoding="utf-8")
    print(f"geschrieben: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
