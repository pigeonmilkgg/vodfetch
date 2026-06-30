"""Meldet alle URLs via IndexNow an Bing/Yandex (→ schnelle Indexierung, ChatGPT/Copilot-Sichtbarkeit).

Voraussetzung: die Key-Datei /{key}.txt muss live erreichbar sein (im dist enthalten).
Nutzung:  TWITCHDL_BASE_URL="https://deine-domain" python submit_indexnow.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

os.environ.setdefault("TWITCHDL_STATIC", "1")
BASE = (os.environ.get("TWITCHDL_BASE_URL") or "https://cozy-crumble-bff916.netlify.app").rstrip("/")
os.environ["TWITCHDL_BASE_URL"] = BASE
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitchdl import webapp as w  # noqa: E402
from twitchdl.i18n import LANGUAGES, DEFAULT_LANG  # noqa: E402


def _urls_from_sitemap() -> list:
    """Liest die LIVE-Sitemap und gibt exakt deren <loc>-URLs zurück (= ganze Sitemap)."""
    import re
    try:
        r = urllib.request.urlopen(BASE + "/sitemap.xml", timeout=25)
        xml = r.read().decode("utf-8", "ignore")
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
        # nur URLs des eigenen Hosts (Sicherheit), Reihenfolge erhalten, dedupe
        seen, out = set(), []
        for u in locs:
            if u.startswith(BASE) and u not in seen:
                seen.add(u); out.append(u)
        return out
    except Exception as e:
        print("  (Sitemap nicht lesbar, nutze generierte Liste):", e)
        return []


def _urls_generated() -> list:
    urls = [BASE + "/"]
    for c in LANGUAGES:
        if c != DEFAULT_LANG:
            urls.append(BASE + w.lang_path(c))
        urls.append(BASE + w.about_path(c))
        urls.append(BASE + w.blog_index_path(c))
    for s in w.BLOG_ORDER:
        for c in LANGUAGES:
            if w.blog_post_data(s, c):  # nur real existierende Posts
                urls.append(BASE + w.blog_post_path(c, s))
    return urls


def main() -> None:
    urls = _urls_from_sitemap() or _urls_generated()

    host = BASE.split("//", 1)[1]
    payload = {
        "host": host,
        "key": w.INDEXNOW_KEY,
        "keyLocation": f"{BASE}/{w.INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=25)
        print(f"IndexNow OK: HTTP {r.status} — {len(urls)} URLs an host '{host}' gemeldet.")
    except urllib.error.HTTPError as e:
        # 200/202 = ok; manche Endpoints geben 200 ohne Body
        print(f"IndexNow HTTP {e.code}: {e.read()[:200].decode(errors='ignore')} ({len(urls)} URLs)")
    except Exception as e:
        print("IndexNow Fehler:", e)


if __name__ == "__main__":
    main()
