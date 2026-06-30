"""Kommandozeilen-Frontend."""
from __future__ import annotations

import argparse
import sys
import threading
import time

from .core import Downloader
from .errors import TwitchDLError
from .models import ProgressEvent
from .parser import parse_input


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_time(s) -> str:
    if s is None:
        return "??:??"
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


class _CliProgress:
    """Rendert ProgressEvents als Terminal-Balken (eine Zeile, mit \\r)."""
    def __init__(self) -> None:
        self._last_phase = ""
        self._last_len = 0

    def __call__(self, ev: ProgressEvent) -> None:
        if ev.phase in ("resolving", "playlist", "muxing") and ev.message:
            self._line_break()
            print(f"  → {ev.message}")
            return
        if ev.phase == "downloading":
            pct = ev.percent
            speed = _fmt_bytes(ev.speed_bps) + "/s" if ev.speed_bps else ""
            if pct is not None:
                bar_len = 28
                filled = int(bar_len * pct / 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                count = "" if ev.unit == "bytes" else f"{ev.current}/{ev.total}  "
                line = (f"  [{bar}] {pct:5.1f}%  {count}"
                        f"{_fmt_bytes(ev.bytes_done)}  {speed}  ETA {_fmt_time(ev.eta_seconds)}")
            else:  # Live (unbekannte Gesamtlänge)
                line = f"  ● LIVE  {ev.current} Segmente  {_fmt_bytes(ev.bytes_done)}  {speed}"
            self._write(line)
        elif ev.phase == "done":
            self._line_break()
            print(f"  ✓ {ev.message}")
            if ev.output_path:
                print(f"  📁 {ev.output_path}")
        elif ev.phase == "error":
            self._line_break()
            print(f"  ✗ {ev.message}", file=sys.stderr)

    def _write(self, line: str) -> None:
        pad = " " * max(0, self._last_len - len(line))
        sys.stdout.write("\r" + line + pad)
        sys.stdout.flush()
        self._last_len = len(line)

    def _line_break(self) -> None:
        if self._last_len:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._last_len = 0


def _print_info(info) -> None:
    print(f"\n  Titel : {info.title}")
    if info.author:
        print(f"  Kanal : {info.author}")
    if info.duration_seconds:
        print(f"  Länge : {_fmt_time(info.duration_seconds)}")
    print(f"  Typ   : {info.ref.kind}  (ID/Slug: {info.ref.id})")
    print("\n  Verfügbare Qualitäten:")
    for q in info.qualities:
        tag = "  ★" if q.is_source else "   "
        print(f"  {tag} {q.label()}")
    print()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="twitchdl",
        description="Twitch VOD / Clip / Live Downloader.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  twitchdl info  https://twitch.tv/videos/123456789\n"
            "  twitchdl get   https://twitch.tv/videos/123456789 -q best -o ~/Downloads\n"
            "  twitchdl get   https://clips.twitch.tv/SlugHier\n"
            "  twitchdl get   https://twitch.tv/somechannel   (Live aufnehmen, Strg+C zum Stoppen)\n"
            "  twitchdl web   --port 8765\n"
        ),
    )
    p.add_argument("--workers", type=int, default=10, help="parallele Segment-Downloads (Default 10)")
    p.add_argument("--retries", type=int, default=5, help="Versuche pro Segment (Default 5)")
    p.add_argument("--no-mp4", action="store_true", help="kein ffmpeg-Remux, .ts behalten")

    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("info", help="Qualitäten anzeigen (kein Download)")
    pi.add_argument("url", help="Twitch-URL oder ID/Slug")

    pg = sub.add_parser("get", help="Download (Typ wird automatisch erkannt)")
    pg.add_argument("url", help="Twitch-URL oder ID/Slug")
    pg.add_argument("-q", "--quality", default="best", help="best|worst|audio|1080p60|720p … (Default best)")
    pg.add_argument("-o", "--output", default=".", help="Zielordner (Default .)")
    pg.add_argument("-f", "--filename", default=None, help="Dateiname (ohne Endung)")
    pg.add_argument("--try-unmute", action="store_true", help="gemutete VOD-Segmente wiederherstellen versuchen")

    pw = sub.add_parser("web", help="lokale Web-Oberfläche starten")
    pw.add_argument("--host", default="127.0.0.1")
    pw.add_argument("--port", type=int, default=8765)
    pw.add_argument("--no-browser", action="store_true", help="Browser nicht automatisch öffnen")

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "web":
        from .webapp import run_web
        return run_web(host=args.host, port=args.port, open_browser=not args.no_browser,
                       workers=args.workers, retries=args.retries, prefer_mp4=not args.no_mp4)

    progress = _CliProgress()
    dl = Downloader(workers=args.workers, retries=args.retries,
                    progress_cb=progress, prefer_mp4=not args.no_mp4)

    try:
        if args.command == "info":
            info = dl.info(args.url)
            _print_info(info)
            return 0

        if args.command == "get":
            ref = parse_input(args.url)
            t0 = time.monotonic()
            if ref.kind == "channel":
                # Live: in Worker-Thread; Strg+C im Hauptthread setzt stop_event,
                # damit bereits aufgenommene Segmente sauber finalisiert werden.
                print("  ● Live-Aufnahme — Strg+C zum sauberen Beenden.\n")
                stop_event = threading.Event()
                result: dict = {}

                def _runner() -> None:
                    try:
                        result["out"] = dl.download(
                            ref, quality=args.quality, output_dir=args.output,
                            filename=args.filename, stop_event=stop_event)
                    except Exception as exc:  # an Hauptthread durchreichen
                        result["err"] = exc

                th = threading.Thread(target=_runner, daemon=True)
                th.start()
                try:
                    while th.is_alive():
                        th.join(timeout=0.3)
                except KeyboardInterrupt:
                    print("\n  ⏹  Stoppe Aufnahme, finalisiere …")
                    stop_event.set()
                    th.join()
                if "err" in result:
                    raise result["err"]
            else:
                dl.download(ref, quality=args.quality, output_dir=args.output,
                            filename=args.filename, try_unmute=args.try_unmute)
            print(f"\n  Gesamtdauer: {_fmt_time(time.monotonic() - t0)}")
            return 0
    except KeyboardInterrupt:
        print("\n  Abgebrochen.", file=sys.stderr)
        return 130
    except TwitchDLError as e:
        print(f"\n  ✗ Fehler: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # unerwartet — defensiv abfangen
        print(f"\n  ✗ Unerwarteter Fehler: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
