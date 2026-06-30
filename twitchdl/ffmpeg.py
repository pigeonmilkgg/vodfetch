"""ffmpeg-Anbindung mit sauberem Fallback, falls ffmpeg fehlt."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import FFmpegError

_INSTALL_HINT = (
    "ffmpeg nicht gefunden. Installiere es für MP4-Ausgabe:\n"
    "  macOS:   brew install ffmpeg\n"
    "  Ubuntu:  sudo apt install ffmpeg\n"
    "  Windows: winget install Gyan.FFmpeg  (oder https://ffmpeg.org/download.html)"
)


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def install_hint() -> str:
    return _INSTALL_HINT


def remux_ts_to_mp4(combined_ts: Path, out_mp4: Path) -> Path:
    """Container-Wechsel .ts -> .mp4 ohne Re-Encode (verlustfrei, schnell).

    aac_adtstoasc konvertiert ADTS-AAC (TS) zu MP4-kompatiblem AAC.
    +faststart verschiebt den Moov-Atom nach vorn (sofortiges Streamen/Seeken).
    """
    if not has_ffmpeg():
        raise FFmpegError(_INSTALL_HINT)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(combined_ts),
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_mp4.exists() or out_mp4.stat().st_size == 0:
        raise FFmpegError(f"ffmpeg-Remux fehlgeschlagen:\n{proc.stderr.strip()[:500]}")
    return out_mp4
