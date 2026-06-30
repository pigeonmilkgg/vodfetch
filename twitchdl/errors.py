"""Exception-Hierarchie. Jede dem Nutzer gezeigte Fehlermeldung ist handlungsleitend."""
from __future__ import annotations


class TwitchDLError(Exception):
    """Basisklasse aller erwarteten Fehler. Wird in CLI/Web sauber abgefangen."""


class InvalidURLError(TwitchDLError):
    """Eingabe konnte nicht als VOD/Clip/Channel interpretiert werden."""


class NotFoundError(TwitchDLError):
    """Inhalt existiert nicht, ist gelöscht, offline oder geografisch gesperrt."""


class AccessError(TwitchDLError):
    """Token-/Signatur-Problem oder Sub-only/privat (kein öffentlicher Zugriff)."""


class PlaylistError(TwitchDLError):
    """HLS-Master-/Media-Playlist fehlerhaft oder leer."""


class DownloadError(TwitchDLError):
    """Segment(e) konnten trotz Retries nicht geladen werden."""


class FFmpegError(TwitchDLError):
    """ffmpeg-Aufruf fehlgeschlagen."""
