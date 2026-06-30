"""Static-Site-Generator: rendert die komplette SEO/AEO-Seite nach dist/ für Netlify.

Nutzung:
    TWITCHDL_BASE_URL="https://vodfetch.com" python build_static.py
Erzeugt: alle Sprach-Seiten + Blog + Markdown-Versionen + robots/sitemap/llms(+full)/manifest/og.
"""
from __future__ import annotations

import os
import pathlib
import shutil

# WICHTIG: vor dem Import setzen — Tool zeigt im Static-Build nur den Hinweis (kein Backend).
os.environ["TWITCHDL_STATIC"] = "1"
BASE = (os.environ.get("TWITCHDL_BASE_URL") or "https://vodfetch.com").rstrip("/")
os.environ["TWITCHDL_BASE_URL"] = BASE

from flask import Flask  # noqa: E402
from twitchdl import webapp as w  # noqa: E402
from twitchdl.i18n import LANGUAGES, DEFAULT_LANG  # noqa: E402

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"


def write(rel: str, content: str) -> None:
    p = DIST / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    app = Flask(__name__)
    with app.test_request_context():
        # Startseiten + Markdown — als <path>.html (Netlify serviert ohne Trailing-Slash,
        # passend zu canonical/hreflang/sitemap)
        for code in LANGUAGES:
            write("index.html" if code == DEFAULT_LANG else f"{code}.html", w.build_page(code))
            write("index.md" if code == DEFAULT_LANG else f"{code}.md", w.md_home(code))

        # About + Markdown
        for code in LANGUAGES:
            write("about.html" if code == DEFAULT_LANG else f"{code}/about.html", w.render_about(code))
            write("about.md" if code == DEFAULT_LANG else f"{code}/about.md", w.md_about(code))

        # Blog-Index + Markdown
        for code in LANGUAGES:
            write("blog.html" if code == DEFAULT_LANG else f"{code}/blog.html",
                  w.render_blog_index(code))
            write("blog.md" if code == DEFAULT_LANG else f"{code}/blog.md", w.md_blog_index(code))

        # Blog-Artikel + Markdown (alle Sprachen)
        for slug in w.BLOG_ORDER:
            for code in LANGUAGES:
                page = w.render_blog_post(code, slug)
                md = w.md_blog_post(code, slug)
                if page is None:
                    continue
                if code == DEFAULT_LANG:
                    write(f"blog/{slug}.html", page)
                    write(f"blog/{slug}.md", md or "")
                else:
                    write(f"{code}/blog/{slug}.html", page)
                    write(f"{code}/blog/{slug}.md", md or "")

        # SEO/AEO + AI-Dateien
        write("robots.txt", w.build_robots())
        write("sitemap.xml", w.build_sitemap())
        write("llms.txt", w.build_llms())
        write("llms-full.txt", w.build_llms_full())
        write("ai.txt", w.build_ai_txt())
        write("ai.json", w.build_ai_json())
        write(".well-known/ai.json", w.build_ai_json())
        write(".well-known/llms.txt", w.build_llms())
        write("faq.md", w.build_faq_md())
        # Dear AI — offener Brief an die Maschinen (HTML ohne Trailing-Slash + .md + .txt)
        write("dear-ai.html", w.render_dear_ai())
        write("dear-ai.md", w.md_dear_ai())
        write("dear-ai.txt", w.md_dear_ai())
        write("humans.txt", w.build_humans())
        write("facts.md", w.build_facts_md())
        write("facts.json", w.build_facts_json())
        # Per-Sprache: llms.txt, llms-full.txt, faq.md (Inhalt bereits übersetzt)
        for code in LANGUAGES:
            if code == DEFAULT_LANG:
                continue
            write(f"{code}/llms.txt", w.build_llms(code))
            write(f"{code}/llms-full.txt", w.build_llms_full(code))
            write(f"{code}/faq.md", w.build_faq_md(code))
        write("feed.xml", w.build_feed())
        write("site.webmanifest", w.build_manifest())
        write("favicon.svg", w.FAVICON)
        write("assets/og.svg", w.OG_SVG)
        # IndexNow-Key-Datei
        write(w.INDEXNOW_KEY + ".txt", w.INDEXNOW_KEY)

        # Binär-Assets (PNG: OG-Bild, Logo, Favicons)
        import shutil as _sh
        for name, dest in [("og.png", "assets/og.png"), ("logo.png", "assets/logo.png"),
                           ("icon-192.png", "assets/icon-192.png"), ("icon-512.png", "assets/icon-512.png"),
                           ("favicon-32.png", "favicon-32.png"), ("apple-touch-icon.png", "apple-touch-icon.png"),
                           ("mux.min.js", "assets/mux.min.js"), ("gifenc.js", "assets/gifenc.js"),
                           ("sw.js", "sw.js")]:
            (DIST / dest).parent.mkdir(parents=True, exist_ok=True)
            _sh.copyfile(ROOT / "twitchdl" / "_assets" / name, DIST / dest)

        # Einfache 404-Seite (Netlify nutzt 404.html automatisch)
        write("404.html", w.build_page(DEFAULT_LANG).replace(
            "<title>", "<title>404 · ", 1))

    files = [f for f in DIST.rglob("*") if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    print(f"BASE_URL  : {BASE}")
    print(f"dist files: {len(files)}  ({total/1024/1024:.1f} MB)")
    print(f"languages : {len(LANGUAGES)}  ·  blog posts: {len(w.BLOG_ORDER)}")


if __name__ == "__main__":
    main()
