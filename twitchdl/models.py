"""Reine Datencontainer (keine Logik)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Inhaltstypen
KIND_VOD = "vod"
KIND_CLIP = "clip"
KIND_CHANNEL = "channel"  # = Live


@dataclass(frozen=True)
class MediaRef:
    """Ergebnis des URL/ID-Parsings."""
    kind: str          # KIND_VOD | KIND_CLIP | KIND_CHANNEL
    id: str            # VOD-ID, Clip-Slug oder Channel-Login
    source: str = ""   # ursprüngliche Eingabe (für Fehlermeldungen)


@dataclass
class Quality:
    """Eine verfügbare Qualitätsvariante aus der HLS-Master-Playlist oder Clip-API."""
    name: str                       # z.B. "1080p60", "720p", "audio_only", "chunked"
    url: str                        # Media-Playlist-URL (VOD/Live) oder MP4-URL (Clip)
    resolution: Optional[str] = None    # "1920x1080" oder None (audio)
    fps: Optional[float] = None
    bandwidth: Optional[int] = None     # bit/s
    group_id: Optional[str] = None      # HLS GROUP-ID
    is_source: bool = False             # "chunked"/Source-Variante

    @property
    def height(self) -> int:
        """Vertikale Auflösung zur Sortierung; 0 für audio_only."""
        if not self.resolution or "x" not in self.resolution:
            return 0
        try:
            return int(self.resolution.split("x")[1])
        except (ValueError, IndexError):
            return 0

    def label(self) -> str:
        bits = [self.name]
        if self.resolution:
            bits.append(self.resolution)
        if self.bandwidth:
            bits.append(f"{self.bandwidth / 1_000_000:.1f} Mbit/s")
        return " · ".join(bits)


@dataclass
class MediaInfo:
    """Vollständige, abrufbereite Beschreibung eines Inhalts."""
    ref: MediaRef
    title: str
    author: str = ""
    duration_seconds: Optional[int] = None
    qualities: list[Quality] = field(default_factory=list)

    def best(self) -> Quality:
        """Höchste verfügbare Qualität (Source bevorzugt, sonst max. Bandbreite/Höhe)."""
        if not self.qualities:
            raise ValueError("Keine Qualitäten verfügbar")
        srcs = [q for q in self.qualities if q.is_source]
        pool = srcs or self.qualities
        return max(pool, key=lambda q: (q.height, q.bandwidth or 0))

    def worst(self) -> Quality:
        # niedrigste Video-Qualität; audio_only (height 0) nur falls nichts anderes da ist
        vids = [q for q in self.qualities if q.height > 0]
        pool = vids or self.qualities
        return min(pool, key=lambda q: (q.height, q.bandwidth or 0))

    def audio_only(self) -> Optional[Quality]:
        for q in self.qualities:
            if "audio" in q.name.lower() or q.height == 0:
                return q
        return None

    def select(self, choice: str) -> Quality:
        """choice: 'best' | 'worst' | 'audio' | exakter Name (z.B. '720p60')."""
        choice = (choice or "best").strip().lower()
        if choice in ("best", "source", "chunked"):
            return self.best()
        if choice == "worst":
            return self.worst()
        if choice in ("audio", "audio_only"):
            a = self.audio_only()
            if a:
                return a
            return self.worst()
        # exakter / teilweiser Name-Match
        for q in self.qualities:
            if q.name.lower() == choice:
                return q
        for q in self.qualities:
            if choice in q.name.lower():
                return q
        avail = ", ".join(q.name for q in self.qualities)
        raise ValueError(f"Qualität '{choice}' nicht verfügbar. Verfügbar: {avail}")


@dataclass
class Segment:
    """Ein HLS-Segment."""
    index: int
    url: str
    duration: float = 0.0
    muted: bool = False


@dataclass
class ProgressEvent:
    """Einheitliches Fortschritts-Ereignis für CLI & Web."""
    phase: str                       # "resolving"|"playlist"|"downloading"|"muxing"|"done"|"error"
    message: str = ""
    current: int = 0                 # erledigte Einheiten (Segmente oder Bytes — s. unit)
    total: int = 0                   # Gesamteinheiten (0 = unbekannt, z.B. Live)
    unit: str = "segments"           # "segments" | "bytes"
    bytes_done: int = 0
    speed_bps: float = 0.0           # Bytes/s
    eta_seconds: Optional[float] = None
    output_path: Optional[str] = None

    @property
    def percent(self) -> Optional[float]:
        if self.total > 0:
            return min(100.0, self.current / self.total * 100.0)
        return None

    def as_dict(self) -> dict:
        return {
            "phase": self.phase,
            "message": self.message,
            "current": self.current,
            "total": self.total,
            "unit": self.unit,
            "percent": self.percent,
            "bytes_done": self.bytes_done,
            "speed_bps": self.speed_bps,
            "eta_seconds": self.eta_seconds,
            "output_path": self.output_path,
        }
