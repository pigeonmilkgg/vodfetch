#!/usr/bin/env python3
"""Helix-Snapshot-Collector — der History-Flywheel (TRACKER_DOMINATION_PLAN T0.4).

Sammelt einmal pro Lauf einen kompakten Tages-Snapshot über die OFFIZIELLE Twitch
Helix-API (App-Access-Token, client_credentials) und legt ihn versioniert unter
data/ ab. Bewusst von Deploys entkoppelt — noch konsumiert KEINE Seite diese Daten;
sie sind die Option auf ehrliche "seit 2026"-Trend-Seiten (Batch T6).

Ehrlichkeits-Notizen (siehe data/README.md):
- Nur offizielle, dokumentierte Endpunkte. Kein Scraping, kein unoffizielles GQL.
- "Viewer-Summen pro Spiel" sind eine dokumentierte NÄHERUNG (Summe über die
  Top-~1000-Streams, nicht das gesamte Verzeichnis).
- Follower-Totale sind exakt (Get Channel Followers, total).

Env: TWITCH_HELIX_CLIENT_ID / TWITCH_HELIX_CLIENT_SECRET (lokal via .env,
in GitHub Actions als Repo-Secrets). Fehlen sie, wird der Lauf sauber übersprungen
(Exit 0 + Hinweis), damit der Cron vor der Einrichtung nicht rot läuft.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPDIR = DATA / "snapshots"

HELIX = "https://api.twitch.tv/helix"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
LANGS = ["de", "fr", "es"]
TOP_GAMES_N = 500
TOP_STREAMS_N = 1000
KEEP_STREAMS = 300          # voll gespeicherte Top-Streams
KEEP_LANG_STREAMS = 50      # pro Sprache


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def _http(url: str, data: bytes | None = None, headers: dict | None = None,
          retries: int = 4) -> dict:
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:  # 429/5xx → Backoff
            last = e
            if e.code == 429 or e.code >= 500:
                time.sleep(min(2 ** attempt * 2, 20))
                continue
            raise
        except Exception as e:  # Netz-Flakes
            last = e
            time.sleep(min(2 ** attempt * 2, 20))
    raise RuntimeError(f"HTTP endgültig fehlgeschlagen: {url} ({last})")


def get_token(cid: str, secret: str) -> str:
    body = urllib.parse.urlencode({
        "client_id": cid, "client_secret": secret,
        "grant_type": "client_credentials",
    }).encode()
    return _http(TOKEN_URL, data=body)["access_token"]


def helix(path: str, params: dict, cid: str, token: str) -> dict:
    qs = urllib.parse.urlencode(params, doseq=True)
    return _http(f"{HELIX}/{path}?{qs}",
                 headers={"Client-Id": cid, "Authorization": f"Bearer {token}"})


def paginate(path: str, params: dict, cid: str, token: str, want: int) -> list[dict]:
    out: list[dict] = []
    cursor = None
    while len(out) < want:
        p = dict(params, first=100)
        if cursor:
            p["after"] = cursor
        resp = helix(path, p, cid, token)
        data = resp.get("data", [])
        if not data:
            break
        out.extend(data)
        cursor = (resp.get("pagination") or {}).get("cursor")
        if not cursor:
            break
        time.sleep(0.15)  # weit unter 800 Punkte/min bleiben
    return out[:want]


def main() -> int:
    _load_dotenv()
    cid = os.environ.get("TWITCH_HELIX_CLIENT_ID", "").strip()
    secret = os.environ.get("TWITCH_HELIX_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        msg = ("SKIP: TWITCH_HELIX_CLIENT_ID/SECRET nicht gesetzt — Twitch-Dev-App "
               "anlegen (siehe .env.example) und als GitHub-Actions-Secrets hinterlegen.")
        print(msg)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            pathlib.Path(summary).write_text(msg + "\n")
        return 0

    now = dt.datetime.now(dt.timezone.utc)
    token = get_token(cid, secret)
    print(f"Token ok. Sammle Snapshot {now:%Y-%m-%d %H:%M} UTC …")

    # 1) Top-Spiele (Helix-Ranking = nach Zuschauern, Zahlen liefert der Endpunkt nicht)
    games = paginate("games/top", {}, cid, token, TOP_GAMES_N)
    top_games = [{"id": g["id"], "name": g["name"], "rank": i + 1}
                 for i, g in enumerate(games)]
    print(f"  games/top: {len(top_games)}")

    # 2) Top-Streams gesamt (liefert viewer_count) → Vollliste + Aggregate
    streams = paginate("streams", {}, cid, token, TOP_STREAMS_N)
    print(f"  streams: {len(streams)}")
    by_game: dict[str, dict] = {}
    by_lang: dict[str, dict] = {}
    total_viewers = 0
    for s in streams:
        v = int(s.get("viewer_count") or 0)
        total_viewers += v
        g = by_game.setdefault(s.get("game_id") or "0",
                               {"name": s.get("game_name") or "?", "viewers": 0, "channels": 0})
        g["viewers"] += v
        g["channels"] += 1
        l = by_lang.setdefault(s.get("language") or "?", {"viewers": 0, "channels": 0})
        l["viewers"] += v
        l["channels"] += 1
    game_viewers = sorted(
        ({"game_id": k, "name": v["name"], "viewers_approx": v["viewers"],
          "channels_in_top": v["channels"]} for k, v in by_game.items()),
        key=lambda x: -x["viewers_approx"])[:200]
    top_streams = [{
        "login": s.get("user_login"), "name": s.get("user_name"),
        "game": s.get("game_name"), "game_id": s.get("game_id"),
        "viewers": s.get("viewer_count"), "lang": s.get("language"),
        "started_at": s.get("started_at"),
    } for s in streams[:KEEP_STREAMS]]

    # 3) Top-Streams je Sprache (DE/FR/ES)
    lang_streams: dict[str, list] = {}
    for lang in LANGS:
        ls = paginate("streams", {"language": lang}, cid, token, 100)
        lang_streams[lang] = [{
            "login": s.get("user_login"), "name": s.get("user_name"),
            "game": s.get("game_name"), "viewers": s.get("viewer_count"),
        } for s in ls[:KEEP_LANG_STREAMS]]
        print(f"  streams[{lang}]: {len(ls)}")

    # 4) Roster: Profile + exakte Follower-Totale
    roster_file = DATA / "roster.json"
    roster = json.loads(roster_file.read_text())["channels"] if roster_file.exists() else []
    logins = [c["login"].lower() for c in roster]
    users: dict[str, dict] = {}
    for i in range(0, len(logins), 100):
        chunk = logins[i:i + 100]
        resp = helix("users", {"login": chunk}, cid, token)
        for u in resp.get("data", []):
            users[u["login"].lower()] = u
        time.sleep(0.15)
    missing = sorted(set(logins) - set(users))
    if missing:
        print(f"  WARNUNG: {len(missing)} Roster-Logins nicht gefunden: {', '.join(missing[:20])}")
    followers: dict[str, dict] = {}
    for lg, u in users.items():
        try:
            resp = helix("channels/followers", {"broadcaster_id": u["id"], "first": 1}, cid, token)
            followers[lg] = {
                "id": u["id"], "name": u["display_name"],
                "followers": int(resp.get("total") or 0),
                "created_at": u.get("created_at"),
                "broadcaster_type": u.get("broadcaster_type") or "",
            }
        except Exception as e:
            print(f"  WARNUNG: followers({lg}) fehlgeschlagen: {e}")
        time.sleep(0.12)
    print(f"  roster: {len(followers)}/{len(logins)} Follower-Totale")

    snapshot = {
        "schema": 1,
        "date": f"{now:%Y-%m-%d}",
        "collected_at": now.isoformat(timespec="seconds"),
        "source": "Twitch Helix API (official; app access token)",
        "method_notes": [
            "top_games: Helix games/top ranking (no viewer numbers from this endpoint)",
            f"game_viewers: APPROXIMATION — viewer sums over the top {TOP_STREAMS_N} streams only",
            "roster followers: exact totals via channels/followers",
        ],
        "totals": {
            "viewers_in_top_streams": total_viewers,
            "streams_sampled": len(streams),
            "by_language": {k: v for k, v in sorted(by_lang.items(), key=lambda kv: -kv[1]["viewers"])[:30]},
        },
        "top_games": top_games,
        "game_viewers": game_viewers,
        "top_streams": top_streams,
        "lang_top_streams": lang_streams,
        "roster_followers": dict(sorted(followers.items(), key=lambda kv: -kv[1]["followers"])),
        "roster_missing": missing,
    }

    SNAPDIR.mkdir(parents=True, exist_ok=True)
    out = SNAPDIR / f"{now:%Y-%m-%d}.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")
    (DATA / "latest.json").write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")

    # 5) Follower-Zeitreihe deterministisch aus allen Snapshots regenerieren (CSV)
    series: dict[str, dict[str, int]] = {}
    for f in sorted(SNAPDIR.glob("*.json")):
        try:
            snap = json.loads(f.read_text())
        except Exception:
            continue
        for lg, info in (snap.get("roster_followers") or {}).items():
            series.setdefault(lg, {})[snap["date"]] = info["followers"]
    dates = sorted({d for m in series.values() for d in m})
    lines = ["login," + ",".join(dates)]
    for lg in sorted(series):
        lines.append(lg + "," + ",".join(str(series[lg].get(d, "")) for d in dates))
    (DATA / "series").mkdir(exist_ok=True)
    (DATA / "series" / "roster-followers.csv").write_text("\n".join(lines) + "\n")

    print(f"OK: {out.relative_to(ROOT)} geschrieben "
          f"({out.stat().st_size / 1024:.0f} KB), Serie über {len(dates)} Tage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
