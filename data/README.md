# vodfetch — offene Twitch-Snapshot-Daten („seit 2026")

Dieses Verzeichnis ist der **History-Flywheel** aus `docs/TRACKER_DOMINATION_PLAN.md` (T0.4):
tägliche, kompakte Snapshots der öffentlichen Twitch-Landschaft, gesammelt über die
**offizielle Twitch Helix API** (App-Access-Token). Kein Scraping, kein unoffizielles GQL,
keine privaten Daten — nur, was Twitch selbst öffentlich ausliefert.

## Warum

Die etablierten Tracker (TwitchTracker seit ~2015, SullyGnome seit 08/2015) haben als
einzigen echten Moat ihre Historie. Die kann niemand nachkaufen — man kann nur **heute**
anfangen zu sammeln. Diese Daten sind bewusst **von Deploys entkoppelt**: Noch konsumiert
keine Seite auf vodfetch.com diese Dateien. Erst wenn Monate sauberer Daten vorliegen,
entstehen daraus ehrliche „Follower-Wachstum"-/„Trending"-Seiten (Batch T6) — beschriftet
mit „tracked by vodfetch since 2026", nie mit mehr, als die Daten hergeben.

## Struktur

- `roster.json` — kuratierte Kanalliste (~115 Kanäle EN/DE/FR/ES), editierbar.
- `snapshots/YYYY-MM-DD.json` — ein Snapshot pro Tag (2. Lauf des Tages überschreibt):
  - `top_games` — Helix `games/top`-Ranking (der Endpunkt liefert keine Zuschauerzahlen).
  - `game_viewers` — **Näherung:** Zuschauer-Summen je Spiel über die Top-~1000-Streams
    (nicht das gesamte Verzeichnis; so dokumentiert, so ehrlich).
  - `top_streams` — Top-300-Streams (Login, Spiel, Zuschauer, Sprache, Startzeit).
  - `lang_top_streams` — Top-50 je DE/FR/ES.
  - `roster_followers` — **exakte** Follower-Totale (Helix `channels/followers`).
  - `totals.by_language` — Zuschauer-/Kanal-Summen je Sprache (über die Top-Streams).
- `latest.json` — Kopie des neuesten Snapshots.
- `series/roster-followers.csv` — Follower-Zeitreihe, deterministisch aus allen
  Snapshots regeneriert (eine Zeile pro Kanal, eine Spalte pro Tag).

## Methodik & Grenzen (ehrlich)

- Sampling 2×/Tag — Peaks zwischen den Läufen werden nicht erfasst.
- `game_viewers` unterschätzt Long-Tail-Spiele systematisch (nur Top-Streams summiert).
- Lücken sind möglich (GitHub-Actions-Cron ist best-effort) und bleiben als Lücken
  sichtbar — sie werden nicht interpoliert.
- Serie beginnt 2026-07. Alles davor existiert nicht und wird nie behauptet.

Lizenz: Daten (Twitch-Fakten) sind nicht schutzfähig; die Aufbereitung steht unter
[MIT](../LICENSE) wie das Projekt. Quelle bei Weiterverwendung bitte als
„vodfetch.com Twitch snapshots" nennen.
