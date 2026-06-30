# PRD & Technisches Konzept — `twitchdl`

> **Dokumenttyp:** Product Requirements Document + Implementierungs-Spezifikation
> **Adressat:** Eine KI (Coding-Agent), die dieses Dokument als alleinige Quelle zur fehlerfreien Implementierung nutzt.
> **Version:** 1.0 · **Status:** umgesetzt · **Letztes Update:** 2026-06-29

---

## 0. TL;DR für die implementierende KI

Baue ein Python-Paket `twitchdl`, das **Twitch VODs, Clips und Live-Streams** herunterlädt. Kein
offizieller Twitch-Download-Endpoint existiert; der Weg führt über die **interne GraphQL-API** +
**Usher-HLS-Endpoints**. Liefere zwei Frontends auf einer gemeinsamen Engine: eine **CLI** und eine
**lokale Web-UI** (Flask + Server-Sent-Events für Live-Fortschritt). Output ist standardmäßig MP4
(via ffmpeg `-c copy`), mit sauberem Fallback auf `.ts` wenn ffmpeg fehlt.

**Kernpipeline (auswendig lernen):**
```
URL/ID ──parse──► {kind, id}
   VOD:  GraphQL PlaybackAccessToken ─► usher /vod/{id}.m3u8 ─► master ─► media(.ts) ─► download‖ ─► ffmpeg mux ─► out.mp4
   LIVE: GraphQL PlaybackAccessToken ─► usher /api/channel/hls/{ch}.m3u8 ─► media poll-loop ─► download‖ ─► ffmpeg mux ─► out.mp4
   CLIP: GraphQL VideoAccessToken_Clip ─► videoQualities[].sourceURL + sig/token ─► direkter MP4-Download ─► out.mp4
```

---

## 1. Vision & Zielsetzung

**Vision:** Das robusteste, am einfachsten bedienbare Self-Hosted-Tool, um eigene oder öffentliche
Twitch-Inhalte lokal zu archivieren — ohne Drittanbieter-Webseiten, ohne Tracking, ohne Limits.

**Produktziele**
| Ziel | Messbar gemacht durch |
|---|---|
| Zuverlässigkeit | Download bricht nie ungeprüft ab; jedes fehlende Segment wird geretryt; klare Fehlermeldungen |
| Vollständigkeit | VOD + Clip + Live in V1 |
| Geschwindigkeit | Paralleler Segment-Download (Default 10 Worker), sättigt typische Heim-Bandbreite |
| Bedienbarkeit | CLI für Power-User + Web-UI „URL rein, Datei raus" für alle anderen |
| Portabilität | Reines Python 3.9+; einzige externe Binärabhängigkeit = ffmpeg (optional mit Fallback) |

**Nicht-Ziele (V1):** DRM-Umgehung (Twitch nutzt kein DRM auf VODs), Re-Encoding/Transcoding,
Untertitel/Chat-Export, Scheduling/Auto-Capture, Cloud-Deployment.

---

## 2. Rechtlicher & ethischer Rahmen (verbindlich)

Dieses Tool ist für **legitime Zwecke**: Archivierung eigener Inhalte, Backup öffentlich
zugänglicher VODs/Clips, Fair-Use (Forschung, Berichterstattung, Barrierefreiheit).

- Die Software lädt **ausschließlich öffentlich erreichbare** Inhalte; kein Bypass von
  Bezahlschranken über fremde Konten. Sub-only/private VODs sind in V1 **bewusst ausgeklammert**
  (würde Login/OAuth erfordern — siehe Roadmap).
- Die UI zeigt einen Hinweis: Nutzer ist für die Einhaltung der Twitch-ToS und des Urheberrechts
  verantwortlich.
- Kein Rate-Limit-Hammering: respektvolle Concurrency-Defaults, Retries mit Backoff.

---

## 3. Personas & Top-Use-Cases

1. **Der Streamer (Owner):** „Ich will mein gestriges 6h-VOD sichern, bevor Twitch es nach 14 Tagen
   löscht." → VOD-Download in Source-Qualität, robust gegen 6h Länge.
2. **Der Editor/Clipper:** „Ich brauche diese 30s-Clips als MP4 für den Schnitt." → Clip-Batch.
3. **Der Archivar:** „Ich nehme diesen Live-Stream jetzt mit auf." → Live-Recording bis Stopp.
4. **Der Power-User:** „Skript-Integration, Qualität wählen, Zielordner setzen." → CLI mit Flags.

---

## 4. Funktionale Anforderungen

### 4.1 Eingabe
- **FR-1** Akzeptiere VOD-URLs: `twitch.tv/videos/{id}`, bare `{id}`.
- **FR-2** Akzeptiere Clip-URLs: `clips.twitch.tv/{slug}`, `twitch.tv/{ch}/clip/{slug}`,
  `twitch.tv/{ch}/clips/{slug}`, bare `{slug}`.
- **FR-3** Akzeptiere Channel/Live-URLs: `twitch.tv/{channel}`, bare `{channel}`.
- **FR-4** Auto-Erkennung des Inhaltstyps aus der URL; manueller Override per Flag/Dropdown.

### 4.2 Info / Discovery
- **FR-5** `info`-Funktion: liste verfügbare Qualitäten (Auflösung, FPS, Bandbreite) **ohne**
  Download. Dient zugleich als End-to-End-Smoke-Test.

### 4.3 Download
- **FR-6** Qualitätswahl: `best` (Default), `worst`, `audio` (audio_only), oder exakte Wahl
  (`1080p60`, `720p`, …). `best` = höchste Bandbreite (i.d.R. „chunked"/Source).
- **FR-7** Paralleler Segment-Download mit konfigurierbarer Worker-Zahl (Default 10).
- **FR-8** Pro-Segment-Retry mit exponentiellem Backoff (Default 5 Versuche).
- **FR-9** Stummgeschaltete VOD-Segmente (`-muted.ts`/`-unmuted.ts`) korrekt behandeln:
  herunterladen was die Playlist nennt; optional `--try-unmute` zum Wiederherstellungsversuch.
- **FR-10** Live: Media-Playlist im Loop pollen (Intervall = Segmentdauer), neue Segmente
  anhängen, bei `#EXT-X-ENDLIST` oder Nutzer-Stopp sauber finalisieren; Ad-/Discontinuity-Marker
  tolerieren ohne Abbruch.
- **FR-11** Muxing: Segmente → MP4 via ffmpeg (`-c copy`, AAC-Bitstreamfilter `aac_adtstoasc`).
  Fallback ohne ffmpeg: Byte-Konkatenation der `.ts` zu spielbarem `.ts` + Warnung.
- **FR-12** Resume/Idempotenz: bereits geladene Segmente im Temp-Ordner werden nicht erneut geladen.
- **FR-13** Zielpfad/Dateiname konfigurierbar; Default aus Titel/ID + sichere Sanitization.

### 4.4 Frontends
- **FR-14 CLI:** Subcommands `info`, `download` (auto), `vod`, `clip`, `live`; Flags für Qualität,
  Output, Worker, Web-Port.
- **FR-15 Web-UI:** Single-Page: URL-Eingabe → „Analysieren" (zeigt Qualitäten) → „Download" mit
  Live-Fortschrittsbalken via SSE; Stopp-Button für Live.

### 4.5 Fortschritt & Feedback
- **FR-16** Einheitliches Progress-Interface (Callback): Phase, aktuelle/Gesamt-Segmente, Bytes,
  Geschwindigkeit, ETA. CLI rendert Balken im Terminal, Web rendert über SSE.

---

## 5. Nicht-funktionale Anforderungen
- **NFR-1 Robustheit:** Keine unbehandelte Exception erreicht den Nutzer; alles wird zu klaren,
  handlungsleitenden Fehlermeldungen (`TwitchDLError`-Hierarchie).
- **NFR-2 Performance:** 1h Source-VOD lädt bandbreitenbegrenzt, nicht CPU-/Latenz-begrenzt.
- **NFR-3 Portabilität:** macOS/Linux/Windows; Python 3.9+; `from __future__ import annotations`.
- **NFR-4 Minimale Deps:** nur `requests` (+ `flask` für Web-UI). ffmpeg extern & optional.
- **NFR-5 Wartbarkeit:** klare Modultrennung, reine Funktionen wo möglich, Unit-Tests für Parser.
- **NFR-6 Testbarkeit:** Netzfreie Unit-Tests für URL- & m3u8-Parsing; `info` als Live-Smoke-Test.

---

## 6. Technische Architektur (Research-Ergebnis)

### 6.1 Twitch-Auslieferung — Fakten
- **GraphQL-Endpoint:** `https://gql.twitch.tv/gql` (POST, JSON).
- **Öffentlicher Web-Client-ID:** `kimne78kx3ncx6brgo4mv6wki5h1ko` (Header `Client-ID`).
  Akzeptiert **rohe** GraphQL-Queries (kein persisted-hash nötig → robuster gegen Hash-Rotation).
- **Usher (HLS-Token-Gateway):**
  - VOD: `https://usher.ttvnw.net/vod/{vodID}.m3u8`
  - Live: `https://usher.ttvnw.net/api/channel/hls/{channel}.m3u8`
  - Query-Params: `sig` (=signature), `token` (=value, URL-encoded), `allow_source=true`,
    `allow_audio_only=true`, `player=twitchweb`, `playlist_include_framerate=true`,
    `supported_codecs=av1,h265,h264`, `p={random}`, (Live zusätzlich `fast_bread=true`).

### 6.2 GraphQL-Operationen (rohe Queries)
**VOD/Live Token — `PlaybackAccessToken`:**
```graphql
query PlaybackAccessToken($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: Boolean!, $playerType: String!) {
  streamPlaybackAccessToken(channelName: $login, params: {platform: "web", playerBackend: "mediaplayer", playerType: $playerType}) @include(if: $isLive) { value signature }
  videoPlaybackAccessToken(id: $vodID, params: {platform: "web", playerBackend: "mediaplayer", playerType: $playerType}) @include(if: $isVod) { value signature }
}
```
Variablen VOD: `{isLive:false, login:"", isVod:true, vodID:"<id>", playerType:"embed"}`
Variablen Live: `{isLive:true, login:"<channel>", isVod:false, vodID:"", playerType:"embed"}`

**Clip — `VideoAccessToken_Clip`:**
```graphql
query VideoAccessToken_Clip($slug: ID!) {
  clip(slug: $slug) {
    id title durationSeconds
    broadcaster { displayName login }
    videoQualities { frameRate quality sourceURL }
    playbackAccessToken(params: {platform: "web", playerBackend: "mediaplayer", playerType: "site"}) { signature value }
  }
}
```
Download-URL je Quality = `sourceURL + "?sig=" + signature + "&token=" + urlencode(value)`.

**Metadaten (optional, schöner Dateiname) — VOD:** Query `VideoMetadata`/`video(id:)` für `title`,
`owner.displayName`, `lengthSeconds`. Best effort; Fehler hier brechen den Download nicht ab.

### 6.3 HLS-Parsing
- **Master-Playlist:** Zeilenpaare `#EXT-X-MEDIA:...,NAME="..."` / `#EXT-X-STREAM-INF:BANDWIDTH=...,RESOLUTION=...,...` gefolgt von der Varianten-URL.
  → Liste von `Quality{name, group_id, resolution, fps, bandwidth, url}`.
- **Media-Playlist:** `#EXTINF:<dur>,` gefolgt vom Segment-Dateinamen (relativ). Base-URL =
  Varianten-URL ohne Dateinamen. `#EXT-X-ENDLIST` markiert Ende (VOD/finished).
- **Muted:** Segmentnamen können auf `-muted.ts` enden. Standard: laden wie gelistet.
  `--try-unmute`: ersetze `-muted` → `-unmuted` und probiere, sonst Fallback auf gemutete Variante.

### 6.4 Muxing
- Segmente in Temp-Ordner, in Reihenfolge zu einer `combined.ts` konkateniert.
- ffmpeg: `ffmpeg -y -i combined.ts -c copy -bsf:a aac_adtstoasc -movflags +faststart out.mp4`.
- Fehlt ffmpeg → behalte `combined.ts` (spielbar) + Warnung mit Install-Hinweis (`brew install ffmpeg`).

### 6.5 Komponentenmodell (Module)
```
twitchdl/
  errors.py     # Exception-Hierarchie (TwitchDLError → InvalidURLError, NotFoundError, ...)
  models.py     # @dataclass: MediaRef, Quality, MediaInfo, Segment, ProgressEvent
  parser.py     # parse_input(str) -> MediaRef{kind: vod|clip|channel, id}
  gql.py        # TwitchGQL: post(), playback_access_token(), clip(), video_metadata()
  hls.py        # parse_master(text,url)->[Quality]; parse_media(text,url)->(segments,ended)
  ffmpeg.py     # has_ffmpeg(); mux_ts_to_mp4(); concat fallback
  core.py       # Downloader: info(), download_vod(), download_clip(), record_live(); _fetch_segments‖
  cli.py        # argparse-Frontend
  webapp.py     # Flask + SSE-Frontend
  __main__.py   # python -m twitchdl
```

### 6.6 Concurrency- & Fehlerstrategie
- `ThreadPoolExecutor(max_workers=N)` für Segmente; Reihenfolge über Index-Map gewahrt.
- `requests.Session` mit Connection-Pool; pro Request Timeout.
- Pro-Segment: bis zu `retries` Versuche, Backoff `min(2^attempt, 30)s`; danach harter Fehler
  (außer Segment ist als optional/muted bekannt → loggen & weiter).
- Globaler KeyboardInterrupt → Live sauber finalisieren (bereits geladene Segmente muxen).

---

## 7. Edge-Cases (Checkliste für die KI)
- [ ] VOD-ID mit/ohne `v`-Präfix, mit Query-/Fragment-Anhängseln in der URL.
- [ ] Clip-Slug enthält Groß-/Kleinschreibung & Bindestriche; URL mit `?t=`/Tracking-Params.
- [ ] Master-Playlist ohne RESOLUTION (audio_only), Varianten-Reihenfolge nicht garantiert.
- [ ] Media-Playlist mit `-muted` Segmenten mitten im VOD.
- [ ] Live-Playlist: neue Segmente zwischen Polls, Duplikate vermeiden (per Sequence/Name dedupen).
- [ ] Live-Stream offline/nicht live → klare NotFound-Meldung statt Stacktrace.
- [ ] usher 403/Token abgelaufen → aussagekräftiger Fehler.
- [ ] Geo-/Sub-only/410-VOD → NotFound/Restricted-Meldung.
- [ ] Dateinamen mit `/ : * ? " < > |` → sanitisieren.
- [ ] ffmpeg fehlt → Fallback `.ts`, kein Crash.
- [ ] Sehr lange VODs (Tausende Segmente) → Speicher: Segmente auf Disk, nicht im RAM.

## 8. Akzeptanzkriterien
- **AC-1** `python -m twitchdl info <public-vod-url>` listet ≥1 Qualität (beweist GQL+Usher+HLS live).
- **AC-2** `download` erzeugt eine spielbare Datei; mit ffmpeg `.mp4`, sonst `.ts`.
- **AC-3** Unit-Tests für `parser` & `hls` grün (netzfrei).
- **AC-4** Web-UI startet, zeigt Qualitäten nach „Analysieren", streamt Fortschritt.
- **AC-5** Keine unbehandelte Exception bei ungültiger URL / offline Channel / fehlendem ffmpeg.

## 9. Roadmap (Post-V1)
OAuth-Login für Sub-only/private VODs · Chat-Download (Rechat-API) · Untertitel/Transcript ·
Batch-/Playlist-Import · Auto-Capture-Scheduler · Docker-Image · Transcoding-Profile.
