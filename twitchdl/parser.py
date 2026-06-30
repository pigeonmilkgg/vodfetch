"""URL-/ID-Parsing → MediaRef. Netzfrei und vollständig unit-getestet."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .errors import InvalidURLError
from .models import MediaRef, KIND_VOD, KIND_CLIP, KIND_CHANNEL

# VOD-ID = reine Ziffern (optional 'v'-Präfix in alten Links)
_VOD_ID = re.compile(r"^v?(\d{6,})$")
# Clip-Slug: Twitch-Slugs sind alphanumerisch + Bindestriche, meist gemischt.
_CLIP_SLUG = re.compile(r"^[A-Za-z0-9-_]{6,}$")
# Channel-Login: 3-25 Zeichen, alphanumerisch + Unterstrich.
_CHANNEL = re.compile(r"^[A-Za-z0-9_]{2,25}$")

_TWITCH_HOSTS = {
    "twitch.tv", "www.twitch.tv", "m.twitch.tv",
    "clips.twitch.tv", "www.clips.twitch.tv",
    "player.twitch.tv",
}

# Reservierte Pfadnamen, die KEINE Channel-Logins sind.
_RESERVED = {
    "videos", "directory", "settings", "downloads", "subscriptions",
    "drops", "wallet", "p", "search", "store", "prime",
}


def parse_input(raw: str) -> MediaRef:
    """Erkenne VOD, Clip oder Channel (Live) aus URL oder roher ID.

    Beispiele:
        twitch.tv/videos/123456789      -> vod 123456789
        clips.twitch.tv/AwkwardHelpfulFoo -> clip AwkwardHelpfulFoo
        twitch.tv/shroud/clip/Foo-Bar   -> clip Foo-Bar
        twitch.tv/shroud                -> channel shroud
        123456789                       -> vod 123456789
    """
    if not raw or not raw.strip():
        raise InvalidURLError("Leere Eingabe.")
    s = raw.strip()

    # --- Rohe ID/Slug (keine URL) ---------------------------------------
    if "/" not in s and "." not in s and " " not in s:
        m = _VOD_ID.match(s)
        if m:
            return MediaRef(KIND_VOD, m.group(1), s)
        # Mehrdeutig: könnte Channel ODER Clip-Slug sein. Heuristik:
        # echte Clip-Slugs sind i.d.R. lang & gemischt; Channels kurz/klein.
        if _CHANNEL.match(s) and len(s) <= 25 and "-" not in s:
            return MediaRef(KIND_CHANNEL, s.lower(), s)
        if _CLIP_SLUG.match(s):
            return MediaRef(KIND_CLIP, s, s)
        raise InvalidURLError(f"'{raw}' ist weder eine gültige ID noch eine URL.")

    # --- URL-Normalisierung --------------------------------------------
    candidate = s if "://" in s else "https://" + s
    parsed = urlparse(candidate)
    host = (parsed.netloc or "").lower().split("@")[-1].split(":")[0]
    if host and host not in _TWITCH_HOSTS and not host.endswith(".twitch.tv"):
        raise InvalidURLError(f"Kein Twitch-Host: '{host}'.")

    parts = [p for p in (parsed.path or "").split("/") if p]

    # clips.twitch.tv/<slug>
    if host.startswith("clips.") and parts:
        return MediaRef(KIND_CLIP, parts[0], s)

    # player.twitch.tv/?video=v123 oder ?channel=foo
    if host.startswith("player."):
        from urllib.parse import parse_qs
        q = parse_qs(parsed.query or "")
        if "video" in q:
            vid = q["video"][0].lstrip("v")
            return MediaRef(KIND_VOD, vid, s)
        if "channel" in q:
            return MediaRef(KIND_CHANNEL, q["channel"][0].lower(), s)

    # /videos/<id>
    if len(parts) >= 2 and parts[0] == "videos":
        m = _VOD_ID.match(parts[1])
        if m:
            return MediaRef(KIND_VOD, m.group(1), s)
        raise InvalidURLError(f"Ungültige VOD-ID in URL: '{parts[1]}'.")

    # /<channel>/clip/<slug>  oder  /<channel>/clips/<slug>
    if len(parts) >= 3 and parts[1] in ("clip", "clips"):
        return MediaRef(KIND_CLIP, parts[2], s)

    # /<channel>  (Live)
    if len(parts) >= 1 and parts[0].lower() not in _RESERVED:
        if _CHANNEL.match(parts[0]):
            return MediaRef(KIND_CHANNEL, parts[0].lower(), s)

    raise InvalidURLError(f"Konnte aus '{raw}' keinen Twitch-Inhalt ableiten.")


def sanitize_filename(name: str, max_len: int = 150) -> str:
    """Mache einen String dateisystemsicher."""
    name = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "_", name).strip().strip(".")
    name = re.sub(r"\s+", " ", name)
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "twitch_download"
