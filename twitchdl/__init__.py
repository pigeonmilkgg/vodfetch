"""twitchdl — robuster Downloader für Twitch VODs, Clips und Live-Streams.

Öffentliche API:
    from twitchdl import Downloader, parse_input
"""
from __future__ import annotations

from .core import Downloader
from .parser import parse_input
from .models import MediaRef, Quality, MediaInfo, ProgressEvent
from .errors import (
    TwitchDLError,
    InvalidURLError,
    NotFoundError,
    AccessError,
    PlaylistError,
    DownloadError,
    FFmpegError,
)

__version__ = "1.0.0"

__all__ = [
    "Downloader",
    "parse_input",
    "MediaRef",
    "Quality",
    "MediaInfo",
    "ProgressEvent",
    "TwitchDLError",
    "InvalidURLError",
    "NotFoundError",
    "AccessError",
    "PlaylistError",
    "DownloadError",
    "FFmpegError",
    "__version__",
]
