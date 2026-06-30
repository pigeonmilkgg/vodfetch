"""HLS (m3u8) Parsing: Master-Playlist → Qualitäten, Media-Playlist → Segmente.

Bewusst ohne externe m3u8-Library: schlanker, kontrollierbarer, weniger Angriffsfläche.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from .errors import PlaylistError
from .models import Quality, Segment

_ATTR_RE = re.compile(r'([A-Z0-9-]+)=("([^"]*)"|[^,]*)')


def _parse_attrs(line: str) -> dict:
    """Parse 'KEY=VALUE,KEY="quoted value"' Attributlisten."""
    out: dict = {}
    for m in _ATTR_RE.finditer(line):
        key = m.group(1)
        val = m.group(3) if m.group(3) is not None else m.group(2)
        out[key] = val
    return out


def parse_master(text: str, base_url: str) -> list[Quality]:
    """Parse eine HLS-Master-Playlist zu einer Liste von Quality-Objekten."""
    if "#EXTM3U" not in text:
        raise PlaylistError("Antwort ist keine gültige HLS-Playlist.")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    qualities: list[Quality] = []
    pending_media: dict = {}          # zuletzt gesehene #EXT-X-MEDIA Attrs (NAME etc.)
    pending_stream: dict = {}         # zuletzt gesehene #EXT-X-STREAM-INF Attrs

    for line in lines:
        if line.startswith("#EXT-X-MEDIA:"):
            pending_media = _parse_attrs(line[len("#EXT-X-MEDIA:"):])
        elif line.startswith("#EXT-X-STREAM-INF:"):
            pending_stream = _parse_attrs(line[len("#EXT-X-STREAM-INF:"):])
        elif not line.startswith("#"):
            # URL-Zeile: gehört zum vorhergehenden STREAM-INF
            url = urljoin(base_url, line)
            name = (
                pending_media.get("NAME")
                or pending_stream.get("VIDEO")
                or pending_stream.get("GROUP-ID")
                or "unknown"
            )
            group_id = pending_media.get("GROUP-ID") or pending_stream.get("VIDEO")
            resolution = pending_stream.get("RESOLUTION")
            bandwidth = _to_int(pending_stream.get("BANDWIDTH"))
            fps = _to_float(pending_stream.get("FRAME-RATE"))
            is_source = (group_id == "chunked") or ("source" in name.lower()) or ("chunked" in name.lower())

            # Schöneres Label für Source
            display = name
            if is_source and resolution:
                h = resolution.split("x")[-1]
                fps_part = f"{int(fps)}" if fps else ""
                display = f"{h}p{fps_part} (source)"

            qualities.append(Quality(
                name=display,
                url=url,
                resolution=resolution,
                fps=fps,
                bandwidth=bandwidth,
                group_id=group_id,
                is_source=is_source,
            ))
            pending_media = {}
            pending_stream = {}

    if not qualities:
        raise PlaylistError("Master-Playlist enthielt keine Qualitäten.")
    # höchste zuerst
    qualities.sort(key=lambda q: (q.is_source, q.height, q.bandwidth or 0), reverse=True)
    return qualities


def parse_media(text: str, base_url: str, start_index: int = 0) -> tuple[list[Segment], bool, float]:
    """Parse eine HLS-Media-Playlist.

    Returns (segments, ended, target_duration).
        segments: ab start_index nummeriert (für Live-Inkrement)
        ended:    True wenn #EXT-X-ENDLIST vorhanden (VOD / finished)
        target_duration: #EXT-X-TARGETDURATION (Poll-Intervall für Live)
    """
    if "#EXTM3U" not in text:
        raise PlaylistError("Media-Playlist ungültig (kein #EXTM3U).")

    segments: list[Segment] = []
    ended = False
    target_duration = 0.0
    cur_duration = 0.0
    idx = start_index

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-ENDLIST"):
            ended = True
        elif line.startswith("#EXT-X-TARGETDURATION:"):
            target_duration = _to_float(line.split(":", 1)[1]) or 0.0
        elif line.startswith("#EXTINF:"):
            cur_duration = _to_float(line[len("#EXTINF:"):].split(",")[0]) or 0.0
        elif line.startswith("#"):
            continue  # andere Tags ignorieren (Discontinuity, Map, etc.)
        else:
            url = urljoin(base_url, line)
            muted = "-muted" in line.lower() or "muted=true" in line.lower()
            segments.append(Segment(index=idx, url=url, duration=cur_duration, muted=muted))
            idx += 1
            cur_duration = 0.0

    return segments, ended, target_duration


def base_of(url: str) -> str:
    """URL ohne Dateinamen (für relative Segment-Auflösung)."""
    return url.rsplit("/", 1)[0] + "/"


def _to_int(v) -> "int | None":
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _to_float(v) -> "float | None":
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None
