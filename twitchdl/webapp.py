"""SEO/AEO-optimierte, mehrsprachige Web-Oberfläche für den Twitch Downloader.

- Server-gerendertes HTML pro Sprache (crawlbar auch ohne JavaScript)
- Vollständiges <head>: Title/Description/Keywords, canonical, hreflang (+x-default),
  Open Graph, Twitter Cards, robots, JSON-LD (WebSite, SoftwareApplication, FAQPage,
  HowTo, BreadcrumbList)
- /robots.txt, /sitemap.xml, /llms.txt (AEO), /site.webmanifest, /favicon.svg, /assets/og.svg
- Funktionaler Downloader über /api/* (Flask + Server-Sent-Events), unverändert robust
"""
from __future__ import annotations

import html as _html
import json
import os
import queue
import threading
import uuid
import webbrowser

from .core import Downloader
from .errors import TwitchDLError
from .i18n import DEFAULT_LANG, LANGUAGES, get_strings, normalize_lang
from .models import ProgressEvent
from .parser import parse_input

_jobs: dict = {}
_lock = threading.Lock()

# Static-Export-Modus (Netlify u.ä.): kein lokales Backend → Tool zeigt Hinweis.
STATIC_MODE = os.environ.get("TWITCHDL_STATIC") == "1"

import datetime as _dt
BRAND = "Twitch Downloader"
BUILD_DATE = os.environ.get("TWITCHDL_BUILD_DATE") or _dt.date.today().isoformat()
# Optionale Entitäts-Verknüpfungen (GitHub/Social) für E-E-A-T — per Env setzbar.
SAMEAS = [u.strip() for u in os.environ.get("TWITCHDL_SAMEAS", "").split(",") if u.strip()]
# IndexNow-Key (Datei muss unter /{key}.txt erreichbar sein). Per Env überschreibbar.
INDEXNOW_KEY = os.environ.get("TWITCHDL_INDEXNOW_KEY", "8f3a2b7c9d1e4f5a6b8c0d2e3f4a5b6c")
# Optionale Webmaster-Verifizierung per Meta-Tag (Google URL-prefix / Bing). DNS-Verify braucht das nicht.
GSC_VERIFY = os.environ.get("TWITCHDL_GSC_VERIFY", "")
BING_VERIFY = os.environ.get("TWITCHDL_BING_VERIFY", "")

_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_assets")


def _asset_bytes(name: str) -> bytes:
    with open(os.path.join(_ASSET_DIR, name), "rb") as f:
        return f.read()


# --------------------------------------------------------------------------- #
# Helfer
# --------------------------------------------------------------------------- #
def esc(s) -> str:
    return _html.escape(str(s if s is not None else ""), quote=True)


def base_url() -> str:
    env = os.environ.get("TWITCHDL_BASE_URL")
    if env:
        return env.rstrip("/")
    try:
        from flask import request
        return request.url_root.rstrip("/")
    except Exception:
        return "http://127.0.0.1:8800"


def lang_path(lang: str) -> str:
    return "/" if lang == DEFAULT_LANG else f"/{lang}"


def lang_url(lang: str) -> str:
    return base_url() + lang_path(lang)


def blog_index_path(lang: str) -> str:
    return "/blog" if lang == DEFAULT_LANG else f"/{lang}/blog"


def blog_post_path(lang: str, slug: str) -> str:
    return f"/blog/{slug}" if lang == DEFAULT_LANG else f"/{lang}/blog/{slug}"


# Blog-Inhalte (auto-generiert via Workflow). Fehlt die Datei → leerer Blog.
try:
    from ._blog import BLOG_POSTS, BLOG_ORDER
except ImportError:
    BLOG_POSTS: dict = {}
    BLOG_ORDER: list = []


def blog_post_data(slug: str, lang: str) -> "dict | None":
    p = BLOG_POSTS.get(slug)
    if not p:
        return None
    i = p.get("i18n", {})
    return i.get(lang) or i.get(DEFAULT_LANG)


# --------------------------------------------------------------------------- #
# JSON-LD (strukturierte Daten für SEO + AEO)
# --------------------------------------------------------------------------- #
def _jsonld_tags(blocks: list) -> str:
    out = []
    for b in blocks:
        payload = json.dumps(b, ensure_ascii=False).replace("<", "\\u003c")
        out.append(f'<script type="application/ld+json">{payload}</script>')
    return "\n".join(out)


def _org() -> dict:
    bu = base_url()
    o = {
        "@type": "Organization",
        "name": BRAND,
        "url": bu + "/",
        "logo": {"@type": "ImageObject", "url": bu + "/assets/logo.png", "width": 512, "height": 512},
        "description": "Free, open-source tool to download Twitch VODs, clips and live streams as MP4.",
    }
    if SAMEAS:
        o["sameAs"] = SAMEAS
    return o


def _publisher() -> dict:
    return _org()


def build_jsonld(t: dict, lang: str, canonical: str) -> str:
    hreflang = LANGUAGES[lang]["hreflang"]
    bu = base_url()
    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": t["brand"],
        "url": bu + "/",
        "inLanguage": hreflang,
        "description": t["meta_description"],
        "publisher": _org(),
    }
    software = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": t["brand"],
        "url": canonical,
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "Windows, macOS, Linux, Web",
        "inLanguage": hreflang,
        "description": t["meta_description"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [f["title"] for f in t["features"]],
        "publisher": _org(),
    }
    webpage = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": t["meta_title"],
        "url": canonical,
        "inLanguage": hreflang,
        "description": t["meta_description"],
        "dateModified": BUILD_DATE,
        "isPartOf": {"@type": "WebSite", "name": t["brand"], "url": bu + "/"},
        "primaryImageOfPage": {"@type": "ImageObject", "url": bu + "/assets/og.png"},
        "speakable": {"@type": "SpeakableSpecification",
                      "cssSelector": ["h1", ".lead", ".faq summary h3", ".faq-a p"]},
        "publisher": _org(),
    }
    faqpage = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": hreflang,
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["q"],
                "acceptedAnswer": {"@type": "Answer", "text": f["a"]},
            }
            for f in t["faqs"]
        ],
    }
    howto = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": t["how_h2"],
        "inLanguage": hreflang,
        "step": [
            {"@type": "HowToStep", "position": i + 1, "name": s["title"], "text": s["desc"]}
            for i, s in enumerate(t["how_steps"])
        ],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": t["brand"], "item": canonical},
        ],
    }
    return _jsonld_tags([website, software, webpage, faqpage, howto, breadcrumb])


# --------------------------------------------------------------------------- #
# <head> (generisch + Home-Wrapper)
# --------------------------------------------------------------------------- #
def _head(lang: str, *, title: str, description: str, keywords: str, canonical: str,
          alt_pairs: list, jsonld: str, og_type: str = "website", md_href: str = "") -> str:
    bu = base_url()
    og_img = esc(bu + "/assets/og.png")
    alt = "\n".join(
        f'<link rel="alternate" hreflang="{esc(h)}" href="{esc(u)}">' for h, u in alt_pairs
    )
    md_link = f'\n<link rel="alternate" type="text/markdown" href="{esc(md_href)}">' if md_href else ""
    verify = ""
    if GSC_VERIFY:
        verify += f'\n<meta name="google-site-verification" content="{esc(GSC_VERIFY)}">'
    if BING_VERIFY:
        verify += f'\n<meta name="msvalidate.01" content="{esc(BING_VERIFY)}">'
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="keywords" content="{esc(keywords)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<meta name="theme-color" content="#9147ff">{verify}
<link rel="canonical" href="{esc(canonical)}">
{alt}
<meta property="og:type" content="{esc(og_type)}">
<meta property="og:site_name" content="Twitch Downloader">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:locale" content="{esc(get_strings(lang)['locale'])}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:type" content="image/png">
<meta property="og:image:alt" content="Twitch Downloader — download Twitch VODs, clips and live streams to MP4">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{og_img}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="Twitch Downloader Blog" href="/feed.xml">
<link rel="alternate" type="text/plain" title="LLM guide (llms.txt)" href="{esc(_aifile_path(lang, 'llms.txt'))}">
<link rel="alternate" type="text/plain" title="AI guide (ai.txt)" href="/ai.txt">{md_link}
{jsonld}
<style>{CSS}</style>"""


def _home_alt_pairs() -> list:
    bu = base_url()
    pairs = [("x-default", bu + "/")]
    for code, meta in LANGUAGES.items():
        pairs.append((meta["hreflang"], bu + lang_path(code)))
    return pairs


def build_head(t: dict, lang: str) -> str:
    canonical = lang_url(lang)
    return _head(lang, title=t["meta_title"], description=t["meta_description"],
                 keywords=t["meta_keywords"], canonical=canonical,
                 alt_pairs=_home_alt_pairs(), jsonld=build_jsonld(t, lang, canonical),
                 og_type="website", md_href=md_href_for(lang_path(lang)))


# --------------------------------------------------------------------------- #
# <body>
# --------------------------------------------------------------------------- #
def _lang_select(t: dict, lang: str) -> str:
    opts = []
    for code, meta in LANGUAGES.items():
        sel = " selected" if code == lang else ""
        opts.append(f'<option value="{esc(lang_path(code))}"{sel}>{esc(meta["name"])}</option>')
    return (
        f'<label class="langsel"><span class="sr-only">{esc(t["nav_lang"])}</span>'
        f'<select onchange="location.href=this.value" aria-label="{esc(t["nav_lang"])}">'
        f'{"".join(opts)}</select></label>'
    )


def _topbar(t: dict, lang: str, blog: bool = False) -> str:
    home = lang_path(lang)
    # Auf Blog-Seiten zeigen Sektions-Anker zurück zur Startseite
    a = (lambda x: home + x) if blog else (lambda x: x)
    return f"""<header class="topbar">
  <a class="brand" href="{esc(home)}"><span class="dot"></span>Twitch Downloader<small>{esc(t["tagline"])}</small></a>
  <nav class="mainnav">
    <a href="{esc(a('#features'))}">{esc(t["nav_features"])}</a>
    <a href="{esc(a('#how'))}">{esc(t["nav_how"])}</a>
    <a href="{esc(blog_index_path(lang))}">{esc(t["nav_blog"])}</a>
    <a href="{esc(about_path(lang))}">{esc(t["nav_about"])}</a>
    <a href="{esc(a('#faq'))}">{esc(t["nav_faq"])}</a>
    {_lang_select(t, lang)}
  </nav>
</header>"""


def _footer(t: dict, lang: str) -> str:
    foot_langs = " · ".join(
        f'<a href="{esc(lang_path(code))}" hreflang="{esc(meta["hreflang"])}">{esc(meta["name"])}</a>'
        for code, meta in LANGUAGES.items()
    )
    ai_links = (
        '<a href="/llms.txt">llms.txt</a> · <a href="/llms-full.txt">llms-full.txt</a> · '
        '<a href="/ai.txt">ai.txt</a> · <a href="/ai.json">ai.json</a> · <a href="/faq.md">faq.md</a>'
    )
    return (
        '<footer class="sitefoot">\n'
        f'  <p>{esc(t["footer_made"])}</p>\n'
        f'  <p class="footlinks">{foot_langs}</p>\n'
        f'  <p class="footlinks ai">For AI &amp; LLMs: {ai_links}</p>\n'
        "</footer>"
    )


def build_body(t: dict, lang: str) -> str:
    types_cards = "".join(
        f'<article class="card"><h3>{esc(c["title"])}</h3><p>{esc(c["desc"])}</p></article>'
        for c in t["types"]
    )
    feature_cards = "".join(
        f'<article class="feature"><div class="ficon" aria-hidden="true">{_FEATURE_ICONS[i % len(_FEATURE_ICONS)]}</div>'
        f'<h3>{esc(f["title"])}</h3><p>{esc(f["desc"])}</p></article>'
        for i, f in enumerate(t["features"])
    )
    how_steps = "".join(
        f'<li class="step"><div class="num">{i + 1}</div><div><h3>{esc(s["title"])}</h3>'
        f'<p>{esc(s["desc"])}</p></div></li>'
        for i, s in enumerate(t["how_steps"])
    )
    faqs = "".join(
        f'<details class="faq"><summary><h3>{esc(f["q"])}</h3><span class="chev" aria-hidden="true">＋</span></summary>'
        f'<div class="faq-a"><p>{esc(f["a"])}</p></div></details>'
        for f in t["faqs"]
    )
    guide_cards = "".join(
        f'<article class="card"><h3><a href="{esc(blog_post_path(lang, s))}">{esc(gd["title"])}</a></h3>'
        f'<p>{esc(gd["excerpt"])}</p></article>'
        for s in BLOG_ORDER for gd in [blog_post_data(s, lang)] if gd
    )
    guides_section = (
        f'\n  <section id="guides" class="block">\n    <h2>{esc(t["blog_h1"])}</h2>\n'
        f'    <div class="cards">{guide_cards}</div>\n'
        f'    <p style="margin-top:16px"><a class="readlink" href="{esc(blog_index_path(lang))}">{esc(t["blog_read"])}</a></p>\n'
        "  </section>\n"
    ) if guide_cards else ""

    return f"""{_topbar(t, lang)}

<main>
  <section class="hero">
    <p class="badge">{esc(t["hero_badge"])}</p>
    <h1>{esc(t["hero_h1"])}<span>{esc(t["hero_h1_sub"])}</span></h1>
    <p class="lead">{esc(t["hero_sub"])}</p>

    <div class="tool" id="tool">
      <label for="url">{esc(t["tool_url_label"])}</label>
      <input id="url" type="text" inputmode="url" autocomplete="off" spellcheck="false"
             placeholder="{esc(t["tool_url_ph"])}">
      <button class="primary" id="analyzeBtn" onclick="analyze()">{esc(t["tool_analyze"])}</button>

      <div class="result hidden" id="resultCard">
        <div class="meta" id="meta"></div>
        <div class="qrow">
          <label class="sr-only" for="quality">{esc(t["tool_quality"])}</label>
          <select id="quality" onchange="onQuality()"></select>
          <span class="est" id="sizeEst"></span>
        </div>
        <button class="primary big" id="downloadBtn" onclick="startDownload()">{esc(t["tool_download"])}</button>
        <button class="optlink" type="button" id="optBtn" onclick="toggleAdv()">{esc(t["tool_options"])}</button>
        <div class="adv hidden" id="adv">
          <div class="row">
            <div class="field" id="fmtField"><label>{esc(t["tool_format"])}</label>
              <div class="seg" id="fmtSeg">
                <button type="button" data-v="mp4" class="on" onclick="setFmt('mp4')">MP4</button>
                <button type="button" data-v="ts" onclick="setFmt('ts')">TS</button>
              </div></div>
            <div class="field"><label for="filename">{esc(t["tool_filename"])}</label>
              <input id="filename" placeholder="{esc(t["tool_filename_ph"])}"></div>
          </div>
          <div class="trim hidden" id="trimBox">
            <label class="trimtoggle"><input type="checkbox" id="trimOn" onchange="onTrimToggle()"> {esc(t["tool_trim"])}</label>
            <div class="trimbody hidden" id="trimBody">
              <p class="trimhint">{esc(t["tool_trim_hint"])}</p>
              <div class="trow">
                <label>{esc(t["tool_from"])}</label><input id="tStart" class="time" value="0:00" oninput="onTrimEdit()">
                <label>{esc(t["tool_to"])}</label><input id="tEnd" class="time" value="0:00" oninput="onTrimEdit()">
                <span class="seldur" id="selDur"></span>
              </div>
            </div>
          </div>
          <button class="ghost hidden" id="chatBtn" onclick="downloadChat()">{esc(t["tool_chat"])}</button>
        </div>
        <button class="ghost hidden" id="stopBtn" onclick="stopJob()">{esc(t["tool_stop"])}</button>
      </div>

      <div class="progress hidden" id="progressCard">
        <div class="bar"><i id="barFill"></i></div>
        <div class="stats"><span id="statLeft"></span><span id="statRight"></span></div>
        <div class="log" id="log"></div>
      </div>

      <div class="recent hidden" id="recentBox">
        <h3>{esc(t["tool_recent"])}</h3>
        <ul id="recentList"></ul>
      </div>
    </div>
    <p class="trust">{esc(t["trust"])}</p>
  </section>

  <section class="prose">
    <h2>{esc(t["what_h2"])}</h2>
    <p>{esc(t["what_p"])}</p>
  </section>

  <section id="types" class="block">
    <h2>{esc(t["types_h2"])}</h2>
    <div class="cards">{types_cards}</div>
  </section>

  <section id="features" class="block">
    <h2>{esc(t["features_h2"])}</h2>
    <div class="features">{feature_cards}</div>
  </section>

  <section id="how" class="block">
    <h2>{esc(t["how_h2"])}</h2>
    <ol class="steps">{how_steps}</ol>
  </section>

  <section id="faq" class="block">
    <h2>{esc(t["faq_h2"])}</h2>
    <div class="faqs">{faqs}</div>
  </section>
{guides_section}
  <p class="disclaimer">{esc(t["disclaimer"])}</p>
</main>

{_footer(t, lang)}"""


def _document(lang: str, head_inner: str, body_inner: str, tool_js: bool = False) -> str:
    meta = LANGUAGES[lang]
    parts = []
    if tool_js:
        t = get_strings(lang)
        js_cfg = json.dumps({
            "analyzing": t["tool_analyzing"],
            "analyze": t["tool_analyze"],
            "autoQuality": t["tool_auto_quality"],
            "staticNotice": t.get("static_notice", ""),
        }, ensure_ascii=False).replace("<", "\\u003c")
        flag = "window.TWITCHDL_HOSTED=false;" if STATIC_MODE else ""
        parts.append('<script src="/assets/mux.min.js" defer></script>')
        parts.append(f"<script>{flag}window.I18N={js_cfg};</script>")
        parts.append(f"<script>{JS}</script>")
    parts.append("<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(function(){})}</script>")
    scripts = "\n".join(parts) + "\n"
    return (
        f'<!DOCTYPE html>\n<html lang="{esc(meta["hreflang"])}" dir="{esc(meta["dir"])}">\n'
        f"<head>\n{head_inner}\n</head>\n<body>\n{body_inner}\n{scripts}</body>\n</html>"
    )


def build_page(lang: str) -> str:
    t = get_strings(lang)
    return _document(lang, build_head(t, lang), build_body(t, lang), tool_js=True)


# --------------------------------------------------------------------------- #
# Blog (Index + Artikel) — SEO/AEO-optimiert
# --------------------------------------------------------------------------- #
def _blog_index_alt_pairs() -> list:
    bu = base_url()
    pairs = [("x-default", bu + "/blog")]
    for code, meta in LANGUAGES.items():
        pairs.append((meta["hreflang"], bu + blog_index_path(code)))
    return pairs


def _blog_post_alt_pairs(slug: str) -> list:
    bu = base_url()
    pairs = [("x-default", bu + "/blog/" + slug)]
    for code, meta in LANGUAGES.items():
        pairs.append((meta["hreflang"], bu + blog_post_path(code, slug)))
    return pairs


def render_blog_index(lang: str) -> str:
    t = get_strings(lang)
    bu = base_url()
    canonical = bu + blog_index_path(lang)
    hreflang = LANGUAGES[lang]["hreflang"]

    cards = []
    items = []
    pos = 0
    for slug in BLOG_ORDER:
        d = blog_post_data(slug, lang)
        if not d:
            continue
        pos += 1
        href = blog_post_path(lang, slug)
        cards.append(
            f'<article class="card"><h3><a href="{esc(href)}">{esc(d["title"])}</a></h3>'
            f'<p>{esc(d["excerpt"])}</p>'
            f'<a class="readlink" href="{esc(href)}">{esc(t["blog_read"])}</a></article>'
        )
        items.append({"@type": "ListItem", "position": pos,
                      "url": bu + href, "name": d["title"]})

    blog_ld = {"@context": "https://schema.org", "@type": "Blog", "name": t["blog_h1"],
               "url": canonical, "inLanguage": hreflang, "description": t["blog_sub"],
               "publisher": _publisher()}
    itemlist_ld = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": items}
    crumbs_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Twitch Downloader", "item": bu + lang_path(lang)},
        {"@type": "ListItem", "position": 2, "name": t["nav_blog"], "item": canonical},
    ]}

    head = _head(lang, title=f'{t["blog_h1"]} | Twitch Downloader',
                 description=t["blog_sub"], keywords=t["meta_keywords"], canonical=canonical,
                 alt_pairs=_blog_index_alt_pairs(),
                 jsonld=_jsonld_tags([blog_ld, itemlist_ld, crumbs_ld]), og_type="website",
                 md_href=md_href_for(blog_index_path(lang)))
    body = f"""{_topbar(t, lang, blog=True)}
<main>
  <section class="hero bloghero">
    <h1>{esc(t["blog_h1"])}</h1>
    <p class="lead">{esc(t["blog_sub"])}</p>
  </section>
  <section class="block">
    <div class="cards">{"".join(cards) or "<p class='lead'>—</p>"}</div>
  </section>
</main>
{_footer(t, lang)}"""
    return _document(lang, head, body, tool_js=False)


def render_blog_post(lang: str, slug: str) -> "str | None":
    d = blog_post_data(slug, lang)
    if not d:
        return None
    t = get_strings(lang)
    bu = base_url()
    post = BLOG_POSTS.get(slug, {})
    date = post.get("date", "")
    canonical = bu + blog_post_path(lang, slug)
    hreflang = LANGUAGES[lang]["hreflang"]

    # Artikel-Sektionen
    sec_html = []
    for s in d.get("sections", []):
        paras = "".join(f"<p>{esc(p)}</p>" for p in s.get("paragraphs", []))
        sec_html.append(f'<h2>{esc(s["heading"])}</h2>{paras}')
    # Schritte
    steps_html = "".join(
        f'<li class="step"><div class="num">{i + 1}</div><div><h3>{esc(s["title"])}</h3>'
        f'<p>{esc(s["desc"])}</p></div></li>'
        for i, s in enumerate(d.get("how_steps", []))
    )
    # FAQ
    faq_html = "".join(
        f'<details class="faq"><summary><h3>{esc(f["q"])}</h3><span class="chev" aria-hidden="true">＋</span></summary>'
        f'<div class="faq-a"><p>{esc(f["a"])}</p></div></details>'
        for f in d.get("faqs", [])
    )
    # Verwandte Guides (andere Posts)
    related = []
    for other in BLOG_ORDER:
        if other == slug:
            continue
        od = blog_post_data(other, lang)
        if not od:
            continue
        href = blog_post_path(lang, other)
        related.append(f'<article class="card"><h3><a href="{esc(href)}">{esc(od["title"])}</a></h3>'
                       f'<p>{esc(od["excerpt"])}</p></article>')

    # JSON-LD
    article_ld = {"@context": "https://schema.org", "@type": "BlogPosting",
                  "headline": d["title"], "description": d["excerpt"], "inLanguage": hreflang,
                  "mainEntityOfPage": canonical, "image": bu + "/assets/og.png",
                  "isPartOf": {"@type": "WebSite", "name": BRAND, "url": bu + "/"},
                  "speakable": {"@type": "SpeakableSpecification",
                                "cssSelector": ["h1", ".answer", ".faq summary h3", ".faq-a p"]},
                  "author": _org(), "publisher": _org()}
    if date:
        article_ld["datePublished"] = date
        article_ld["dateModified"] = date
    blocks = [article_ld]
    if d.get("how_steps"):
        blocks.append({"@context": "https://schema.org", "@type": "HowTo", "name": d["title"],
                       "inLanguage": hreflang,
                       "step": [{"@type": "HowToStep", "position": i + 1, "name": s["title"], "text": s["desc"]}
                                for i, s in enumerate(d["how_steps"])]})
    if d.get("faqs"):
        blocks.append({"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": hreflang,
                       "mainEntity": [{"@type": "Question", "name": f["q"],
                                       "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                                      for f in d["faqs"]]})
    blocks.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Twitch Downloader", "item": bu + lang_path(lang)},
        {"@type": "ListItem", "position": 2, "name": t["nav_blog"], "item": bu + blog_index_path(lang)},
        {"@type": "ListItem", "position": 3, "name": d["title"], "item": canonical},
    ]})

    head = _head(lang, title=d["meta_title"], description=d["meta_description"],
                 keywords=t["meta_keywords"], canonical=canonical,
                 alt_pairs=_blog_post_alt_pairs(slug), jsonld=_jsonld_tags(blocks), og_type="article",
                 md_href=md_href_for(blog_post_path(lang, slug)))

    updated = f'<p class="updated">{esc(t["blog_updated"])}: {esc(date)}</p>' if date else ""
    related_html = (f'<section class="block"><h2>{esc(t["blog_related"])}</h2>'
                    f'<div class="cards">{"".join(related)}</div></section>') if related else ""
    steps_block = (f'<h2>{esc(t["how_h2"])}</h2><ol class="steps">{steps_html}</ol>') if steps_html else ""
    faq_block = (f'<h2>{esc(t["faq_h2"])}</h2><div class="faqs">{faq_html}</div>') if faq_html else ""

    body = f"""{_topbar(t, lang, blog=True)}
<main>
  <article class="article">
    <nav class="crumbs"><a href="{esc(blog_index_path(lang))}">{esc(t["nav_blog"])}</a> › <span>{esc(d["title"])}</span></nav>
    <h1>{esc(d["title"])}</h1>
    {updated}
    <p class="answer">{esc(d["excerpt"])}</p>
    {"".join(sec_html)}
    {steps_block}
    {faq_block}
    <div class="cta">
      <h2>{esc(t["blog_cta_h"])}</h2>
      <p>{esc(t["blog_cta_p"])}</p>
      <a class="ctabtn" href="{esc(lang_path(lang))}#tool">{esc(t["blog_cta_btn"])}</a>
    </div>
    {related_html}
    <p><a href="{esc(lang_path(lang))}">{esc(t["blog_back"])}</a></p>
  </article>
</main>
{_footer(t, lang)}"""
    return _document(lang, head, body, tool_js=False)


# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
CSS = r"""
:root{--bg:#0e0e10;--panel:#18181b;--panel2:#1f1f23;--border:#2a2a2e;--purple:#9147ff;
--purple2:#772ce8;--text:#efeff1;--muted:#adadb8;--green:#00b85f;--red:#ff5c5c}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
background:var(--bg);color:var(--text);line-height:1.6;-webkit-font-smoothing:antialiased}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
a{color:var(--purple);text-decoration:none}a:hover{text-decoration:underline}
h1,h2,h3{line-height:1.2}
.hidden{display:none}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 22px;
border-bottom:1px solid var(--border);position:sticky;top:0;background:rgba(14,14,16,.85);
backdrop-filter:blur(8px);z-index:10;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:9px;font-weight:800;font-size:18px;color:var(--text)}
.brand:hover{text-decoration:none}
.brand small{font-weight:500;color:var(--muted);font-size:12px}
.brand .dot{width:11px;height:11px;border-radius:50%;background:var(--purple)}
.mainnav{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.mainnav a{color:var(--muted);font-size:14px;font-weight:600}
.mainnav a:hover{color:var(--text);text-decoration:none}
.langsel select{background:var(--panel2);color:var(--text);border:1px solid var(--border);
border-radius:8px;padding:7px 10px;font-size:13px;cursor:pointer}
main{max-width:880px;margin:0 auto;padding:0 18px}
.hero{text-align:center;padding:48px 0 16px}
.badge{display:inline-block;background:rgba(145,71,255,.14);color:#c8a6ff;border:1px solid rgba(145,71,255,.35);
padding:6px 14px;border-radius:999px;font-size:13px;font-weight:600;margin:0 0 18px}
.hero h1{font-size:44px;font-weight:900;margin:0 0 6px;letter-spacing:-.02em}
.hero h1 span{display:block;font-size:21px;font-weight:700;color:var(--muted);margin-top:10px;letter-spacing:0}
.lead{font-size:17px;color:var(--muted);max-width:620px;margin:14px auto 0}
.tool{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:22px;margin:28px 0 12px;
text-align:left;box-shadow:0 18px 50px rgba(0,0,0,.35)}
.tool label{display:block;font-size:12px;color:var(--muted);margin:0 0 6px;text-transform:uppercase;letter-spacing:.5px;font-weight:700}
.tool input,.tool select{width:100%;background:var(--panel2);border:1px solid var(--border);border-radius:9px;
color:var(--text);padding:12px;font-size:14px;outline:none}
.tool input:focus,.tool select:focus{border-color:var(--purple)}
button{border:none;border-radius:9px;padding:13px 18px;font-size:15px;font-weight:700;cursor:pointer;width:100%;transition:.15s}
button.primary{background:var(--purple);color:#fff;margin-top:12px}
button.primary:hover{background:var(--purple2)}
button.ghost{background:var(--panel2);border:1px solid var(--border);color:var(--text);margin-top:10px}
button:disabled{opacity:.5;cursor:not-allowed}
.row{display:flex;gap:12px;margin-top:14px;flex-wrap:wrap}.row .field{flex:1;min-width:140px}
.result,.progress{margin-top:6px}
.meta{font-size:14px;color:var(--muted);margin:4px 0 14px;line-height:1.6}
.meta b{color:var(--text)}.meta .tag{display:inline-block;background:var(--purple);color:#fff;font-size:11px;
padding:2px 8px;border-radius:6px;margin-left:6px;vertical-align:middle}
.bar{height:14px;background:var(--panel2);border-radius:8px;overflow:hidden;border:1px solid var(--border)}
.bar>i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--purple),var(--purple2));transition:width .25s}
.stats{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-top:8px}
.log{background:#000;border-radius:8px;padding:11px;font-family:ui-monospace,Menlo,monospace;font-size:12px;
color:#9fe;max-height:150px;overflow:auto;margin-top:11px;white-space:pre-wrap;line-height:1.5}
.log .ok{color:var(--green)}.log .err{color:var(--red)}
.pulse{animation:pulse 1.4s infinite}@keyframes pulse{50%{opacity:.45}}
.trust{font-size:13px;color:var(--muted);margin:8px 0 0}
section.prose,section.block{padding:34px 0;border-top:1px solid var(--border)}
section h2{font-size:27px;font-weight:800;margin:0 0 18px;letter-spacing:-.01em}
section.prose p{color:var(--muted);font-size:16px;max-width:680px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:13px;padding:20px}
.card h3{font-size:17px;margin:0 0 8px}.card p{color:var(--muted);font-size:14px;margin:0}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.feature{background:var(--panel);border:1px solid var(--border);border-radius:13px;padding:20px}
.feature .ficon{width:38px;height:38px;color:var(--purple);margin-bottom:12px}
.feature .ficon svg{width:100%;height:100%}
.feature h3{font-size:16px;margin:0 0 7px}.feature p{color:var(--muted);font-size:14px;margin:0}
.steps{list-style:none;counter-reset:s;padding:0;margin:0;display:grid;gap:14px}
.step{display:flex;gap:16px;align-items:flex-start;background:var(--panel);border:1px solid var(--border);
border-radius:13px;padding:18px}
.step .num{flex:none;width:34px;height:34px;border-radius:50%;background:var(--purple);color:#fff;
display:flex;align-items:center;justify-content:center;font-weight:800}
.step h3{font-size:16px;margin:0 0 4px}.step p{color:var(--muted);font-size:14px;margin:0}
.faqs{display:grid;gap:10px}
.faq{background:var(--panel);border:1px solid var(--border);border-radius:11px;overflow:hidden}
.faq summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;
gap:12px;padding:16px 18px}
.faq summary::-webkit-details-marker{display:none}
.faq summary h3{font-size:16px;margin:0;font-weight:700}
.faq .chev{color:var(--purple);font-size:20px;font-weight:700;flex:none;transition:transform .2s}
.faq[open] .chev{transform:rotate(45deg)}
.faq-a{padding:0 18px 16px}.faq-a p{color:var(--muted);font-size:14px;margin:0}
.disclaimer{font-size:12px;color:var(--muted);text-align:center;max-width:680px;margin:30px auto;
padding:14px 16px;border:1px dashed var(--border);border-radius:10px}
.sitefoot{border-top:1px solid var(--border);padding:26px 18px;text-align:center;color:var(--muted);font-size:13px}
.footlinks{margin-top:10px;line-height:2}.footlinks a{color:var(--muted)}
[dir=rtl] .step{flex-direction:row}
.bloghero{padding:40px 0 8px}
.card h3 a{color:var(--text)}.card h3 a:hover{color:var(--purple);text-decoration:none}
.readlink{display:inline-block;margin-top:12px;color:var(--purple);font-weight:700;font-size:14px}
.article{max-width:760px;margin:0 auto;padding:26px 0 8px}
.crumbs{font-size:13px;color:var(--muted);margin-bottom:14px}
.crumbs a{color:var(--muted)}
.article>h1{font-size:33px;font-weight:900;margin:0 0 8px;letter-spacing:-.01em}
.updated{font-size:13px;color:var(--muted);margin:0 0 22px}
.article h2{font-size:22px;margin:30px 0 12px}
.article>p,.article h2+p{color:#d7d7db;font-size:16px;margin:0 0 14px}
.answer{background:rgba(145,71,255,.10);border-left:3px solid var(--purple);border-radius:8px;
padding:14px 16px;font-size:17px;color:var(--text);margin:0 0 22px;font-weight:500}
.article .steps{margin:8px 0 6px}
.cta{background:linear-gradient(135deg,rgba(145,71,255,.20),rgba(119,44,232,.06));
border:1px solid rgba(145,71,255,.4);border-radius:14px;padding:26px;margin:34px 0;text-align:center}
.cta h2{margin:0 0 8px}.cta p{color:var(--muted);margin:0 0 16px}
.ctabtn{display:inline-block;background:var(--purple);color:#fff;padding:13px 24px;border-radius:9px;font-weight:800}
.ctabtn:hover{background:var(--purple2);text-decoration:none}
.est{font-size:12px;color:var(--muted);margin-left:8px}
.seg{display:inline-flex;border:1px solid var(--border);border-radius:8px;overflow:hidden}
.seg button{width:auto;background:var(--panel2);color:var(--muted);border:none;padding:9px 15px;font-size:13px;font-weight:700;border-radius:0;margin:0;cursor:pointer}
.seg button.on{background:var(--purple);color:#fff}
.trim{margin-top:14px;border:1px solid var(--border);border-radius:10px;padding:12px 14px;background:var(--panel2)}
.trimtoggle{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text);text-transform:none;letter-spacing:0;font-weight:600;cursor:pointer;margin:0}
.trimtoggle input{width:auto;margin:0}
.trimbody{margin-top:12px}
.trimhint{font-size:12px;color:var(--muted);margin:0 0 10px}
.trow{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.trow label{margin:0;font-size:11px}
.time{width:96px !important;text-align:center;font-variant-numeric:tabular-nums}
.seldur{font-size:13px;color:var(--purple);font-weight:700;margin-left:auto}
.btnrow{display:flex;gap:10px}.btnrow button{flex:1}
.recent{margin-top:16px;border-top:1px solid var(--border);padding-top:14px}
.recent h3{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin:0 0 8px}
.recent ul{list-style:none;margin:0;padding:0;font-size:13px}
.recent li{padding:4px 0;color:var(--muted);display:flex;justify-content:space-between;gap:10px}
.recent li b{color:var(--text);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#url{padding:14px;font-size:15px}
.tool input{transition:border-color .15s,box-shadow .15s}
.tool input:focus{box-shadow:0 0 0 3px rgba(145,71,255,.25)}
.qrow{display:flex;align-items:center;gap:12px;margin:6px 0 14px}
.qrow select{flex:1}
button{transition:transform .12s,background .15s,opacity .15s}
.primary.big{font-size:17px;padding:16px 18px;box-shadow:0 8px 24px rgba(145,71,255,.35)}
.primary.big:hover{transform:translateY(-1px)}
.optlink{width:auto;background:none;border:none;color:var(--muted);font-size:13px;font-weight:600;padding:9px 4px;margin:9px auto 0;display:block;cursor:pointer}
.optlink:hover{color:var(--text)}
.optlink::after{content:' ▾'}
.optlink.open::after{content:' ▴'}
.adv{margin-top:8px;border-top:1px solid var(--border);padding-top:14px;animation:fade .2s ease}
.result{animation:fadeup .28s cubic-bezier(.2,.7,.2,1)}
.progress.ok .bar>i{background:linear-gradient(90deg,var(--green),#0bd17a)!important}
.progress.ok .bar{box-shadow:0 0 0 1px rgba(0,184,95,.45)}
@keyframes fadeup{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@media(max-width:600px){.hero h1{font-size:34px}.hero h1 span{font-size:18px}.mainnav{gap:12px}.article>h1{font-size:27px}}
"""


# Dekorative Feature-Icons (inline SVG, aria-hidden)
_FEATURE_ICONS = [
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l2.5 5.5L20 9l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.5z"/></svg>',
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/></svg>',
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h7l-1 8 10-12h-7z"/></svg>',
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6z"/></svg>',
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></svg>',
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 16V4m0 12l-4-4m4 4l4-4"/><path d="M4 20h16"/></svg>',
]


# --------------------------------------------------------------------------- #
# JS (Downloader-Logik; Labels über window.I18N)
# --------------------------------------------------------------------------- #
JS = r"""
let curKind=null,curJob=null,es=null;
const API=(window.TWITCHDL_API||'');
function backend(){return window.TWITCHDL_HOSTED!==false}
function $(id){return document.getElementById(id)}
function notice(){$('resultCard').classList.add('hidden');$('progressCard').classList.remove('hidden');$('log').innerHTML='';log(I18N.staticNotice||'Run the Twitch Downloader locally to download.','err')}
function log(m,c){const l=$('log');const s=document.createElement('div');if(c)s.className=c;s.textContent=m;l.appendChild(s);l.scrollTop=l.scrollHeight}
function fb(n){if(!n)return'0 B';const u=['B','KB','MB','GB','TB'];let i=0;while(n>=1024&&i<u.length-1){n/=1024;i++}return n.toFixed(1)+' '+u[i]}
function ft(s){if(s==null)return'–';s=Math.round(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;return(h?h+':':'')+String(m).padStart(2,'0')+':'+String(x).padStart(2,'0')}
async function analyze(){
  const url=$('url').value.trim();if(!url){$('url').focus();return}
  if(!backend()){return clientAnalyze();}
  const b=$('analyzeBtn');b.disabled=true;b.textContent=I18N.analyzing;$('resultCard').classList.add('hidden');
  try{
    const r=await fetch(API+'/api/info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const d=await r.json();if(!r.ok)throw new Error(d.error||'Error');
    curKind=d.kind;
    let h='<b>'+(d.title||'—')+'</b>';if(d.author)h+=' · '+d.author;h+='<span class="tag">'+d.kind+'</span>';
    if(d.duration)h+='<br>'+ft(d.duration);$('meta').innerHTML=h;
    const sel=$('quality');sel.innerHTML='';
    const auto=document.createElement('option');auto.value='best';auto.textContent=I18N.autoQuality;sel.appendChild(auto);
    d.qualities.forEach(q=>{const o=document.createElement('option');o.value=q.name;o.textContent=(q.is_source?'★ ':'')+q.label;sel.appendChild(o)});
    sel.value='best';$('resultCard').classList.remove('hidden');
  }catch(e){alert(e.message)}finally{b.disabled=false;b.textContent=I18N.analyze}
}
async function startDownload(){
  if(!backend()){return clientDownload();}
  const body={url:$('url').value.trim(),quality:$('quality').value,output:($('output')?$('output').value.trim():'')||'.',filename:$('filename').value.trim()};
  $('downloadBtn').disabled=true;$('progressCard').classList.remove('hidden');
  $('log').innerHTML='';$('barFill').style.width='0%';$('statLeft').textContent='';$('statRight').textContent='';
  try{
    const r=await fetch(API+'/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d=await r.json();if(!r.ok)throw new Error(d.error||'Error');
    curJob=d.job_id;if(d.kind==='channel')$('stopBtn').classList.remove('hidden');listen(curJob);
  }catch(e){log('✗ '+e.message,'err');$('downloadBtn').disabled=false}
}
function listen(id){
  es=new EventSource(API+'/api/progress/'+id);
  es.onmessage=ev=>{const d=JSON.parse(ev.data);
    if(d.phase==='downloading'){
      if(d.percent!=null){$('barFill').style.width=d.percent.toFixed(1)+'%';
        const c=(d.unit==='bytes')?fb(d.bytes_done):(d.current+'/'+d.total+' · '+fb(d.bytes_done));
        $('statLeft').textContent=c;$('statRight').textContent=fb(d.speed_bps)+'/s · ETA '+ft(d.eta_seconds)}
      else{$('barFill').style.width='100%';$('barFill').parentElement.classList.add('pulse');
        $('statLeft').textContent='● LIVE · '+d.current;$('statRight').textContent=fb(d.bytes_done)+' · '+fb(d.speed_bps)+'/s'}
      if(d.message)log(d.message);
    }else if(d.phase==='done'){$('barFill').style.width='100%';$('barFill').parentElement.classList.remove('pulse');
      log('✓ '+(d.message||'OK'),'ok');if(d.output_path)log('📁 '+d.output_path,'ok');flashOk();finish();
    }else if(d.phase==='error'){log('✗ '+d.message,'err');finish();
    }else if(d.message){log('→ '+d.message)}
  };
  es.addEventListener('end',()=>finish());
  es.onerror=function(){if(es&&es.readyState===2){log('✗ Connection lost','err');finish()}};
}
function finish(){if(es){es.close();es=null}$('downloadBtn').disabled=false;$('stopBtn').classList.add('hidden');$('barFill').parentElement.classList.remove('pulse');curJob=null}
async function stopJob(){if(!backend()){clientStop=true;$('stopBtn').disabled=true;log('⏹ Stopping…');setTimeout(()=>{$('stopBtn').disabled=false},1500);return}if(!curJob)return;$('stopBtn').disabled=true;try{await fetch(API+'/api/stop/'+curJob,{method:'POST'})}catch(e){}finally{setTimeout(()=>{$('stopBtn').disabled=false},2000)}}

/* ===================== Client-side downloader (static web app) ===================== */
/* Runs in the browser via the same-origin /api/tw proxy (Netlify Function) + mux.js (TS->MP4). */
const TW_CID='kimne78kx3ncx6brgo4mv6wki5h1ko';
let clientRef=null,clientQ=[],clientStop=false,clientMedia={},curFmt='mp4',trim={on:false,start:0,end:0},totalDur=0;
function P(u){return '/api/tw?url='+encodeURIComponent(u)}
function G(id){return document.getElementById(id)}
function eh(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms)})}
function safeName(s){return (String(s||'twitch').replace(/[\\/:*?"<>|]+/g,'_').replace(/\s+/g,' ').trim().slice(0,120))||'twitch'}
function saveBlob(blob,name){var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},2000)}
function parseTime(s){s=String(s||'').trim();if(/^\d+(\.\d+)?$/.test(s))return parseFloat(s);var p=s.split(':').map(Number);if(p.some(isNaN))return 0;var t=0;for(var i=0;i<p.length;i++)t=t*60+p[i];return t}
async function gqlReq(body){var r=await fetch(P('https://gql.twitch.tv/gql'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw new Error('GraphQL HTTP '+r.status);return r.json()}
function parseInput(raw){raw=(raw||'').trim();if(!raw)throw new Error('Enter a Twitch URL');
  if(!/[\/.]/.test(raw)){if(/^v?\d{6,}$/.test(raw))return{kind:'vod',id:raw.replace(/^v/,'')};
    if(/^[A-Za-z0-9_-]{6,}$/.test(raw)&&raw.indexOf('-')>=0)return{kind:'clip',id:raw};
    if(/^[A-Za-z0-9_]{2,25}$/.test(raw))return{kind:'channel',id:raw.toLowerCase()};return{kind:'clip',id:raw};}
  var url;try{url=new URL(raw.indexOf('://')>=0?raw:'https://'+raw)}catch(e){throw new Error('Invalid URL')}
  var host=url.hostname.toLowerCase();var parts=url.pathname.split('/').filter(Boolean);
  if(host.indexOf('clips.')===0&&parts[0])return{kind:'clip',id:parts[0]};
  if(parts[0]==='videos'&&parts[1])return{kind:'vod',id:parts[1].replace(/^v/,'')};
  if(parts.length>=3&&(parts[1]==='clip'||parts[1]==='clips'))return{kind:'clip',id:parts[2]};
  if(parts[0])return{kind:'channel',id:parts[0].toLowerCase()};throw new Error('Unrecognized Twitch URL');}
function baseOf(u){return u.slice(0,u.lastIndexOf('/')+1)}
function parseMaster(text){var out=[],stream=null,media=null;
  text.split('\n').forEach(function(raw){var ln=raw.trim();if(!ln)return;
    if(ln.indexOf('#EXT-X-MEDIA:')===0)media=ln;
    else if(ln.indexOf('#EXT-X-STREAM-INF:')===0)stream=ln;
    else if(ln[0]!=='#'){var name=null,res=null,bw=0,m;
      if(media){m=/NAME="([^"]+)"/.exec(media);if(m)name=m[1]}
      if(stream){m=/RESOLUTION=([0-9x]+)/.exec(stream);if(m)res=m[1];var b=/BANDWIDTH=(\d+)/.exec(stream);if(b)bw=+b[1]}
      var isSrc=/chunked|source/i.test((name||'')+' '+(media||''));var audio=/audio/i.test((name||'')+(media||''));
      out.push({url:ln,resolution:res,bandwidth:bw,is_source:isSrc,audio:audio,
        label:(name||res||'source')+(res?' · '+res:'')+(bw?' · '+(bw/1e6).toFixed(1)+' Mbit/s':'')});
      stream=null;media=null;}});
  out.sort(function(a,b){return (b.is_source-a.is_source)||(b.bandwidth-a.bandwidth)});return out}
function parseMedia(text,base){var segs=[],ended=false,target=2,dur=0;
  text.split('\n').forEach(function(raw){var ln=raw.trim();
    if(ln.indexOf('#EXT-X-ENDLIST')===0)ended=true;
    else if(ln.indexOf('#EXT-X-TARGETDURATION:')===0){var v=parseFloat(ln.split(':')[1]);if(v)target=v}
    else if(ln.indexOf('#EXTINF:')===0){dur=parseFloat(ln.slice(8).split(',')[0])||0}
    else if(ln&&ln[0]!=='#'){segs.push({url:/^https?:/.test(ln)?ln:base+ln,dur:dur});dur=0}});
  var cum=0;segs.forEach(function(s){s.start=cum;cum+=s.dur});
  return{segs:segs,ended:ended,target:target,total:cum}}
async function clipInfo(slug){
  var q='query($s:ID!){clip(slug:$s){title durationSeconds broadcaster{displayName} videoQualities{quality frameRate sourceURL} playbackAccessToken(params:{platform:"web",playerBackend:"mediaplayer",playerType:"site"}){signature value}}}';
  var d=await gqlReq({query:q,variables:{s:slug}});var c=d&&d.data&&d.data.clip;
  if(!c)throw new Error('Clip not found or deleted');var tok=c.playbackAccessToken||{};var vq=c.videoQualities||[];
  if(!vq.length||!tok.signature)throw new Error('Clip not available');
  var quals=vq.map(function(v){return{url:v.sourceURL+'?sig='+tok.signature+'&token='+encodeURIComponent(tok.value),is_source:false,clip:true,
    label:(v.quality||'?')+'p'+(v.frameRate>0?Math.round(v.frameRate):'')}});
  if(quals[0])quals[0].is_source=true;
  return{title:c.title,author:(c.broadcaster||{}).displayName,duration:c.durationSeconds,qualities:quals}}
async function vodLiveInfo(ref){var token,usher,d;
  if(ref.kind==='vod'){d=await gqlReq({query:'query($id:ID!){videoPlaybackAccessToken(id:$id,params:{platform:"web",playerBackend:"mediaplayer",playerType:"embed"}){value signature}}',variables:{id:ref.id}});
    token=d&&d.data&&d.data.videoPlaybackAccessToken;if(!token)throw new Error('VOD unavailable (deleted, private or sub-only)');
    usher='https://usher.ttvnw.net/vod/'+ref.id+'.m3u8';}
  else{d=await gqlReq({query:'query($l:String!){streamPlaybackAccessToken(channelName:$l,params:{platform:"web",playerBackend:"mediaplayer",playerType:"embed"}){value signature}}',variables:{l:ref.id}});
    token=d&&d.data&&d.data.streamPlaybackAccessToken;if(!token)throw new Error('Channel offline or not found');
    usher='https://usher.ttvnw.net/api/channel/hls/'+ref.id+'.m3u8';}
  var p=new URLSearchParams({sig:token.signature,token:token.value,allow_source:'true',allow_audio_only:'true',player:'twitchweb',playlist_include_framerate:'true',supported_codecs:'av1,h265,h264',p:String(Math.floor(Math.random()*9e6))});
  var r=await fetch(P(usher+'?'+p.toString()));
  if(!r.ok)throw new Error('Usher '+r.status+(r.status===403?' (sub-only/expired)':r.status===404?' (offline/not found)':''));
  var quals=parseMaster(await r.text());if(!quals.length)throw new Error('No qualities available');
  var title=ref.kind==='vod'?'vod_'+ref.id:ref.id+'_live',author='';
  if(ref.kind==='vod'){try{var m=await gqlReq({query:'query($id:ID!){video(id:$id){title lengthSeconds owner{displayName}}}',variables:{id:ref.id}});var v=m&&m.data&&m.data.video;if(v){title=v.title||title;author=(v.owner||{}).displayName||''}}catch(e){}}
  return{title:title,author:author,duration:null,qualities:quals}}
async function loadMedia(idx){
  if(clientMedia[idx])return clientMedia[idx];
  var q=clientQ[idx];var r=await fetch(P(q.url));if(!r.ok)throw new Error('Playlist HTTP '+r.status);
  var m=parseMedia(await r.text(),baseOf(q.url));clientMedia[idx]=m;return m}
async function clientAnalyze(){var b=$('analyzeBtn');b.disabled=true;b.textContent=I18N.analyzing;
  ['resultCard','progressCard'].forEach(function(i){if(G(i))G(i).classList.add('hidden')});
  try{var ref=parseInput($('url').value);clientRef=ref;curKind=ref.kind;clientMedia={};
    var info=ref.kind==='clip'?await clipInfo(ref.id):await vodLiveInfo(ref);clientQ=info.qualities;
    $('meta').innerHTML='<b>'+eh(info.title)+'</b>'+(info.author?' · '+eh(info.author):'')+'<span class="tag">'+ref.kind+'</span>'+(info.duration?'<br>'+ft(info.duration):'');
    var sel=$('quality');sel.innerHTML='';
    info.qualities.forEach(function(q,i){var o=document.createElement('option');o.value=String(i);o.textContent=(q.is_source?'★ ':'')+q.label;sel.appendChild(o)});
    sel.value='0';
    if(G('trimBox'))G('trimBox').classList.add('hidden');if(G('trimOn'))G('trimOn').checked=false;if(G('trimBody'))G('trimBody').classList.add('hidden');trim={on:false,start:0,end:0};
    if(G('chatBtn'))G('chatBtn').classList.toggle('hidden',ref.kind!=='vod');
    if(ref.kind==='vod'){try{var m=await loadMedia(0);totalDur=m.total;
      if(G('trimBox')){G('trimBox').classList.remove('hidden');G('tStart').value=ft(0);G('tEnd').value=ft(totalDur);trim.end=totalDur;
        var tp=getQ('t');if(tp){var ts=parseTwitchT(tp);if(ts>0&&ts<totalDur&&G('trimOn')){if(G('adv'))G('adv').classList.remove('hidden');G('trimOn').checked=true;onTrimToggle();G('tStart').value=ft(ts);G('tEnd').value=ft(Math.min(ts+60,totalDur));onTrimEdit();}}}
    }catch(e){}}
    onQuality();
    $('resultCard').classList.remove('hidden');renderRecent();
  }catch(e){alert((e&&e.message)||String(e))}finally{b.disabled=false;b.textContent=I18N.analyze}}
function curQ(){return clientQ[parseInt(($('quality')||{}).value||'0',10)||0]}
function setFmt(f){curFmt=f;var bs=document.querySelectorAll('#fmtSeg button');for(var i=0;i<bs.length;i++)bs[i].classList.toggle('on',bs[i].getAttribute('data-v')===f);updateEst()}
async function onQuality(){var q=curQ();var audio=q&&(q.audio||/audio/i.test(q.label||''));
  if(G('fmtField'))G('fmtField').style.display=audio?'none':'';
  if(clientRef&&clientRef.kind==='vod'){try{var idx=parseInt(($('quality')||{}).value||'0',10)||0;var m=await loadMedia(idx);totalDur=m.total;if(!trim.on&&G('tEnd')){G('tEnd').value=ft(totalDur);trim.end=totalDur}}catch(e){}}
  updateEst()}
function onTrimToggle(){trim.on=!!(G('trimOn')&&G('trimOn').checked);if(G('trimBody'))G('trimBody').classList.toggle('hidden',!trim.on);updateEst()}
function onTrimEdit(){trim.start=parseTime((G('tStart')||{}).value);trim.end=parseTime((G('tEnd')||{}).value);updateEst()}
function selRange(){if(trim.on&&clientRef&&clientRef.kind==='vod'){var s=Math.max(0,trim.start),e=Math.min(totalDur||trim.end,trim.end);if(e<=s)e=totalDur;return[s,e]}return[0,totalDur]}
function estBytes(){var q=curQ();if(!(clientRef&&clientRef.kind==='vod'&&q&&q.bandwidth))return 0;var r=selRange();return q.bandwidth/8*Math.max(0,r[1]-r[0])}
function updateEst(){if(G('sizeEst')){var e=estBytes();G('sizeEst').textContent=e>0?('≈ '+fb(e)):''}
  if(trim.on&&G('selDur')){var r=selRange();G('selDur').textContent=ft(r[0])+' → '+ft(r[1])+' = '+ft(r[1]-r[0])}}
async function makeSink(filename){
  if(window.showSaveFilePicker){try{var h=await window.showSaveFilePicker({suggestedName:filename});var ws=await h.createWritable();
    return{write:function(b){return ws.write(b)},close:function(){return ws.close()},blob:null}}
    catch(e){if(e&&e.name==='AbortError')throw new Error('Cancelled');log('⚠ Could not stream to disk — buffering in memory','err')}}
  var chunks=[];return{write:async function(b){chunks.push(b instanceof Uint8Array?b:new Uint8Array(b))},close:async function(){},blob:function(type){return new Blob(chunks,{type:type||'application/octet-stream'})}}}
async function fetchBin(u){var CH=4000000,off=0,parts=[];
  for(var g=0;g<4000;g++){var r=null,e416=false;
    for(var a=0;a<4;a++){try{var rr=await fetch(P(u),{headers:{'Range':'bytes='+off+'-'+(off+CH-1)}});
      if(rr.ok){r=rr;break}if(rr.status===416){e416=true;break}}catch(e){}await sleep(300*(a+1))}
    if(e416)break;if(!r)throw new Error('Segment failed');
    var ab=await r.arrayBuffer();if(ab.byteLength)parts.push(new Uint8Array(ab));
    if(r.status===200)break;            /* server ignored Range -> full body */
    off+=ab.byteLength;
    if(ab.byteLength===0||ab.byteLength<CH)break;   /* short read -> last chunk */
  }
  var len=0;parts.forEach(function(p){len+=p.byteLength});var all=new Uint8Array(len),o=0;parts.forEach(function(p){all.set(p,o);o+=p.byteLength});return all}
function makeMux(){var tm=new muxjs.mp4.Transmuxer({remux:true,keepOriginalTimestamps:true});var out=[];
  tm.on('data',function(seg){out.push(seg.initSegment);out.push(seg.data)});
  return{push:function(b){tm.push(b)},finish:function(){tm.flush();return out}}}
async function clientDownload(){if(!clientRef)return;var q=curQ();if(!q)return;
  $('downloadBtn').disabled=true;$('progressCard').classList.remove('hidden','ok');$('log').innerHTML='';$('barFill').style.width='0%';$('statLeft').textContent='';$('statRight').textContent='';$('barFill').parentElement.classList.remove('pulse');clientStop=false;
  var mb=$('meta').querySelector('b');var name=safeName(($('filename').value.trim())||(mb&&mb.textContent)||clientRef.id);
  try{if(clientRef.kind==='clip')await dlClip(q,name);else await dlSegments(clientRef,q,name);}
  catch(e){log('✗ '+((e&&e.message)||String(e)),'err')}
  $('downloadBtn').disabled=false;if(G('stopBtn'))$('stopBtn').classList.add('hidden');$('barFill').parentElement.classList.remove('pulse')}
async function dlClip(q,name){log('Downloading clip…');var ab=await fetchBin(q.url);
  saveBlob(new Blob([ab],{type:'video/mp4'}),name+'.mp4');log('✓ Done: '+name+'.mp4','ok');log('📁 Saved to your Downloads','ok');addRecent(name+'.mp4');flashOk()}
function setBar(p){$('barFill').style.width=p.toFixed(1)+'%'}
async function dlSegments(ref,q,name){
  var idx=parseInt(($('quality')||{}).value||'0',10)||0;
  var media=clientMedia[idx]||await loadMedia(idx);
  var isLive=(ref.kind==='channel')&&!media.ended;
  var audio=q.audio||/audio/i.test(q.label||'');
  var useMux=(!isLive)&&(curFmt==='mp4')&&!!window.muxjs;   /* live always streams as TS */
  var ext=audio?(useMux?'.m4a':'.aac'):(useMux?'.mp4':'.ts');
  var list=null;
  if(!isLive){var segs=media.segs;if(trim.on){var rg=selRange();segs=segs.filter(function(s){return (s.start+s.dur)>rg[0]&&s.start<rg[1]})}list=segs;if(!list.length)throw new Error('No segments in range')}
  /* memory guards */
  var est=estBytes();
  if(useMux&&est>1500e6){if(!confirm('This MP4 is ~'+fb(est)+'. Converting to MP4 buffers it in memory and may fail for very large VODs. Tip: choose Format → TS, or trim a shorter section. Continue?'))throw new Error('Cancelled')}
  else if(!window.showSaveFilePicker&&!isLive&&est>700e6){if(!confirm('This download is ~'+fb(est)+' and your browser will buffer it in memory. For large files use Chrome/Edge (streams to disk) or trim a section. Continue?'))throw new Error('Cancelled')}
  var sink=await makeSink(name+ext);var start=Date.now(),done=0,bytes=0;
  if(useMux){
    var mux;try{mux=makeMux()}catch(e){throw new Error('MP4 converter failed to start — choose Format → TS.')}
    var total=list.length;log('Downloading '+total+' segments → MP4…');
    for(var i=0;i<list.length;i+=6){if(clientStop)break;var batch=list.slice(i,i+6);
      var bufs=await Promise.all(batch.map(function(s){return fetchBin(s.url)}));
      for(var j=0;j<bufs.length;j++){try{mux.push(bufs[j])}catch(e){throw new Error('MP4 conversion failed — choose Format → TS and retry.')}bytes+=bufs[j].byteLength;done++}
      var el=(Date.now()-start)/1000||0.1;setBar(done/total*92);$('statLeft').textContent=done+'/'+total+' · '+fb(bytes);$('statRight').textContent=fb(bytes/el)+'/s · ETA '+ft((total-done)*(el/Math.max(done,1)))}
    if(clientStop){await sink.close();log('⏹ Stopped','err');return}
    log('Converting to MP4…');setBar(97);
    var outparts;try{outparts=mux.finish()}catch(e){throw new Error('MP4 conversion failed — choose Format → TS and retry.')}
    for(var k=0;k<outparts.length;k++)if(outparts[k])await sink.write(outparts[k]);
    setBar(100);await sink.close();if(sink.blob)saveBlob(sink.blob(audio?'audio/mp4':'video/mp4'),name+ext);
    log('✓ Done: '+name+ext,'ok');addRecent(name+ext);flashOk();return}
  /* ---- TS / raw path: streams per segment (low memory; used for live & TS format) ---- */
  var seen={};
  async function pump(items,total){for(var i=0;i<items.length;i+=6){if(clientStop)break;var batch=items.slice(i,i+6);
    var bufs=await Promise.all(batch.map(function(s){return fetchBin(s.url)}));
    for(var j=0;j<bufs.length;j++){await sink.write(bufs[j]);bytes+=bufs[j].byteLength;done++}
    var el=(Date.now()-start)/1000||0.1;
    if(total){setBar(done/total*100);$('statLeft').textContent=done+'/'+total+' · '+fb(bytes);$('statRight').textContent=fb(bytes/el)+'/s · ETA '+ft((total-done)*(el/Math.max(done,1)))}
    else{setBar(100);$('barFill').parentElement.classList.add('pulse');$('statLeft').textContent='● LIVE · '+done+' · '+fb(bytes);$('statRight').textContent=fb(bytes/el)+'/s'}}}
  if(isLive){if(G('stopBtn'))$('stopBtn').classList.remove('hidden');log('Recording live → TS… press Stop to finish');
    var fails=0;media.segs.forEach(function(s){seen[s.url]=1});await pump(media.segs,0);
    while(!clientStop){await sleep((media.target||2)*1000);
      try{var rr=await fetch(P(q.url));if(rr.ok){var mm=parseMedia(await rr.text(),baseOf(q.url));var fresh=mm.segs.filter(function(s){return !seen[s.url]});fresh.forEach(function(s){seen[s.url]=1});if(fresh.length){fails=0;await pump(fresh,0)}else{fails++}if(mm.ended)break}else{fails++}}catch(e){fails++}
      if(fails>=8){log('Stream ended or unreachable.','ok');break}}
  }else{log('Downloading '+list.length+' segments → TS…');await pump(list,list.length)}
  await sink.close();if(sink.blob)saveBlob(sink.blob(audio?'audio/aac':'video/mp2t'),name+ext);
  log('✓ Done: '+name+ext,'ok');if(ext==='.ts'||ext==='.aac')log('ℹ Plays in VLC; for MP4 choose Format → MP4.','ok');addRecent(name+ext);flashOk()}
async function downloadChat(){if(!clientRef||clientRef.kind!=='vod')return;var btn=$('chatBtn');btn.disabled=true;clientStop=false;
  $('progressCard').classList.remove('hidden');log('Downloading chat…');
  try{var cursor=null,lines=[],n=0;
    var Q='query($id:ID!,$cursor:Cursor){video(id:$id){comments(contentOffsetSeconds:0,first:100,after:$cursor){edges{cursor node{contentOffsetSeconds commenter{displayName} message{fragments{text}}}} pageInfo{hasNextPage}}}}';
    for(var g=0;g<3000;g++){if(clientStop)break;
      var d=await gqlReq({query:Q,variables:{id:clientRef.id,cursor:cursor}});
      var c=d&&d.data&&d.data.video&&d.data.video.comments;if(!c)break;var edges=c.edges||[];
      edges.forEach(function(e){var nd=e.node||{};var off=nd.contentOffsetSeconds||0;var who=(nd.commenter||{}).displayName||'?';
        var msg=((nd.message||{}).fragments||[]).map(function(f){return f.text}).join('');lines.push('['+ft(off)+'] '+who+': '+msg);n++});
      $('statLeft').textContent=n+' messages';
      if(!c.pageInfo||!c.pageInfo.hasNextPage||!edges.length)break;cursor=edges[edges.length-1].cursor}
    if(!lines.length)throw new Error('No chat available for this VOD');
    saveBlob(new Blob([lines.join('\n')],{type:'text/plain'}),safeName(clientRef.id)+'_chat.txt');
    log('✓ Chat saved ('+n+' messages)','ok')}
  catch(e){log('✗ '+((e&&e.message)||String(e)),'err')}finally{btn.disabled=false}}
function getQ(k){try{return new URLSearchParams(location.search).get(k)}catch(e){return null}}
function parseTwitchT(t){if(!t)return 0;var s=0;var m=String(t).match(/(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?/);if(m){s=(parseInt(m[1]||0))*3600+(parseInt(m[2]||0))*60+(parseInt(m[3]||0))}if(!s&&/^\d+$/.test(t))s=+t;return s}
function addRecent(name){try{var k='twdl_recent';var a=JSON.parse(localStorage.getItem(k)||'[]');a.unshift({name:name,t:Date.now()});localStorage.setItem(k,JSON.stringify(a.slice(0,8)));renderRecent()}catch(e){}}
function renderRecent(){try{var a=JSON.parse(localStorage.getItem('twdl_recent')||'[]');var box=G('recentBox');if(!box||!a.length)return;box.classList.remove('hidden');G('recentList').innerHTML=a.map(function(x){return '<li><b>'+eh(x.name)+'</b><span>'+new Date(x.t).toLocaleDateString()+'</span></li>'}).join('')}catch(e){}}
function initClient(){if(typeof backend==='function'&&backend())return;try{renderRecent()}catch(e){}var u=getQ('url')||getQ('u');if(u){var inp=$('url');if(inp){inp.value=u;if(getQ('go')||getQ('autostart'))setTimeout(function(){analyze()},150)}}}
initClient();
function toggleAdv(){var a=G('adv');if(a)a.classList.toggle('hidden');var o=G('optBtn');if(o)o.classList.toggle('open')}
function flashOk(){var p=G('progressCard');if(p)p.classList.add('ok')}
$('url').addEventListener('keydown',function(e){if(e.key==='Enter')analyze()});
$('url').addEventListener('paste',function(){setTimeout(function(){if(($('url').value||'').trim().length>5)analyze()},80)});
"""


# --------------------------------------------------------------------------- #
# robots.txt / sitemap.xml / llms.txt / manifest / favicon / og
# --------------------------------------------------------------------------- #
def build_robots() -> str:
    bu = base_url()
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n\n"
        "# AI / answer engines explicitly welcome\n"
        "User-agent: GPTBot\nAllow: /\n"
        "User-agent: OAI-SearchBot\nAllow: /\n"
        "User-agent: ChatGPT-User\nAllow: /\n"
        "User-agent: PerplexityBot\nAllow: /\n"
        "User-agent: ClaudeBot\nAllow: /\n"
        "User-agent: Claude-Web\nAllow: /\n"
        "User-agent: Google-Extended\nAllow: /\n"
        "User-agent: Bingbot\nAllow: /\n\n"
        "# AI resources (start here): /llms.txt /llms-full.txt /ai.txt /ai.json /faq.md\n"
        "# Every page is also available as Markdown by appending .md to its URL.\n"
        f"Sitemap: {bu}/sitemap.xml\n"
    )


def _sitemap_entry(loc: str, alt_pairs: list, priority: str, changefreq: str = "weekly") -> str:
    links = "".join(
        f'    <xhtml:link rel="alternate" hreflang="{esc(h)}" href="{esc(u)}"/>\n' for h, u in alt_pairs
    )
    return (
        "  <url>\n"
        f"    <loc>{esc(loc)}</loc>\n"
        f"    <lastmod>{BUILD_DATE}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        f"{links}"
        "  </url>"
    )


def build_sitemap() -> str:
    bu = base_url()
    entries = []
    # Startseiten (alle Sprachen)
    for code in LANGUAGES:
        entries.append(_sitemap_entry(bu + lang_path(code), _home_alt_pairs(),
                                      "1.0" if code == DEFAULT_LANG else "0.9"))
    # About (alle Sprachen)
    for code in LANGUAGES:
        entries.append(_sitemap_entry(bu + about_path(code), _about_alt_pairs(), "0.5"))
    # Blog-Index (alle Sprachen)
    if BLOG_ORDER:
        for code in LANGUAGES:
            entries.append(_sitemap_entry(bu + blog_index_path(code), _blog_index_alt_pairs(), "0.7"))
        # Blog-Artikel (alle Sprachen)
        for slug in BLOG_ORDER:
            for code in LANGUAGES:
                entries.append(_sitemap_entry(bu + blog_post_path(code, slug),
                                              _blog_post_alt_pairs(slug), "0.6"))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


# --------------------------------------------------------------------------- #
# Gemeinsame AI-Fakten (genutzt von llms.txt, ai.txt, ai.json)
# --------------------------------------------------------------------------- #
def _ai_key_facts() -> dict:
    return {
        "max_quality": "1080p60 source",
        "formats": "MP4 (video) or audio-only",
        "content_types": "Twitch VODs (past broadcasts), highlights, clips, live streams",
        "account_required": False,
        "cost": "free",
        "watermark": False,
        "runs": "in your browser (segments relayed via a stateless proxy that stores nothing)",
        "open_source": True,
        "vod_retention": "7 days default, 14 with Prime/Turbo, up to 60 for Affiliates/Partners",
    }


def _ai_quick_answers() -> list:
    return [
        ("How to download a Twitch VOD",
         "Copy the VOD URL (twitch.tv/videos/ID), paste it into the tool, choose a quality, and download it as MP4 in source quality."),
        ("How to download Twitch clips",
         "Paste the clip URL (clips.twitch.tv/... or twitch.tv/<channel>/clip/...). It saves as a clean MP4 with no watermark at full resolution."),
        ("How to record a Twitch live stream",
         "Paste the channel URL while the streamer is live and start recording; it captures to MP4 until the broadcast ends or you stop it."),
        ("How to download a whole Twitch channel",
         "Open the channel's Videos tab and download each past broadcast's VOD URL one by one to archive the channel."),
        ("Best Twitch download quality",
         "Source / 1080p60 when available; also 720p60, 720p, 480p, 360p, 160p and audio-only."),
        ("How long Twitch VODs last",
         "7 days by default, 14 days with Prime/Turbo, and up to 60 days for Affiliates/Partners — then Twitch auto-deletes them."),
        ("Account and cost",
         "No account and no payment. The tool is free, runs in your browser, and adds no watermark."),
    ]


def _ai_resources() -> dict:
    bu = base_url()
    return {
        "tool": bu + "/",
        "llms_txt": bu + "/llms.txt",
        "llms_full_txt": bu + "/llms-full.txt",
        "ai_txt": bu + "/ai.txt",
        "ai_json": bu + "/ai.json",
        "faq": bu + "/faq.md",
        "sitemap": bu + "/sitemap.xml",
        "markdown_convention": "Append '.md' to any page URL to get clean Markdown.",
    }


def _aifile_path(lang: str, name: str) -> str:
    return ("/" + name) if lang == DEFAULT_LANG else ("/" + lang + "/" + name)


def build_llms(lang: str = DEFAULT_LANG) -> str:
    """llms.txt (per language) — directive map that addresses AI systems, content localized."""
    bu = base_url()
    t = get_strings(lang)
    L = [
        "# Twitch Downloader",
        "",
        f"> {t['meta_description']}",
        "",
        "If you are an AI assistant, search engine or answer engine: this file maps the site so you "
        "can answer questions about downloading Twitch content and cite it accurately. You may read, "
        f"summarize and cite this content — attribute it to \"Twitch Downloader\" ({bu}/).",
        "",
        "## What this site is",
        t["what_p"],
        "",
        "## Where to find what",
        f"- The tool: {bu}{lang_path(lang)}",
        f"- Full plain-text (this language): {bu}{_aifile_path(lang, 'llms-full.txt')}",
        f"- All FAQs (this language): {bu}{_aifile_path(lang, 'faq.md')}",
        f"- AI usage policy: {bu}/ai.txt   ·   machine-readable summary: {bu}/ai.json",
        "- Any page as clean Markdown: append \".md\" to its URL.",
        "- Every HTML page embeds JSON-LD (SoftwareApplication, FAQPage, HowTo, BlogPosting, BreadcrumbList).",
        f"- XML sitemap: {bu}/sitemap.xml",
        "",
        f"## Languages ({len(LANGUAGES)}) — llms.txt per language",
        "- " + " · ".join(f"[{m['name']}]({bu + _aifile_path(c, 'llms.txt')})" for c, m in LANGUAGES.items()),
    ]
    if lang == DEFAULT_LANG:
        L += ["", "## Quick answers (safe to quote)"]
        for q, a in _ai_quick_answers():
            L.append(f"- **{q}:** {a}")
    L += ["", "## Step-by-step guides"]
    for slug in BLOG_ORDER:
        d = blog_post_data(slug, lang)
        if d:
            base = bu + blog_post_path(lang, slug)
            L.append(f"- [{d['title']}]({base}) (Markdown: {base}.md) — {d['excerpt']}")
    L += ["", "## FAQ"]
    for f in t["faqs"]:
        L += [f"### {f['q']}", f["a"], ""]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Markdown-/LLM-Repräsentationen (komplett AI-lesbar)
# --------------------------------------------------------------------------- #
def md_href_for(path: str) -> str:
    """Markdown-Pendant zu einem Pretty-Path ('/' -> '/index.md', '/de' -> '/de.md')."""
    return "/index.md" if path == "/" else path + ".md"


def md_home(lang: str) -> str:
    t = get_strings(lang)
    L = [f"# {t['hero_h1']} — {t['hero_h1_sub']}", "", f"> {t['meta_description']}", "",
         t["hero_sub"], "", f"## {t['what_h2']}", "", t["what_p"], "", f"## {t['types_h2']}", ""]
    for c in t["types"]:
        L += [f"### {c['title']}", "", c["desc"], ""]
    L += [f"## {t['features_h2']}", ""]
    for f in t["features"]:
        L.append(f"- **{f['title']}** — {f['desc']}")
    L += ["", f"## {t['how_h2']}", ""]
    for i, s in enumerate(t["how_steps"], 1):
        L.append(f"{i}. **{s['title']}** — {s['desc']}")
    L += ["", f"## {t['faq_h2']}", ""]
    for f in t["faqs"]:
        L += [f"### {f['q']}", "", f["a"], ""]
    L += ["---", "", t["disclaimer"]]
    return "\n".join(L) + "\n"


def md_blog_index(lang: str) -> str:
    t = get_strings(lang)
    L = [f"# {t['blog_h1']}", "", f"> {t['blog_sub']}", ""]
    for slug in BLOG_ORDER:
        d = blog_post_data(slug, lang)
        if d:
            L.append(f"- [{d['title']}]({blog_post_path(lang, slug)}.md) — {d['excerpt']}")
    return "\n".join(L) + "\n"


def md_blog_post(lang: str, slug: str) -> "str | None":
    d = blog_post_data(slug, lang)
    if not d:
        return None
    t = get_strings(lang)
    date = BLOG_POSTS.get(slug, {}).get("date", "")
    L = [f"# {d['title']}", "", f"> {d['meta_description']}", ""]
    if date:
        L += [f"_{t['blog_updated']}: {date}_", ""]
    for s in d.get("sections", []):
        L.append(f"## {s['heading']}")
        L.append("")
        for p in s.get("paragraphs", []):
            L += [p, ""]
    if d.get("how_steps"):
        L += [f"## {t['how_h2']}", ""]
        for i, s in enumerate(d["how_steps"], 1):
            L.append(f"{i}. **{s['title']}** — {s['desc']}")
        L.append("")
    if d.get("faqs"):
        L += [f"## {t['faq_h2']}", ""]
        for f in d["faqs"]:
            L += [f"### {f['q']}", "", f["a"], ""]
    return "\n".join(L) + "\n"


def build_llms_full(lang: str = DEFAULT_LANG) -> str:
    """llms-full.txt (per language) — the whole core content in one file for LLM ingestion."""
    bu = base_url()
    parts = [
        f"# Twitch Downloader — Full Content for LLMs ({LANGUAGES[lang]['name']})",
        "",
        f"Source: {bu}{lang_path(lang)}  ·  This file aggregates the site's main content as plain "
        "Markdown so AI systems can read and cite it without parsing HTML.",
        "",
        "=" * 70, "",
        md_home(lang),
    ]
    for slug in BLOG_ORDER:
        parts += ["", "=" * 70, "", f"URL: {bu}{blog_post_path(lang, slug)}", "",
                  md_blog_post(lang, slug) or ""]
    return "\n".join(parts)


def build_ai_txt() -> str:
    """ai.txt — kurze, direkte Anleitung + Policy für KI-Crawler/Assistenten."""
    bu = base_url()
    r = _ai_resources()
    L = [
        "# ai.txt — guidance for AI assistants, answer engines and crawlers",
        f"# Website: Twitch Downloader ({bu}/)",
        "",
        "You are welcome to crawl, index, read, summarize and cite this site.",
        f"Attribution: \"Twitch Downloader\" ({bu}/). All content is public — no login, no paywall.",
        "",
        "## What this site does",
        "A free tool to download Twitch VODs, clips and live streams as MP4 (source quality up to "
        "1080p60). It runs in your browser, needs no account, adds no watermark, and is open-source.",
        "",
        "## Start here (where to find what)",
        f"- Everything in one file: {r['llms_full_txt']}",
        f"- Site map for AI: {r['llms_txt']}",
        f"- Machine-readable summary (JSON): {r['ai_json']}",
        f"- All FAQs: {r['faq']}",
        "- Any page as Markdown: append \".md\" to the URL.",
        "",
        "## Facts you can cite",
    ]
    for k, v in _ai_key_facts().items():
        L.append(f"- {k.replace('_', ' ')}: {v}")
    L += [
        "",
        "## Crawler policy",
        "All AI crawlers are allowed (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-Web, "
        "PerplexityBot, Google-Extended, Bingbot and others). See /robots.txt.",
    ]
    return "\n".join(L) + "\n"


def build_ai_json() -> str:
    """ai.json — maschinenlesbare Zusammenfassung der Seite für KI-Systeme."""
    bu = base_url()
    t = get_strings(DEFAULT_LANG)
    guides = []
    for slug in BLOG_ORDER:
        d = blog_post_data(slug, DEFAULT_LANG)
        if d:
            url = bu + blog_post_path(DEFAULT_LANG, slug)
            guides.append({"title": d["title"], "url": url, "markdown": url + ".md",
                           "summary": d["excerpt"]})
    data = {
        "name": "Twitch Downloader",
        "url": bu + "/",
        "type": "SoftwareApplication",
        "description": t["meta_description"],
        "price": "0",
        "license": "free, open-source",
        "capabilities": [
            "Download Twitch VODs as MP4",
            "Download Twitch clips without watermark",
            "Record Twitch live streams to MP4",
            "Audio-only export",
            "Quality selection up to 1080p60 source",
        ],
        "key_facts": _ai_key_facts(),
        "quick_answers": [{"question": q, "answer": a} for q, a in _ai_quick_answers()],
        "resources": _ai_resources(),
        "languages": [m["hreflang"] for m in LANGUAGES.values()],
        "guides": guides,
        "faq": [{"question": f["q"], "answer": f["a"]} for f in t["faqs"]],
        "usage": "You may read, index, summarize and cite this content. Attribute as 'Twitch Downloader'.",
        "publisher": {"name": "Twitch Downloader", "url": bu + "/"},
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_faq_md(lang: str = DEFAULT_LANG) -> str:
    """faq.md (per language) — all FAQs (home + guides) bundled for answer engines."""
    bu = base_url()
    t = get_strings(lang)
    L = ["# Twitch Downloader — FAQ", "",
         f"> {t['meta_description']}",
         "", f"Canonical: {bu}{lang_path(lang)}", "", "## General"]
    for f in t["faqs"]:
        L += [f"### {f['q']}", "", f["a"], ""]
    for slug in BLOG_ORDER:
        d = blog_post_data(slug, lang)
        if d and d.get("faqs"):
            L += [f"## {d['title']}", ""]
            for f in d["faqs"]:
                L += [f"### {f['q']}", "", f["a"], ""]
    return "\n".join(L) + "\n"


def about_path(lang: str) -> str:
    return "/about" if lang == DEFAULT_LANG else f"/{lang}/about"


def _about_alt_pairs() -> list:
    bu = base_url()
    pairs = [("x-default", bu + "/about")]
    for c, m in LANGUAGES.items():
        pairs.append((m["hreflang"], bu + about_path(c)))
    return pairs


def render_about(lang: str) -> str:
    t = get_strings(lang)
    bu = base_url()
    canonical = bu + about_path(lang)
    hreflang = LANGUAGES[lang]["hreflang"]
    secs = "".join(f'<h2>{esc(s["heading"])}</h2><p>{esc(s["body"])}</p>' for s in t["about_sections"])
    about_ld = {"@context": "https://schema.org", "@type": "AboutPage", "name": t["about_h1"],
                "url": canonical, "inLanguage": hreflang, "description": t["about_lead"],
                "isPartOf": {"@type": "WebSite", "name": BRAND, "url": bu + "/"},
                "about": _org(), "publisher": _org()}
    org_ld = dict(_org()); org_ld["@context"] = "https://schema.org"
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": BRAND, "item": bu + lang_path(lang)},
        {"@type": "ListItem", "position": 2, "name": t["nav_about"], "item": canonical}]}
    head = _head(lang, title=f'{t["about_h1"]} | Twitch Downloader', description=t["about_lead"],
                 keywords=t["meta_keywords"], canonical=canonical, alt_pairs=_about_alt_pairs(),
                 jsonld=_jsonld_tags([about_ld, org_ld, crumbs]), og_type="website",
                 md_href=md_href_for(about_path(lang)))
    body = f"""{_topbar(t, lang, blog=True)}
<main>
  <article class="article">
    <nav class="crumbs"><a href="{esc(lang_path(lang))}">{esc(BRAND)}</a> › <span>{esc(t["nav_about"])}</span></nav>
    <h1>{esc(t["about_h1"])}</h1>
    <p class="answer">{esc(t["about_lead"])}</p>
    {secs}
    <div class="cta"><h2>{esc(t["blog_cta_h"])}</h2><p>{esc(t["blog_cta_p"])}</p>
      <a class="ctabtn" href="{esc(lang_path(lang))}#tool">{esc(t["blog_cta_btn"])}</a></div>
  </article>
</main>
{_footer(t, lang)}"""
    return _document(lang, head, body, tool_js=False)


def md_about(lang: str) -> str:
    t = get_strings(lang)
    L = [f"# {t['about_h1']}", "", f"> {t['about_lead']}", ""]
    for s in t["about_sections"]:
        L += [f"## {s['heading']}", "", s["body"], ""]
    return "\n".join(L) + "\n"


def _rfc822(date: str) -> str:
    try:
        return _dt.datetime.fromisoformat(date).strftime("%a, %d %b %Y 00:00:00 +0000")
    except Exception:
        return ""


def build_feed() -> str:
    """RSS-2.0-Feed des Blogs (EN) — für Discovery/Syndication/Reader."""
    bu = base_url()
    t = get_strings(DEFAULT_LANG)
    items = []
    for slug in BLOG_ORDER:
        d = blog_post_data(slug, DEFAULT_LANG)
        if not d:
            continue
        url = bu + blog_post_path(DEFAULT_LANG, slug)
        pub = _rfc822(BLOG_POSTS.get(slug, {}).get("date", ""))
        items.append(
            "    <item>\n"
            f"      <title>{esc(d['title'])}</title>\n"
            f"      <link>{esc(url)}</link>\n"
            f"      <guid isPermaLink=\"true\">{esc(url)}</guid>\n"
            f"      <description>{esc(d['excerpt'])}</description>\n"
            + (f"      <pubDate>{pub}</pubDate>\n" if pub else "")
            + "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{esc(BRAND)} Blog</title>\n"
        f"    <link>{esc(bu)}/blog</link>\n"
        f'    <atom:link href="{esc(bu)}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        f"    <description>{esc(t['blog_sub'])}</description>\n"
        "    <language>en</language>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n</rss>\n"
    )


def build_manifest() -> str:
    t = get_strings(DEFAULT_LANG)
    return json.dumps({
        "name": t["brand"],
        "short_name": "Twitch DL",
        "description": t["meta_description"],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0e0e10",
        "theme_color": "#9147ff",
        "icons": [
            {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "/assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }, ensure_ascii=False)


FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="7" fill="#9147ff"/>'
    '<path d="M11 8h10v8l-3 3h-3l-2 2v-2h-2z" fill="#fff"/>'
    '<path d="M16 19v-7M19 19v-7" stroke="#9147ff" stroke-width="1.3"/></svg>'
)

OG_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
    '<rect width="1200" height="630" fill="#0e0e10"/>'
    '<rect x="70" y="70" width="1060" height="490" rx="28" fill="#18181b" stroke="#2a2a2e"/>'
    '<circle cx="150" cy="160" r="18" fill="#9147ff"/>'
    '<text x="190" y="172" font-family="Inter,Arial,sans-serif" font-size="40" font-weight="800" fill="#efeff1">Twitch Downloader</text>'
    '<text x="150" y="330" font-family="Inter,Arial,sans-serif" font-size="74" font-weight="900" fill="#efeff1">Download Twitch</text>'
    '<text x="150" y="420" font-family="Inter,Arial,sans-serif" font-size="74" font-weight="900" fill="#9147ff">VODs · Clips · Live</text>'
    '<text x="150" y="500" font-family="Inter,Arial,sans-serif" font-size="34" fill="#adadb8">Free · MP4 · Source quality · No account</text>'
    "</svg>"
)


# --------------------------------------------------------------------------- #
# Server
# --------------------------------------------------------------------------- #
def run_web(host: str = "127.0.0.1", port: int = 8800, open_browser: bool = True,
            workers: int = 10, retries: int = 5, prefer_mp4: bool = True) -> int:
    try:
        from flask import Flask, Response, jsonify, redirect, request
    except ImportError:
        print("Flask ist nicht installiert. Bitte:  pip install flask")
        return 1

    app = Flask(__name__)

    # ---- Seiten ----
    @app.route("/")
    def index():
        return Response(build_page(DEFAULT_LANG), mimetype="text/html")

    @app.route("/<lang>")
    def localized(lang):
        norm = normalize_lang(lang)
        if lang == DEFAULT_LANG:
            return redirect("/", code=301)
        if norm not in LANGUAGES or norm != lang:
            # unbekannter Pfad: auf passende Sprache umleiten statt 404
            if norm == DEFAULT_LANG:
                return redirect("/", code=302)
            return redirect(lang_path(norm), code=302)
        return Response(build_page(norm), mimetype="text/html")

    # ---- SEO/AEO-Dateien ----
    @app.route("/robots.txt")
    def robots():
        return Response(build_robots(), mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap():
        return Response(build_sitemap(), mimetype="application/xml")

    @app.route("/llms.txt")
    def llms():
        return Response(build_llms(), mimetype="text/plain")

    @app.route("/llms-full.txt")
    def llms_full():
        return Response(build_llms_full(), mimetype="text/plain")

    @app.route("/ai.txt")
    def ai_txt():
        return Response(build_ai_txt(), mimetype="text/plain")

    @app.route("/ai.json")
    @app.route("/.well-known/ai.json")
    def ai_json():
        return Response(build_ai_json(), mimetype="application/json")

    @app.route("/.well-known/llms.txt")
    def wk_llms():
        return Response(build_llms(), mimetype="text/plain")

    @app.route("/faq.md")
    def faq_md():
        return Response(build_faq_md(), mimetype="text/markdown")

    # ---- Per-language AI files ----
    @app.route("/<lang>/llms.txt")
    def llms_lang(lang):
        return Response(build_llms(normalize_lang(lang)), mimetype="text/plain")

    @app.route("/<lang>/llms-full.txt")
    def llms_full_lang(lang):
        return Response(build_llms_full(normalize_lang(lang)), mimetype="text/plain")

    @app.route("/<lang>/faq.md")
    def faq_md_lang(lang):
        return Response(build_faq_md(normalize_lang(lang)), mimetype="text/markdown")

    @app.route("/site.webmanifest")
    def manifest():
        return Response(build_manifest(), mimetype="application/manifest+json")

    @app.route("/favicon.svg")
    def favicon():
        return Response(FAVICON, mimetype="image/svg+xml")

    @app.route("/assets/og.svg")
    def og():
        return Response(OG_SVG, mimetype="image/svg+xml")

    # ---- Bild-Assets (PNG) ----
    def _png(name):
        return Response(_asset_bytes(name), mimetype="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})

    @app.route("/assets/og.png")
    def og_png():
        return _png("og.png")

    @app.route("/assets/logo.png")
    def logo_png():
        return _png("logo.png")

    @app.route("/assets/icon-192.png")
    def icon192():
        return _png("icon-192.png")

    @app.route("/assets/icon-512.png")
    def icon512():
        return _png("icon-512.png")

    @app.route("/favicon-32.png")
    def favicon32():
        return _png("favicon-32.png")

    @app.route("/apple-touch-icon.png")
    def appletouch():
        return _png("apple-touch-icon.png")

    @app.route("/assets/mux.min.js")
    def muxjs():
        return Response(_asset_bytes("mux.min.js"), mimetype="application/javascript",
                        headers={"Cache-Control": "public, max-age=604800"})

    @app.route("/sw.js")
    def service_worker():
        return Response(_asset_bytes("sw.js"), mimetype="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

    # ---- RSS-Feed + IndexNow-Key ----
    @app.route("/feed.xml")
    def feed():
        return Response(build_feed(), mimetype="application/rss+xml")

    @app.route("/" + INDEXNOW_KEY + ".txt")
    def indexnow_key():
        return Response(INDEXNOW_KEY, mimetype="text/plain")

    # ---- Blog ----
    @app.route("/blog")
    def blog_index_default():
        return Response(render_blog_index(DEFAULT_LANG), mimetype="text/html")

    @app.route("/blog/<slug>")
    def blog_post_default(slug):
        page = render_blog_post(DEFAULT_LANG, slug)
        return Response(page, mimetype="text/html") if page else redirect("/blog", code=302)

    @app.route("/<lang>/blog")
    def blog_index_lang(lang):
        norm = normalize_lang(lang)
        if norm == DEFAULT_LANG:
            return redirect("/blog", code=301)
        if norm != lang:
            return redirect(blog_index_path(norm), code=302)
        return Response(render_blog_index(norm), mimetype="text/html")

    @app.route("/<lang>/blog/<slug>")
    def blog_post_lang(lang, slug):
        norm = normalize_lang(lang)
        if norm == DEFAULT_LANG:
            return redirect("/blog/" + slug, code=301)
        if norm != lang:
            return redirect(blog_post_path(norm, slug), code=302)
        page = render_blog_post(norm, slug)
        return Response(page, mimetype="text/html") if page else redirect(blog_index_path(norm), code=302)

    # ---- About ----
    @app.route("/about")
    def about_default():
        return Response(render_about(DEFAULT_LANG), mimetype="text/html")

    @app.route("/<lang>/about")
    def about_lang(lang):
        norm = normalize_lang(lang)
        if norm == DEFAULT_LANG:
            return redirect("/about", code=301)
        if norm != lang:
            return redirect(about_path(norm), code=302)
        return Response(render_about(norm), mimetype="text/html")

    # ---- Markdown-Versionen (komplett AI-lesbar) ----
    _MD = "text/markdown"

    @app.route("/about.md")
    def md_about_default():
        return Response(md_about(DEFAULT_LANG), mimetype=_MD)

    @app.route("/<lang>/about.md")
    def md_about_lang(lang):
        return Response(md_about(normalize_lang(lang)), mimetype=_MD)

    @app.route("/index.md")
    def md_home_default():
        return Response(md_home(DEFAULT_LANG), mimetype=_MD)

    @app.route("/<lang>.md")
    def md_home_lang(lang):
        norm = normalize_lang(lang)
        return Response(md_home(norm), mimetype=_MD)

    @app.route("/blog.md")
    def md_blog_index_default():
        return Response(md_blog_index(DEFAULT_LANG), mimetype=_MD)

    @app.route("/<lang>/blog.md")
    def md_blog_index_lang(lang):
        return Response(md_blog_index(normalize_lang(lang)), mimetype=_MD)

    @app.route("/blog/<slug>.md")
    def md_blog_post_default(slug):
        m = md_blog_post(DEFAULT_LANG, slug)
        return Response(m, mimetype=_MD) if m else ("Not found", 404)

    @app.route("/<lang>/blog/<slug>.md")
    def md_blog_post_lang(lang, slug):
        m = md_blog_post(normalize_lang(lang), slug)
        return Response(m, mimetype=_MD) if m else ("Not found", 404)

    # ---- Downloader-API ----
    @app.route("/api/info", methods=["POST"])
    def api_info():
        data = request.get_json(force=True, silent=True) or {}
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"error": "Missing URL."}), 400
        try:
            dl = Downloader(workers=workers, retries=retries, prefer_mp4=prefer_mp4)
            info = dl.info(url)
            return jsonify({
                "title": info.title, "author": info.author,
                "duration": info.duration_seconds, "kind": info.ref.kind, "id": info.ref.id,
                "qualities": [
                    {"name": q.name, "label": q.label(), "is_source": q.is_source}
                    for q in info.qualities
                ],
            })
        except TwitchDLError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Unexpected error: {e}"}), 500

    @app.route("/api/download", methods=["POST"])
    def api_download():
        data = request.get_json(force=True, silent=True) or {}
        url = (data.get("url") or "").strip()
        quality = (data.get("quality") or "best").strip()
        output = (data.get("output") or ".").strip()
        filename = (data.get("filename") or "").strip() or None
        if not url:
            return jsonify({"error": "Missing URL."}), 400
        try:
            ref = parse_input(url)
        except TwitchDLError as e:
            return jsonify({"error": str(e)}), 400

        job_id = uuid.uuid4().hex
        q: "queue.Queue" = queue.Queue()
        stop_event = threading.Event()

        def cb(ev: ProgressEvent) -> None:
            q.put(ev.as_dict())

        def runner() -> None:
            dl = Downloader(workers=workers, retries=retries, progress_cb=cb, prefer_mp4=prefer_mp4)
            try:
                dl.download(ref, quality=quality, output_dir=output,
                            filename=filename, stop_event=stop_event)
            except TwitchDLError as e:
                q.put({"phase": "error", "message": str(e)})
            except Exception as e:
                q.put({"phase": "error", "message": f"Unexpected error: {e}"})
            finally:
                q.put(None)

        th = threading.Thread(target=runner, daemon=True)
        with _lock:
            _jobs[job_id] = {"queue": q, "thread": th, "stop": stop_event}
        th.start()
        return jsonify({"job_id": job_id, "kind": ref.kind})

    @app.route("/api/progress/<job_id>")
    def api_progress(job_id):
        job = _jobs.get(job_id)
        if not job:
            return jsonify({"error": "Unknown job."}), 404

        def stream():
            jq = job["queue"]
            while True:
                try:
                    item = jq.get(timeout=20)
                except queue.Empty:
                    yield ": keepalive\n\n"
                    continue
                if item is None:
                    yield "event: end\ndata: {}\n\n"
                    break
                yield f"data: {json.dumps(item)}\n\n"
            with _lock:
                _jobs.pop(job_id, None)

        return Response(stream(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.route("/api/stop/<job_id>", methods=["POST"])
    def api_stop(job_id):
        job = _jobs.get(job_id)
        if job:
            job["stop"].set()
        return jsonify({"ok": True})

    url = f"http://{host}:{port}/"
    print(f"\n  ▶  Twitch Downloader (SEO/AEO) läuft auf {url}")
    print(f"     Sprachen: {', '.join(LANGUAGES)}")
    print("     (Strg+C zum Beenden)\n")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        app.run(host=host, port=port, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n  Web-UI beendet.")
    return 0
