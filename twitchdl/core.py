"""Downloader-Engine: orchestriert Token → Playlist → Segmente → Muxing.

Eine Instanz ist über CLI und Web-UI gemeinsam nutzbar. Fortschritt wird über
ein optionales Callback (progress_cb) gemeldet — das einzige Bindeglied zu den Frontends.
"""
from __future__ import annotations

import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

import requests

from . import hls
from .errors import (
    DownloadError,
    NotFoundError,
    PlaylistError,
    TwitchDLError,
)
from .ffmpeg import has_ffmpeg, install_hint, remux_ts_to_mp4
from .gql import AccessToken, TwitchGQL
from .models import (
    KIND_CHANNEL,
    KIND_CLIP,
    KIND_VOD,
    MediaInfo,
    MediaRef,
    ProgressEvent,
    Quality,
    Segment,
)
from .parser import parse_input, sanitize_filename

USHER_VOD = "https://usher.ttvnw.net/vod/{vod_id}.m3u8"
USHER_LIVE = "https://usher.ttvnw.net/api/channel/hls/{channel}.m3u8"

ProgressCallback = Callable[[ProgressEvent], None]


class Downloader:
    def __init__(
        self,
        workers: int = 10,
        retries: int = 5,
        timeout: float = 20.0,
        progress_cb: Optional[ProgressCallback] = None,
        prefer_mp4: bool = True,
    ) -> None:
        self.workers = max(1, workers)
        self.retries = max(1, retries)
        self.timeout = timeout
        self.progress_cb = progress_cb
        self.prefer_mp4 = prefer_mp4
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
        })
        self.gql = TwitchGQL(session=requests.Session(), timeout=timeout)

    # ------------------------------------------------------------------ #
    # Fortschritt
    # ------------------------------------------------------------------ #
    def _emit(self, event: ProgressEvent) -> None:
        if self.progress_cb:
            try:
                self.progress_cb(event)
            except Exception:
                pass  # ein kaputtes UI darf den Download nie abbrechen

    # ------------------------------------------------------------------ #
    # Öffentlich: Info
    # ------------------------------------------------------------------ #
    def info(self, source) -> MediaInfo:
        """Hole Metadaten + verfügbare Qualitäten OHNE Download."""
        ref = source if isinstance(source, MediaRef) else parse_input(str(source))
        self._emit(ProgressEvent("resolving", f"Analysiere {ref.kind} '{ref.id}' …"))
        if ref.kind == KIND_VOD:
            return self._info_vod(ref)
        if ref.kind == KIND_CLIP:
            return self._info_clip(ref)
        if ref.kind == KIND_CHANNEL:
            return self._info_live(ref)
        raise TwitchDLError(f"Unbekannter Inhaltstyp: {ref.kind}")

    def _info_vod(self, ref: MediaRef) -> MediaInfo:
        token = self.gql.playback_access_token(vod_id=ref.id)
        master = self._fetch_master(USHER_VOD.format(vod_id=ref.id), token)
        qualities = hls.parse_master(master, USHER_VOD.format(vod_id=ref.id))
        meta = self.gql.video_metadata(ref.id)
        return MediaInfo(
            ref=ref,
            title=meta.get("title") or f"vod_{ref.id}",
            author=(meta.get("owner") or {}).get("displayName", ""),
            duration_seconds=meta.get("lengthSeconds"),
            qualities=qualities,
        )

    def _info_live(self, ref: MediaRef) -> MediaInfo:
        token = self.gql.playback_access_token(channel=ref.id)
        master = self._fetch_master(USHER_LIVE.format(channel=ref.id), token, live=True)
        qualities = hls.parse_master(master, USHER_LIVE.format(channel=ref.id))
        return MediaInfo(ref=ref, title=f"{ref.id}_live", author=ref.id, qualities=qualities)

    def _info_clip(self, ref: MediaRef) -> MediaInfo:
        clip = self.gql.clip(ref.id)
        sig = clip["playbackAccessToken"]["signature"]
        val = clip["playbackAccessToken"]["value"]
        qualities: list[Quality] = []
        for q in clip.get("videoQualities", []):
            src = q.get("sourceURL")
            if not src:
                continue
            url = f"{src}?sig={sig}&token={quote(val)}"
            qname = q.get("quality", "?")
            fps = q.get("frameRate")
            label = f"{qname}p{int(fps)}" if fps and float(fps) > 0 else f"{qname}p"
            qualities.append(Quality(
                name=label,
                url=url,
                resolution=f"?x{qname}" if str(qname).isdigit() else None,
                fps=float(fps) if fps else None,
                is_source=False,
            ))
        # höchste Auflösung zuerst
        qualities.sort(key=lambda q: (_int(q.name), q.fps or 0), reverse=True)
        if qualities:
            qualities[0].is_source = True
        b = clip.get("broadcaster") or {}
        return MediaInfo(
            ref=ref,
            title=clip.get("title") or f"clip_{ref.id}",
            author=b.get("displayName", ""),
            duration_seconds=clip.get("durationSeconds"),
            qualities=qualities,
        )

    # ------------------------------------------------------------------ #
    # Öffentlich: Download (Auto-Dispatch)
    # ------------------------------------------------------------------ #
    def download(
        self,
        source,
        quality: str = "best",
        output_dir: str = ".",
        filename: Optional[str] = None,
        try_unmute: bool = False,
        stop_event: Optional[threading.Event] = None,
    ) -> Path:
        ref = source if isinstance(source, MediaRef) else parse_input(str(source))
        if ref.kind == KIND_VOD:
            return self.download_vod(ref, quality, output_dir, filename, try_unmute)
        if ref.kind == KIND_CLIP:
            return self.download_clip(ref, quality, output_dir, filename)
        if ref.kind == KIND_CHANNEL:
            return self.record_live(ref, quality, output_dir, filename, stop_event)
        raise TwitchDLError(f"Unbekannter Inhaltstyp: {ref.kind}")

    # ------------------------------------------------------------------ #
    # VOD
    # ------------------------------------------------------------------ #
    def download_vod(self, ref, quality="best", output_dir=".", filename=None, try_unmute=False) -> Path:
        ref = _as_ref(ref, KIND_VOD)
        info = self._info_vod(ref)
        q = info.select(quality)
        self._emit(ProgressEvent("playlist", f"Wähle Qualität: {q.label()}"))

        media_text = self._get(q.url)
        segments, ended, _ = hls.parse_media(media_text, hls.base_of(q.url))
        if not segments:
            raise PlaylistError("VOD-Playlist enthielt keine Segmente.")

        out_base = self._output_base(output_dir, filename, info, q)
        cache = self._cache_dir(output_dir, ref, q.name)
        files = self._download_segments(segments, cache, try_unmute=try_unmute)
        return self._finalize(files, cache, out_base)

    # ------------------------------------------------------------------ #
    # Clip (direkter MP4-Download)
    # ------------------------------------------------------------------ #
    def download_clip(self, ref, quality="best", output_dir=".", filename=None) -> Path:
        ref = _as_ref(ref, KIND_CLIP)
        info = self._info_clip(ref)
        q = info.select(quality)
        out_base = self._output_base(output_dir, filename, info, q)
        out = out_base.with_suffix(".mp4")
        self._emit(ProgressEvent("downloading", f"Lade Clip ({q.label()}) …", total=1))

        tmp = out.with_suffix(".mp4.part")
        bytes_done = self._stream_clip(q.url, tmp)
        tmp.replace(out)
        self._emit(ProgressEvent("done", "Clip fertig.", current=1, total=1,
                                 bytes_done=bytes_done, output_path=str(out)))
        return out

    def _stream_clip(self, url: str, path: Path) -> int:
        """Clip-Streaming mit Byte-Fortschritt (nutzt Content-Length wenn vorhanden)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        try:
            with self.session.get(url, stream=True, timeout=self.timeout) as r:
                if r.status_code != 200:
                    raise TwitchDLError(f"HTTP {r.status_code} beim Clip-Download.")
                total = int(r.headers.get("Content-Length") or 0)
                size = 0
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        if not chunk:
                            continue
                        f.write(chunk)
                        size += len(chunk)
                        elapsed = max(time.monotonic() - start, 1e-6)
                        pct_total = total if total else 0
                        self._emit(ProgressEvent(
                            "downloading", "", current=size, total=pct_total,
                            unit="bytes", bytes_done=size, speed_bps=size / elapsed,
                            eta_seconds=((total - size) / (size / elapsed)) if total and size else None,
                        ))
            if size == 0:
                raise TwitchDLError("Clip-Download lieferte 0 Bytes.")
            return size
        except requests.RequestException as e:
            raise TwitchDLError(f"Netzwerkfehler beim Clip-Download: {e}") from e

    # ------------------------------------------------------------------ #
    # Live-Recording
    # ------------------------------------------------------------------ #
    def record_live(self, ref, quality="best", output_dir=".", filename=None,
                    stop_event: Optional[threading.Event] = None) -> Path:
        ref = _as_ref(ref, KIND_CHANNEL)
        info = self._info_live(ref)
        q = info.select(quality)
        out_base = self._output_base(output_dir, filename, info, q)
        cache = self._cache_dir(output_dir, ref, q.name)
        stop_event = stop_event or threading.Event()

        self._emit(ProgressEvent("downloading", f"Nehme Live-Stream auf: {ref.id} ({q.label()}) — Stopp zum Beenden."))
        seen: set[str] = set()
        index = 0
        files: list[Path] = []
        start = time.monotonic()
        bytes_done = 0

        while not stop_event.is_set():
            try:
                media_text = self._get(q.url)
            except TwitchDLError:
                # Playlist kurzfristig nicht erreichbar → kurz warten, weiter
                if stop_event.wait(2.0):
                    break
                continue
            new_segs, ended, target = hls.parse_media(media_text, hls.base_of(q.url))
            fresh: list[Segment] = []
            for s in new_segs:
                key = s.url.rsplit("/", 1)[-1].split("?")[0]
                if key in seen:
                    continue
                seen.add(key)
                s.index = index
                index += 1
                fresh.append(s)

            for s in fresh:
                path = cache / f"seg_{s.index:06d}.ts"
                try:
                    bytes_done += self._stream_to_file(s.url, path)
                    files.append(path)
                except TwitchDLError:
                    continue  # Live: einzelnes Segment verloren → tolerieren
                elapsed = max(time.monotonic() - start, 1e-6)
                self._emit(ProgressEvent(
                    "downloading",
                    f"Aufnahme läuft … {len(files)} Segmente",
                    current=len(files), total=0,
                    bytes_done=bytes_done, speed_bps=bytes_done / elapsed,
                ))

            if ended:
                self._emit(ProgressEvent("downloading", "Stream beendet (ENDLIST)."))
                break
            wait = target if target and target > 0 else 2.0
            if stop_event.wait(wait):
                break

        if not files:
            raise DownloadError("Keine Segmente aufgenommen (Stream offline oder sofort gestoppt).")
        return self._finalize(files, cache, out_base)

    # ------------------------------------------------------------------ #
    # Segment-Download (parallel, mit Retry)
    # ------------------------------------------------------------------ #
    def _download_segments(self, segments: list[Segment], cache: Path, try_unmute: bool = False) -> list[Path]:
        total = len(segments)
        cache.mkdir(parents=True, exist_ok=True)
        results: dict[int, Path] = {}
        bytes_done = 0
        done = 0
        start = time.monotonic()
        lock = threading.Lock()

        def work(seg: Segment) -> tuple[int, Path, int]:
            path = cache / f"seg_{seg.index:06d}.ts"
            if path.exists() and path.stat().st_size > 0:   # Resume
                return seg.index, path, path.stat().st_size
            url = seg.url
            if try_unmute and seg.muted:
                url = self._maybe_unmute(seg.url)
            size = self._download_with_retry(url, path, fallback_url=seg.url if url != seg.url else None)
            return seg.index, path, size

        self._emit(ProgressEvent("downloading", f"Lade {total} Segmente mit {self.workers} Workern …", total=total))
        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                futures = [pool.submit(work, s) for s in segments]
                for fut in as_completed(futures):
                    idx, path, size = fut.result()  # wirft DownloadError bei endgültigem Fehler
                    with lock:
                        results[idx] = path
                        bytes_done += size
                        done += 1
                        elapsed = max(time.monotonic() - start, 1e-6)
                        speed = bytes_done / elapsed
                        remaining = (total - done) * (elapsed / done) if done else None
                    self._emit(ProgressEvent(
                        "downloading", f"Segment {done}/{total}",
                        current=done, total=total, bytes_done=bytes_done,
                        speed_bps=speed, eta_seconds=remaining,
                    ))
        except DownloadError:
            raise
        # in Reihenfolge zurückgeben
        return [results[i] for i in sorted(results)]

    def _download_with_retry(self, url: str, path: Path, fallback_url: Optional[str] = None) -> int:
        last_err: Optional[Exception] = None
        for attempt in range(self.retries):
            try:
                return self._stream_to_file(url, path)
            except TwitchDLError as e:
                last_err = e
                # Unmute-Versuch fehlgeschlagen → einmal auf Original zurückfallen
                if fallback_url and attempt == 0:
                    url = fallback_url
                    fallback_url = None
                    continue
                time.sleep(min(2 ** attempt, 30) + random.random())
        raise DownloadError(f"Segment endgültig fehlgeschlagen ({path.name}): {last_err}")

    def _stream_to_file(self, url: str, path: Path) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        try:
            with self.session.get(url, stream=True, timeout=self.timeout) as r:
                if r.status_code == 404:
                    raise NotFoundError(f"404 für {url}")
                if r.status_code != 200:
                    raise TwitchDLError(f"HTTP {r.status_code} für {url}")
                size = 0
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        if chunk:
                            f.write(chunk)
                            size += len(chunk)
            if size == 0:
                raise TwitchDLError(f"Leere Antwort für {url}")
            tmp.replace(path)
            return size
        except requests.RequestException as e:
            raise TwitchDLError(f"Netzwerkfehler: {e}") from e
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    @staticmethod
    def _maybe_unmute(url: str) -> str:
        """Recovery-Versuch: gemutete Segmentnamen auf Original zurückführen."""
        return url.replace("-muted", "").replace("-unmuted", "")

    # ------------------------------------------------------------------ #
    # Finalisierung: Segmente → eine Datei
    # ------------------------------------------------------------------ #
    def _finalize(self, files: list[Path], cache: Path, out_base: Path) -> Path:
        if not files:
            raise DownloadError("Keine Segmente zum Zusammenfügen.")
        combined = cache / "combined.ts"
        self._emit(ProgressEvent("muxing", "Füge Segmente zusammen …"))
        with open(combined, "wb") as out:
            for fp in files:
                with open(fp, "rb") as seg:
                    shutil.copyfileobj(seg, out, length=1 << 20)

        if self.prefer_mp4 and has_ffmpeg():
            out_mp4 = out_base.with_suffix(".mp4")
            self._emit(ProgressEvent("muxing", "Remuxe nach MP4 (ffmpeg) …"))
            remux_ts_to_mp4(combined, out_mp4)
            self._cleanup(cache)
            self._emit(ProgressEvent("done", "Fertig.", output_path=str(out_mp4)))
            return out_mp4

        # Fallback: spielbares .ts behalten
        out_ts = out_base.with_suffix(".ts")
        combined.replace(out_ts)
        self._cleanup(cache)
        msg = "Fertig (.ts). " + ("" if has_ffmpeg() else install_hint())
        self._emit(ProgressEvent("done", msg, output_path=str(out_ts)))
        return out_ts

    # ------------------------------------------------------------------ #
    # HTTP-Helfer für Playlists
    # ------------------------------------------------------------------ #
    def _fetch_master(self, usher_url: str, token: AccessToken, live: bool = False) -> str:
        params = {
            "sig": token.signature,
            "token": token.value,
            "allow_source": "true",
            "allow_audio_only": "true",
            "allow_spectre": "false",
            "player": "twitchweb",
            "playlist_include_framerate": "true",
            "supported_codecs": "av1,h265,h264",
            "p": str(random.randint(1, 10_000_000)),
        }
        if live:
            params["fast_bread"] = "true"
        try:
            r = self.session.get(usher_url, params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise TwitchDLError(f"Usher nicht erreichbar: {e}") from e
        if r.status_code == 404:
            raise NotFoundError("Usher: Inhalt nicht gefunden (404) — gelöscht, offline oder gesperrt.")
        if r.status_code == 403:
            raise NotFoundError("Usher: Zugriff verweigert (403) — sub-only/privat oder Token abgelaufen.")
        if r.status_code != 200:
            raise TwitchDLError(f"Usher HTTP {r.status_code}: {r.text[:200]}")
        return r.text

    def _get(self, url: str) -> str:
        try:
            r = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            raise TwitchDLError(f"Netzwerkfehler: {e}") from e
        if r.status_code != 200:
            raise TwitchDLError(f"HTTP {r.status_code} für Playlist.")
        return r.text

    # ------------------------------------------------------------------ #
    # Pfad-Helfer
    # ------------------------------------------------------------------ #
    def _output_base(self, output_dir: str, filename: Optional[str], info: MediaInfo, q: Quality) -> Path:
        d = Path(output_dir).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        if filename:
            stem = sanitize_filename(Path(filename).stem)
        else:
            parts = [info.author, info.title, q.name]
            stem = sanitize_filename(" - ".join(p for p in parts if p))
        return d / stem

    def _cache_dir(self, output_dir: str, ref: MediaRef, qname: str) -> Path:
        d = Path(output_dir).expanduser() / ".twitchdl-cache" / f"{ref.kind}-{ref.id}-{sanitize_filename(qname, 40)}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _cleanup(cache: Path) -> None:
        try:
            shutil.rmtree(cache, ignore_errors=True)
        except OSError:
            pass


# ---------------------------------------------------------------------- #
# Modul-Helfer
# ---------------------------------------------------------------------- #
def _as_ref(ref, expected_kind: str) -> MediaRef:
    if isinstance(ref, MediaRef):
        return ref
    parsed = parse_input(str(ref))
    return parsed


def _int(s: str) -> int:
    digits = "".join(ch for ch in str(s) if ch.isdigit())
    return int(digits) if digits else 0
