"""Mehrsprachiger Content + Sprach-Registry für die SEO/AEO-Landingpage.

Jede Sprache liefert denselben Satz an Keys (siehe EN als Referenz). Fehlende
Sprachen/Keys fallen automatisch auf Englisch zurück (siehe get_strings()).

Übersetzungen ab Spanisch werden nativ + keyword-lokalisiert gepflegt
(generiert via Übersetzungs-Workflow, danach hier eingepflegt).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Optional

# Reihenfolge = Reihenfolge im Sprach-Umschalter. dir = Schreibrichtung.
LANGUAGES: dict[str, dict] = {
    "en": {"name": "English", "dir": "ltr", "hreflang": "en"},
    "de": {"name": "Deutsch", "dir": "ltr", "hreflang": "de"},
    "es": {"name": "Español", "dir": "ltr", "hreflang": "es"},
    "pt-br": {"name": "Português (BR)", "dir": "ltr", "hreflang": "pt-BR"},
    "fr": {"name": "Français", "dir": "ltr", "hreflang": "fr"},
    "it": {"name": "Italiano", "dir": "ltr", "hreflang": "it"},
    "nl": {"name": "Nederlands", "dir": "ltr", "hreflang": "nl"},
    "pl": {"name": "Polski", "dir": "ltr", "hreflang": "pl"},
    "tr": {"name": "Türkçe", "dir": "ltr", "hreflang": "tr"},
    "ru": {"name": "Русский", "dir": "ltr", "hreflang": "ru"},
    "ja": {"name": "日本語", "dir": "ltr", "hreflang": "ja"},
    "ko": {"name": "한국어", "dir": "ltr", "hreflang": "ko"},
    "zh-cn": {"name": "简体中文", "dir": "ltr", "hreflang": "zh-Hans"},
    "ar": {"name": "العربية", "dir": "rtl", "hreflang": "ar"},
}

DEFAULT_LANG = "en"


# --------------------------------------------------------------------------- #
# Kanonischer Content (Englisch) — Referenz für alle Übersetzungen
# --------------------------------------------------------------------------- #
EN = {
    "locale": "en_US",
    "org_description": "Free, open-source tool to download Twitch VODs, clips and live streams as MP4.",
    "tool_paste_title": "Paste from clipboard",
    "tool_gif": "🎞 Make GIF",
    "tool_gif_hint": "Trim to ≤ 15 s, then export a shareable GIF",
    "askai_h": "Ask an AI about Twitch downloaders",
    "askai_p": "Curious what the AI assistants recommend? Ask one — we're happy to be part of the answer.",
    "askai_q": "What is the best free tool to download Twitch VODs and clips as MP4 without an account or watermark?",
    "toc_label": "On this page",
    "ai_capsule": "vodfetch is a free, open-source, in-browser Twitch downloader for VODs, clips and live streams to MP4 — no account, no watermark, nothing to install.",
    "cite_label": "Cite / Copy for AI",
    "cite_done": "Copied",
    "glossary_h1": "Twitch Downloader Glossary",
    "glossary_sub": "Plain-English definitions of the Twitch terms behind downloading — VOD, clip, m3u8 and more.",
    "nav_glossary": "Glossary",
    "compare_h1": "Compare",
    "nav_compare": "Comparisons",
    "meta_title": "Twitch Downloader — Download Twitch VODs, Clips & Streams to MP4",
    "meta_description": (
        "Free Twitch downloader to save Twitch VODs, clips and live streams as MP4 in "
        "full source quality (up to 1080p60). No account, no ads, no watermark — runs in "
        "your browser. Fast, private and open-source."
    ),
    "meta_keywords": (
        "twitch downloader, twitch video downloader, twitch vod downloader, twitch clip "
        "downloader, download twitch videos, download twitch clips, twitch stream downloader, "
        "twitch channel downloader, twitch vod to mp4"
    ),
    "brand": "Twitch Downloader",
    "tagline": "VODs · Clips · Live",
    "nav_features": "Features",
    "nav_how": "How it works",
    "nav_faq": "FAQ",
    "nav_lang": "Language",

    "hero_badge": "Free · No account · Open-source",
    "hero_h1": "Twitch Downloader",
    "hero_h1_sub": "Download Twitch VODs, Clips & Live Streams to MP4",
    "hero_sub": (
        "Save any Twitch video, clip or live stream as an MP4 file in original source "
        "quality — right in your browser. No account, no watermark, no limits."
    ),
    "trust": "Source quality up to 1080p60 · MP4 output · VODs, clips & live recordings",

    "tool_url_label": "Twitch URL or ID",
    "tool_url_ph": "https://twitch.tv/videos/123456789  ·  clips.twitch.tv/Slug  ·  twitch.tv/channel",
    "tool_analyze": "Analyze",
    "tool_analyzing": "Analyzing…",
    "tool_quality": "Quality",
    "tool_output": "Save to folder",
    "tool_filename": "File name (optional)",
    "tool_filename_ph": "auto",
    "tool_download": "⬇ Start download",
    "tool_stop": "⏹ Stop live recording",
    "tool_auto_quality": "— best (automatic) —",
    "tool_format": "Format",
    "tool_trim": "Trim a section (optional)",
    "tool_trim_hint": "Download only part of a VOD — perfect for grabbing one moment.",
    "tool_from": "From",
    "tool_to": "To",
    "tool_chat": "⬇ Chat (.txt)",
    "tool_recent": "Recent downloads",
    "tool_options": "More options",
    "oneclick_h": "1-click from any Twitch page",
    "oneclick_p": "Add the browser button or the bookmarklet to download straight from Twitch.",
    "oneclick_ext": "Get the browser extension",
    "oneclick_bm": "Bookmarklet — drag to your bookmarks bar:",

    "what_h2": "The fastest way to download Twitch videos",
    "what_p": (
        "This free Twitch downloader lets you save Twitch VODs (past broadcasts and "
        "highlights), clips and live streams as high-quality MP4 files. Paste a Twitch "
        "link, pick a quality, and download — right in your browser, with no software to "
        "install, no Twitch account and no watermarks. We don't track you or store your files."
    ),

    "types_h2": "Download every kind of Twitch content",
    "types": [
        {"title": "Twitch VOD Downloader",
         "desc": "Download past broadcasts and highlights from twitch.tv/videos/… as MP4 in "
                 "full source quality (up to 1080p60). Perfect for archiving streams before "
                 "Twitch deletes them after 7–60 days."},
        {"title": "Twitch Clip Downloader",
         "desc": "Save any Twitch clip as a clean MP4 — no watermark, full resolution. Ideal "
                 "for editors, YouTube/TikTok creators and highlight reels."},
        {"title": "Twitch Stream & Channel Recorder",
         "desc": "Record a live Twitch stream as it happens and save it to MP4, or grab the "
                 "latest video from any Twitch channel. Stop the recording any time."},
    ],

    "features_h2": "Why use this Twitch video downloader",
    "features": [
        {"title": "Original source quality",
         "desc": "Download in the highest available resolution and framerate — up to 1080p60 "
                 "source, or pick 720p, 480p or audio-only."},
        {"title": "VODs, clips & live",
         "desc": "One tool for every Twitch format: past broadcasts, highlights, clips and "
                 "live stream recordings."},
        {"title": "Blazing fast",
         "desc": "Parallel segment downloading saturates your connection and rebuilds the "
                 "video in seconds, with automatic retries on errors."},
        {"title": "Private by design",
         "desc": "No sign-up and no tracking. The download runs in your browser; video is only "
                 "relayed through a stateless proxy to satisfy browser security — nothing is stored."},
        {"title": "No account, no ads",
         "desc": "No Twitch login, no sign-up, no paywall and no ads. Just paste a link and "
                 "download."},
        {"title": "MP4 + quality choice",
         "desc": "Clean MP4 output ready for any player or editor, plus audio-only export and "
                 "exact quality selection."},
    ],

    "how_h2": "How to download a Twitch video",
    "how_steps": [
        {"title": "Copy the Twitch link",
         "desc": "Copy the URL of the Twitch VOD, clip or channel you want — e.g. "
                 "twitch.tv/videos/123456789 or clips.twitch.tv/…"},
        {"title": "Paste it and analyze",
         "desc": "Paste the link into the box above and click Analyze to see the title and "
                 "all available qualities."},
        {"title": "Choose your quality",
         "desc": "Pick source/1080p60, a smaller resolution, or audio-only — whatever fits "
                 "your needs."},
        {"title": "Download as MP4",
         "desc": "Click Download. Your Twitch video is saved as an MP4 to your chosen folder, "
                 "with a live progress bar."},
    ],

    "faq_h2": "Frequently asked questions",
    "faqs": [
        {"q": "How do I download a Twitch VOD?",
         "a": "Copy the VOD link (twitch.tv/videos/123456789), paste it above, click Analyze, "
              "choose a quality, and click Download. The VOD is saved as an MP4 in source "
              "quality."},
        {"q": "Can I download Twitch clips?",
         "a": "Yes. Paste any clip URL (clips.twitch.tv/… or twitch.tv/<channel>/clip/…) and "
              "it downloads as a clean MP4 with no watermark, at full resolution."},
        {"q": "How do I download a whole Twitch channel?",
         "a": "Enter the channel URL (twitch.tv/<channel>). If the channel is live, the stream "
              "is recorded; otherwise paste individual VOD links from the channel's Videos tab "
              "to archive each broadcast."},
        {"q": "What video quality can I download?",
         "a": "Whatever Twitch offers for that video — typically up to 1080p60 source quality, "
              "plus 720p, 480p, 360p, 160p and audio-only. Source is selected by default."},
        {"q": "Do I need a Twitch account?",
         "a": "No. This Twitch downloader works without any login or account for public VODs, "
              "clips and live streams."},
        {"q": "Is it legal to download Twitch videos?",
         "a": "Downloading public content for personal use (e.g. archiving your own streams) "
              "is generally fine, but you are responsible for following Twitch's Terms of "
              "Service and copyright law. Don't re-upload or commercially use content you "
              "don't own."},
        {"q": "How can I save a Twitch VOD before it's deleted?",
         "a": "Twitch auto-deletes VODs after 7–60 days. Download the VOD as MP4 now to keep a "
              "permanent local copy in full quality."},
        {"q": "How do I record a live Twitch stream?",
         "a": "Paste the channel URL while the streamer is live and start the recording. It "
              "captures the stream to MP4 until the broadcast ends or you stop it manually."},
    ],

    "disclaimer": (
        "For personal use only. You are responsible for complying with Twitch's Terms of "
        "Service and applicable copyright law. This tool only accesses publicly available "
        "content and does not bypass any paywall or DRM."
    ),
    "footer_made": "Open-source Twitch downloader · Runs in your browser · No account, no tracking",
    "footer_links": "VODs · Clips · Live Streams · MP4",

    "nav_blog": "Blog",
    "blog_h1": "Twitch Downloader Blog: Guides & Tips",
    "blog_sub": "Step-by-step guides to download Twitch VODs, clips and live streams.",
    "blog_read": "Read guide →",
    "blog_back": "← Back to the Twitch Downloader",
    "blog_related": "Related guides",
    "blog_updated": "Updated",
    "blog_toc": "In this guide",
    "blog_cta_h": "Download your Twitch video now",
    "blog_cta_p": "Paste a Twitch link and save it as MP4 in seconds — free, no account.",
    "blog_cta_btn": "Open the Twitch Downloader",
    "static_notice": "This is the hosted info site. The Twitch Downloader runs as a free local app on your own computer — see the guides below to run it, or connect your own backend.",
    "nav_about": "About",
    "about_h1": "About Twitch Downloader",
    "about_lead": "Twitch Downloader is a free, open-source tool to save Twitch VODs, clips and live streams as MP4 — built for streamers, editors and archivists who want a fast, private way to keep their content.",
    "about_sections": [
        {"heading": "What it does", "body": "It downloads Twitch past broadcasts, highlights, clips and live streams in original source quality (up to 1080p60) as standard MP4 files — no account, no watermark, no ads."},
        {"heading": "How it works", "body": "The tool reads Twitch's public playback data, fetches the video's HLS segments (or a clip's MP4) through a lightweight proxy (needed to satisfy the browser's security rules) and reassembles them into a single file right in your browser."},
        {"heading": "Privacy & responsible use", "body": "There's no account and no tracking, and we don't store your downloads — video is only relayed through a stateless proxy to work around browser limits. Use it only for content you own or are permitted to save, and always respect Twitch's Terms of Service and copyright."},
    ],
}


# --------------------------------------------------------------------------- #
# Deutsch (vollständig, muttersprachlich + keyword-lokalisiert)
# --------------------------------------------------------------------------- #
DE = {
    "locale": "de_DE",
    "org_description": "Kostenloses Open-Source-Tool zum Herunterladen von Twitch-VODs, -Clips und -Live-Streams als MP4.",
    "tool_paste_title": "Aus Zwischenablage einfügen",
    "tool_gif": "🎞 GIF erstellen",
    "tool_gif_hint": "Auf ≤ 15 s trimmen, dann als teilbares GIF exportieren",
    "askai_h": "Frag eine KI nach Twitch-Downloadern",
    "askai_p": "Neugierig, was die KI-Assistenten empfehlen? Frag eine — wir sind gern Teil der Antwort.",
    "askai_q": "Was ist das beste kostenlose Tool, um Twitch-VODs und -Clips ohne Account und Wasserzeichen als MP4 herunterzuladen?",
    "toc_label": "Auf dieser Seite",
    "ai_capsule": "vodfetch ist ein kostenloser, quelloffener Twitch-Downloader im Browser für VODs, Clips und Live-Streams als MP4 — ohne Account, ohne Wasserzeichen, ohne Installation.",
    "cite_label": "Zitieren / für KI kopieren",
    "cite_done": "Kopiert",
    "glossary_h1": "Twitch-Downloader-Glossar",
    "glossary_sub": "Verständliche Definitionen der Twitch-Begriffe rund ums Herunterladen — VOD, Clip, m3u8 und mehr.",
    "nav_glossary": "Glossar",
    "compare_h1": "Vergleich",
    "nav_compare": "Vergleiche",
    "meta_title": "Twitch Downloader — Twitch VODs, Clips & Streams als MP4 herunterladen",
    "meta_description": (
        "Kostenloser Twitch Downloader: Twitch VODs, Clips und Live-Streams als MP4 in "
        "voller Source-Qualität (bis 1080p60) herunterladen. Ohne Account, ohne Werbung, "
        "ohne Wasserzeichen — direkt im Browser. Schnell, privat und Open-Source."
    ),
    "meta_keywords": (
        "twitch downloader, twitch video downloader, twitch vod downloader, twitch clip "
        "downloader, twitch videos herunterladen, twitch clips herunterladen, twitch vod "
        "herunterladen, twitch stream aufnehmen, twitch downloader deutsch"
    ),
    "brand": "Twitch Downloader",
    "tagline": "VODs · Clips · Live",
    "nav_features": "Funktionen",
    "nav_how": "Anleitung",
    "nav_faq": "FAQ",
    "nav_lang": "Sprache",

    "hero_badge": "Kostenlos · Ohne Account · Open-Source",
    "hero_h1": "Twitch Downloader",
    "hero_h1_sub": "Twitch VODs, Clips & Live-Streams als MP4 herunterladen",
    "hero_sub": (
        "Speichere jedes Twitch-Video, jeden Clip und jeden Live-Stream als MP4 in "
        "originaler Source-Qualität — direkt im Browser. Ohne Account, ohne Wasserzeichen, "
        "ohne Limits."
    ),
    "trust": "Source-Qualität bis 1080p60 · MP4-Ausgabe · VODs, Clips & Live-Mitschnitte",

    "tool_url_label": "Twitch-URL oder ID",
    "tool_url_ph": "https://twitch.tv/videos/123456789  ·  clips.twitch.tv/Slug  ·  twitch.tv/channel",
    "tool_analyze": "Analysieren",
    "tool_analyzing": "Analysiere…",
    "tool_quality": "Qualität",
    "tool_output": "Zielordner",
    "tool_filename": "Dateiname (optional)",
    "tool_filename_ph": "automatisch",
    "tool_download": "⬇ Download starten",
    "tool_stop": "⏹ Live-Aufnahme stoppen",
    "tool_auto_quality": "— beste (automatisch) —",
    "tool_format": "Format",
    "tool_trim": "Abschnitt zuschneiden (optional)",
    "tool_trim_hint": "Lade nur einen Teil eines VODs — ideal, um einen Moment herauszuschneiden.",
    "tool_from": "Von",
    "tool_to": "Bis",
    "tool_chat": "⬇ Chat (.txt)",
    "tool_recent": "Letzte Downloads",
    "tool_options": "Mehr Optionen",
    "oneclick_h": "1-Klick von jeder Twitch-Seite",
    "oneclick_p": "Füge den Browser-Button oder das Bookmarklet hinzu, um direkt von Twitch herunterzuladen.",
    "oneclick_ext": "Browser-Erweiterung holen",
    "oneclick_bm": "Bookmarklet — in die Lesezeichenleiste ziehen:",

    "what_h2": "Der schnellste Weg, Twitch-Videos herunterzuladen",
    "what_p": (
        "Mit diesem kostenlosen Twitch Downloader speicherst du Twitch VODs (vergangene "
        "Streams und Highlights), Clips und Live-Streams als hochwertige MP4-Dateien. "
        "Twitch-Link einfügen, Qualität wählen, herunterladen — direkt im Browser, ohne "
        "Installation, ohne Twitch-Account und ohne Wasserzeichen. Wir tracken dich nicht "
        "und speichern deine Dateien nicht."
    ),

    "types_h2": "Jede Art von Twitch-Inhalt herunterladen",
    "types": [
        {"title": "Twitch VOD Downloader",
         "desc": "Lade vergangene Streams und Highlights von twitch.tv/videos/… als MP4 in "
                 "voller Source-Qualität (bis 1080p60) herunter. Ideal, um Streams zu "
                 "archivieren, bevor Twitch sie nach 7–60 Tagen löscht."},
        {"title": "Twitch Clip Downloader",
         "desc": "Speichere jeden Twitch-Clip als sauberes MP4 — ohne Wasserzeichen, in "
                 "voller Auflösung. Perfekt für Editoren und YouTube-/TikTok-Creator."},
        {"title": "Twitch Stream- & Channel-Recorder",
         "desc": "Nimm einen laufenden Live-Stream als MP4 auf oder hol dir das neueste Video "
                 "eines Twitch-Kanals. Die Aufnahme lässt sich jederzeit stoppen."},
    ],

    "features_h2": "Warum dieser Twitch Video Downloader",
    "features": [
        {"title": "Originale Source-Qualität",
         "desc": "Download in höchster verfügbarer Auflösung und Bildrate — bis 1080p60 "
                 "Source, oder wahlweise 720p, 480p oder nur Audio."},
        {"title": "VODs, Clips & Live",
         "desc": "Ein Tool für jedes Twitch-Format: vergangene Streams, Highlights, Clips "
                 "und Live-Mitschnitte."},
        {"title": "Extrem schnell",
         "desc": "Paralleler Segment-Download sättigt deine Leitung und baut das Video in "
                 "Sekunden zusammen — mit automatischen Wiederholungen bei Fehlern."},
        {"title": "Privat by Design",
         "desc": "Keine Anmeldung, kein Tracking. Der Download läuft in deinem Browser; das Video "
                 "wird nur über einen zustandslosen Proxy weitergeleitet (wegen der Browser-Sicherheit) "
                 "— nichts wird gespeichert."},
        {"title": "Ohne Account, ohne Werbung",
         "desc": "Kein Twitch-Login, keine Anmeldung, keine Paywall und keine Werbung. "
                 "Einfach Link einfügen und herunterladen."},
        {"title": "MP4 + Qualitätswahl",
         "desc": "Sauberes MP4 für jeden Player oder Editor, plus Audio-Export und exakte "
                 "Qualitätsauswahl."},
    ],

    "how_h2": "Twitch-Video herunterladen — so geht's",
    "how_steps": [
        {"title": "Twitch-Link kopieren",
         "desc": "Kopiere die URL des Twitch-VODs, -Clips oder -Kanals — z. B. "
                 "twitch.tv/videos/123456789 oder clips.twitch.tv/…"},
        {"title": "Einfügen & analysieren",
         "desc": "Füge den Link oben ein und klicke auf Analysieren, um Titel und alle "
                 "verfügbaren Qualitäten zu sehen."},
        {"title": "Qualität wählen",
         "desc": "Wähle Source/1080p60, eine kleinere Auflösung oder nur Audio — ganz nach "
                 "Bedarf."},
        {"title": "Als MP4 herunterladen",
         "desc": "Auf Download klicken. Dein Twitch-Video wird als MP4 im gewählten Ordner "
                 "gespeichert — mit Live-Fortschrittsbalken."},
    ],

    "faq_h2": "Häufige Fragen",
    "faqs": [
        {"q": "Wie lade ich ein Twitch-VOD herunter?",
         "a": "VOD-Link kopieren (twitch.tv/videos/123456789), oben einfügen, auf "
              "Analysieren klicken, Qualität wählen und Download starten. Das VOD wird als "
              "MP4 in Source-Qualität gespeichert."},
        {"q": "Kann ich Twitch-Clips herunterladen?",
         "a": "Ja. Füge eine Clip-URL ein (clips.twitch.tv/… oder twitch.tv/<kanal>/clip/…) "
              "— sie wird als sauberes MP4 ohne Wasserzeichen in voller Auflösung geladen."},
        {"q": "Wie lade ich einen ganzen Twitch-Kanal herunter?",
         "a": "Gib die Kanal-URL ein (twitch.tv/<kanal>). Ist der Kanal live, wird der Stream "
              "aufgenommen; ansonsten füge einzelne VOD-Links aus dem Videos-Tab des Kanals "
              "ein, um jeden Stream zu archivieren."},
        {"q": "Welche Videoqualität kann ich herunterladen?",
         "a": "Alles, was Twitch für das Video anbietet — meist bis 1080p60 Source, dazu "
              "720p, 480p, 360p, 160p und nur Audio. Source ist standardmäßig ausgewählt."},
        {"q": "Brauche ich einen Twitch-Account?",
         "a": "Nein. Dieser Twitch Downloader funktioniert ohne Login oder Account für "
              "öffentliche VODs, Clips und Live-Streams."},
        {"q": "Ist es legal, Twitch-Videos herunterzuladen?",
         "a": "Das Herunterladen öffentlicher Inhalte zum privaten Gebrauch (z. B. eigene "
              "Streams archivieren) ist in der Regel unproblematisch, du bist aber für die "
              "Einhaltung der Twitch-Nutzungsbedingungen und des Urheberrechts verantwortlich. "
              "Lade keine fremden Inhalte erneut hoch und nutze sie nicht kommerziell."},
        {"q": "Wie sichere ich ein Twitch-VOD, bevor es gelöscht wird?",
         "a": "Twitch löscht VODs automatisch nach 7–60 Tagen. Lade das VOD jetzt als MP4 "
              "herunter, um eine dauerhafte lokale Kopie in voller Qualität zu behalten."},
        {"q": "Wie nehme ich einen Twitch-Live-Stream auf?",
         "a": "Füge die Kanal-URL ein, während der Streamer live ist, und starte die Aufnahme. "
              "Der Stream wird als MP4 aufgezeichnet, bis die Übertragung endet oder du manuell "
              "stoppst."},
    ],

    "disclaimer": (
        "Nur für den privaten Gebrauch. Du bist für die Einhaltung der Twitch-"
        "Nutzungsbedingungen und des geltenden Urheberrechts verantwortlich. Dieses Tool "
        "greift ausschließlich auf öffentlich verfügbare Inhalte zu und umgeht keine "
        "Paywall und kein DRM."
    ),
    "footer_made": "Open-Source Twitch Downloader · Läuft im Browser · Kein Account, kein Tracking",
    "footer_links": "VODs · Clips · Live-Streams · MP4",

    "nav_blog": "Blog",
    "blog_h1": "Twitch Downloader Blog: Anleitungen & Tipps",
    "blog_sub": "Schritt-für-Schritt-Anleitungen zum Download von Twitch VODs, Clips und Live-Streams.",
    "blog_read": "Anleitung lesen →",
    "blog_back": "← Zurück zum Twitch Downloader",
    "blog_related": "Verwandte Anleitungen",
    "blog_updated": "Aktualisiert",
    "blog_toc": "In dieser Anleitung",
    "blog_cta_h": "Lade dein Twitch-Video jetzt herunter",
    "blog_cta_p": "Twitch-Link einfügen und in Sekunden als MP4 speichern — kostenlos, ohne Account.",
    "blog_cta_btn": "Twitch Downloader öffnen",
    "static_notice": "Dies ist die gehostete Info-Seite. Der Twitch Downloader läuft als kostenlose lokale App auf deinem Rechner — siehe die Anleitungen unten, oder verbinde dein eigenes Backend.",
    "nav_about": "Über",
    "about_h1": "Über Twitch Downloader",
    "about_lead": "Twitch Downloader ist ein kostenloses, quelloffenes Tool, um Twitch VODs, Clips und Live-Streams als MP4 zu sichern — für Streamer, Editoren und Archivare, die ihre Inhalte schnell und privat behalten wollen.",
    "about_sections": [
        {"heading": "Was es macht", "body": "Es lädt vergangene Twitch-Streams, Highlights, Clips und Live-Streams in originaler Source-Qualität (bis 1080p60) als normale MP4-Dateien — ohne Account, ohne Wasserzeichen, ohne Werbung."},
        {"heading": "Wie es funktioniert", "body": "Das Tool liest die öffentlichen Wiedergabedaten von Twitch, holt die HLS-Segmente des Videos (oder die MP4 eines Clips) über einen schlanken Proxy (nötig wegen der Sicherheitsregeln des Browsers) und fügt sie direkt in deinem Browser zu einer einzigen Datei zusammen."},
        {"heading": "Privatsphäre & verantwortungsvolle Nutzung", "body": "Es gibt keinen Account und kein Tracking, und wir speichern deine Downloads nicht — das Video wird nur über einen zustandslosen Proxy weitergeleitet, um Browser-Limits zu umgehen. Nutze es nur für Inhalte, die dir gehören oder die du speichern darfst, und respektiere stets die Twitch-Nutzungsbedingungen und das Urheberrecht."},
    ],
}


# Übersetzungs-Slots: EN/DE handgepflegt, Rest aus dem Übersetzungs-Workflow.
STRINGS: dict[str, dict] = {
    "en": EN,
    "de": DE,
}

try:
    from ._translations import TRANSLATIONS as _AUTO
    for _code, _obj in _AUTO.items():
        STRINGS.setdefault(_code, _obj)
except ImportError:
    pass  # ohne generierte Übersetzungen: EN-Fallback greift


def get_strings(lang: str) -> dict:
    """Hole vollständigen String-Satz für lang; fehlende Keys → EN-Fallback."""
    base = deepcopy(EN)
    data = STRINGS.get(lang)
    if data:
        base.update(data)
    return base


def normalize_lang(raw: Optional[str]) -> str:
    """Map beliebiger Eingabe (z. B. 'de-DE', 'pt') auf einen unterstützten Code."""
    if not raw:
        return DEFAULT_LANG
    r = raw.strip().lower().replace("_", "-")
    if r in LANGUAGES:
        return r
    # pt -> pt-br, zh -> zh-cn
    short = r.split("-")[0]
    aliases = {"pt": "pt-br", "zh": "zh-cn"}
    if short in aliases:
        return aliases[short]
    if short in LANGUAGES:
        return short
    return DEFAULT_LANG


# Weird-but-honest Lade-Mikrotexte (transkreativ je Sprache). Fallback: en.
LOADING_MSGS = {
    "en": ["Politely asking Twitch for the video…", "Reticulating splines…", "Untangling the playlist spaghetti…", "Teaching the segments to hold hands…", "Herding pixels into a single file…", "Applying the final strip of duct tape…", "Convincing your browser this is totally fine…", "Definitely not mining crypto. Pinky promise…", "Doing the thing. The thing is happening…", "Stitching frames while you look cool…", "Negotiating with the CDN…", "Almost there — warming up the download…"],
    "de": ["Frage Twitch ganz höflich nach dem Video…", "Retikuliere Splines…", "Entwirre den Playlist-Spaghetti…", "Bringe den Segmenten Händchenhalten bei…", "Treibe die Pixel in eine Datei…", "Klebe das letzte Stück Panzerband…", "Überzeuge deinen Browser, dass das völlig okay ist…", "Definitiv kein Krypto-Mining. Ehrenwort…", "Mache das Ding. Das Ding passiert gerade…", "Nähe Frames zusammen, während du gut aussiehst…", "Verhandle mit dem CDN…", "Gleich fertig — wärme den Download auf…"],
    "es": ["Pidiéndole el vídeo a Twitch, con educación…", "Reticulando splines…", "Desenredando los espaguetis de la playlist…", "Enseñando a los segmentos a darse la mano…", "Metiendo los píxeles en un solo archivo, a empujones…", "Pegando el último trozo de cinta americana…", "Convenciendo a tu navegador de que esto es de lo más normal…", "Definitivamente no estamos minando cripto. Te lo juro por Snoopy…", "Haciendo la cosa. La cosa ya está pasando…", "Cosiendo fotogramas mientras tú posas como un crack…", "Negociando con la CDN…", "Casi está — calentando motores para la descarga…"],
    "pt-br": ["Pedindo o vídeo pra Twitch com licencinha…", "Reticulando splines…", "Desenrolando o miojo da playlist…", "Ensinando os pedacinhos a dar as mãos…", "Juntando os pixels num arquivo só…", "Passando a última fita isolante…", "Convencendo seu navegador que tá tudo certo…", "Juro que não é mineração de cripto. Pode crer…", "Fazendo a coisa. A coisa tá rolando…", "Costurando os frames enquanto você arrasa…", "Negociando com o CDN no precinho…", "Quase lá — esquentando o download…"],
    "fr": ["On demande la vidéo à Twitch, très poliment…", "Réticulation des splines en cours…", "On démêle le plat de spaghettis de la playlist…", "On apprend aux segments à se tenir la main…", "On rassemble les pixels dans un seul fichier…", "Pose du dernier bout de scotch magique…", "On convainc ton navigateur que tout va bien…", "On ne mine pas de crypto. Parole d'honneur…", "On fait le truc. Le truc est en train de se faire…", "On coud les images pendant que tu fais le beau…", "Petite négociation avec le CDN…", "On y est presque — on chauffe le téléchargement…"],
    "it": ["Chiediamo gentilmente il video a Twitch…", "Reticolazione delle spline in corso…", "Sbrogliamo gli spaghetti della playlist…", "Insegniamo ai segmenti a tenersi per mano…", "Raduniamo i pixel in un unico file…", "Ultimo giro di nastro adesivo…", "Convinciamo il browser che è tutto regolare…", "Giuriamo, niente mining di cripto. Promesso…", "Stiamo facendo la cosa. La cosa sta succedendo…", "Cuciamo i fotogrammi mentre tu fai il figo…", "Trattativa in corso con la CDN…", "Ci siamo quasi — scaldiamo il download…"],
    "nl": ["Twitch netjes om het filmpje vragen…", "Splines aan het reticuleren…", "De afspeellijst-spaghetti ontklitten…", "De segmenten handjes laten vasthouden…", "Pixels één bestand in jagen…", "Het laatste stukje ducttape erop…", "Je browser overtuigen dat dit prima is…", "Echt geen crypto aan het minen. Erewoord…", "Het ding aan het doen. Het ding gebeurt nu…", "Frames aan elkaar naaien terwijl jij cool blijft…", "Aan het onderhandelen met de CDN…", "Bijna klaar — de download even opwarmen…"],
    "pl": ["Grzecznie proszę Twitcha o filmik…", "Retikuluję splajny…", "Rozplątuję makaron z playlisty…", "Uczę segmenty trzymać się za rączki…", "Spędzam piksele do jednego pliku…", "Przyklejam ostatni kawałek taśmy klejącej…", "Przekonuję przeglądarkę, że to spoko…", "Na pewno nie kopię kryptowalut. Słowo harcerza…", "Robię to coś. To coś właśnie się dzieje…", "Zszywam klatki, a ty wyglądasz zajebiście…", "Negocjuję z CDN-em…", "Już prawie — rozgrzewam pobieranie…"],
    "tr": ["Twitch'ten videoyu kibarca rica ediyoruz…", "Spline'lar retikülüze ediliyor…", "Oynatma listesi makarnası çözülüyor…", "Parçalara el ele tutuşmayı öğretiyoruz…", "Pikseller tek dosyaya güdülüyor…", "Son kez koli bandı çekiyoruz…", "Tarayıcına 'her şey yolunda' diye tatlı dille anlatıyoruz…", "Kesinlikle kripto kazmıyoruz. Cidden, söz…", "O şeyi yapıyoruz. Şey oluyor işte…", "Sen havalı dururken kareleri dikiyoruz…", "CDN ile pazarlık ediyoruz, biraz nazlanıyor…", "Az kaldı — indirmeyi ısıtıyoruz…"],
    "ru": ["Вежливо выпрашиваем видео у Twitch…", "Ретикулируем сплайны…", "Распутываем спагетти из плейлиста…", "Учим сегменты держаться за ручки…", "Сгоняем пиксели в один файл…", "Приматываем последний кусочек скотча…", "Убеждаем браузер, что всё путём…", "Точно не майним крипту. Зуб даём…", "Делаем дело. Дело уже делается…", "Сшиваем кадры, пока ты весь такой красивый…", "Договариваемся с CDN по-хорошему…", "Почти готово — прогреваем загрузку…"],
    "ja": ["Twitchに動画をペコリとお願い中…", "スプライン補間してます…", "プレイリストのスパゲッティをほぐし中…", "バラバラの断片に手をつながせ中…", "ピクセルを一つのファイルに集合させ中…", "最後にガムテで補強中…", "ブラウザに「全然平気だよ」と説得中…", "断じて仮想通貨は掘ってません。指切りげんまん…", "例のアレを実行中。アレ、進行中…", "君がキメ顔してる間にフレーム縫合中…", "CDNと交渉中…", "もうすぐ完了――ダウンロードを温め中…"],
    "ko": ["트위치에 영상 좀 달라고 정중히 부탁하는 중…", "스플라인 보정 중… (심시티 감성)", "엉킨 플레이리스트 라면발 푸는 중…", "조각난 영상들 손 꼭 잡혀주는 중…", "흩어진 픽셀들 한 파일로 몰이하는 중…", "마지막으로 박스테이프 쫙 붙이는 중…", "브라우저한테 '이거 완전 정상이야' 설득하는 중…", "절대 코인 채굴 안 함. 새끼손가락 걸고 약속…", "그거 하는 중. 그게 지금 되고 있음…", "그대가 폼 잡는 동안 프레임 꿰매는 중…", "CDN이랑 흥정하는 중…", "거의 다 됐어요 — 다운로드 예열 중…"],
    "zh-cn": ["正在彬彬有礼地向 Twitch 讨视频…", "正在重新拼接样条曲线…", "正在解开播放列表这碗意大利面…", "正在教视频片段手拉手…", "正在把像素一只只赶进文件里…", "正在贴上最后一截万能胶带…", "正在说服你的浏览器：放心，没事…", "绝对没在偷偷挖矿，拉钩上吊…", "正在搞事情，事情正在搞…", "正在缝合每一帧，你只管帅就好…", "正在和 CDN 服务器讨价还价…", "马上好——正在给下载热个身…"],
    "ar": ["نطلب الفيديو من تويتش بكل أدب…", "نُعيد حساب المنحنيات يا لاعبين…", "نفك تشابك المعكرونة المسلسلة…", "نُعلّم المقاطع تمسك أيادي بعضها…", "نسوق البكسلات داخل ملف واحد…", "نلصق آخر شريط لاصق سحري…", "نُقنع متصفحك أنّ كل شيء تمام…", "أكيد لا نُنقّب عملات رقمية… وعد شرف…", "نسوي الحاجة… الحاجة قاعدة تصير…", "نخيط اللقطات وأنت واقف بأناقة…", "نتفاوض مع خوادم التوزيع (CDN)…", "كملنا تقريباً — نُسخّن التحميل…"],
}


def get_loading_msgs(lang: str) -> list:
    return LOADING_MSGS.get(lang) or LOADING_MSGS["en"]
