"""Twitch GraphQL-Client: Access-Tokens, Clip-Daten, VOD-Metadaten.

Nutzt den öffentlichen Web-Client-ID und rohe GraphQL-Queries (kein persisted-hash,
damit robust gegen Hash-Rotation auf Twitch-Seite).
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from .errors import AccessError, NotFoundError, TwitchDLError

GQL_URL = "https://gql.twitch.tv/gql"
# Öffentlicher Web-Player-Client-ID (kein Secret; im Browser frei einsehbar).
WEB_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

_PLAYBACK_ACCESS_TOKEN_QUERY = """
query PlaybackAccessToken($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: Boolean!, $playerType: String!) {
  streamPlaybackAccessToken(channelName: $login, params: {platform: "web", playerBackend: "mediaplayer", playerType: $playerType}) @include(if: $isLive) {
    value
    signature
  }
  videoPlaybackAccessToken(id: $vodID, params: {platform: "web", playerBackend: "mediaplayer", playerType: $playerType}) @include(if: $isVod) {
    value
    signature
  }
}
""".strip()

_CLIP_QUERY = """
query VideoAccessToken_Clip($slug: ID!) {
  clip(slug: $slug) {
    id
    title
    durationSeconds
    broadcaster { displayName login }
    videoQualities { frameRate quality sourceURL }
    playbackAccessToken(params: {platform: "web", playerBackend: "mediaplayer", playerType: "site"}) {
      signature
      value
    }
  }
}
""".strip()

_VIDEO_METADATA_QUERY = """
query VideoMetadata($id: ID!) {
  video(id: $id) {
    id
    title
    lengthSeconds
    owner { displayName login }
  }
}
""".strip()


class AccessToken:
    __slots__ = ("value", "signature")

    def __init__(self, value: str, signature: str) -> None:
        self.value = value
        self.signature = signature


class TwitchGQL:
    def __init__(self, session: Optional[requests.Session] = None, timeout: float = 15.0) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.setdefault("Client-ID", WEB_CLIENT_ID)
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        )

    # --- low level -----------------------------------------------------
    def post(self, query: str, variables: dict, operation: str) -> dict:
        payload = {"operationName": operation, "query": query, "variables": variables}
        try:
            r = self.session.post(GQL_URL, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise TwitchDLError(f"Netzwerkfehler bei GraphQL-Anfrage: {e}") from e
        if r.status_code != 200:
            raise TwitchDLError(f"GraphQL HTTP {r.status_code}: {r.text[:200]}")
        try:
            data = r.json()
        except ValueError as e:
            raise TwitchDLError("GraphQL-Antwort war kein gültiges JSON.") from e
        if isinstance(data, dict) and data.get("errors"):
            msgs = "; ".join(str(e.get("message", e)) for e in data["errors"])
            raise TwitchDLError(f"GraphQL-Fehler: {msgs}")
        return data.get("data", {}) if isinstance(data, dict) else {}

    # --- high level ----------------------------------------------------
    def playback_access_token(self, *, vod_id: str = "", channel: str = "") -> AccessToken:
        """Token für VOD (vod_id) ODER Live (channel)."""
        is_vod = bool(vod_id)
        variables = {
            "isLive": not is_vod,
            "login": channel.lower() if channel else "",
            "isVod": is_vod,
            "vodID": vod_id or "",
            "playerType": "embed",
        }
        data = self.post(_PLAYBACK_ACCESS_TOKEN_QUERY, variables, "PlaybackAccessToken")
        key = "videoPlaybackAccessToken" if is_vod else "streamPlaybackAccessToken"
        tok = data.get(key)
        if not tok or not tok.get("value") or not tok.get("signature"):
            what = f"VOD {vod_id}" if is_vod else f"Channel '{channel}'"
            raise NotFoundError(
                f"Kein Zugriffs-Token für {what}. "
                f"{'VOD existiert nicht / gelöscht / sub-only.' if is_vod else 'Channel ist offline oder existiert nicht.'}"
            )
        return AccessToken(tok["value"], tok["signature"])

    def clip(self, slug: str) -> dict:
        data = self.post(_CLIP_QUERY, {"slug": slug}, "VideoAccessToken_Clip")
        clip = data.get("clip")
        if not clip:
            raise NotFoundError(f"Clip '{slug}' nicht gefunden oder gelöscht.")
        qualities = clip.get("videoQualities") or []
        token = clip.get("playbackAccessToken") or {}
        if not qualities:
            raise NotFoundError(f"Clip '{slug}' hat keine abrufbaren Video-Qualitäten.")
        if not token.get("signature") or not token.get("value"):
            raise AccessError(f"Kein gültiges Token für Clip '{slug}'.")
        return clip

    def video_metadata(self, vod_id: str) -> dict:
        """Best-effort Metadaten; gibt {} zurück statt zu werfen."""
        try:
            data = self.post(_VIDEO_METADATA_QUERY, {"id": vod_id}, "VideoMetadata")
            return data.get("video") or {}
        except TwitchDLError:
            return {}
