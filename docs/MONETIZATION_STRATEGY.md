# vodfetch — Monetarisierungsstrategie

**Stand: 2026-07-29 · Iteration 1 · Verfasser: CPO-Rolle**
Grundlage: 6 Rechercheachsen (Wettbewerbspreise, Schmerzpunkte, Zahlungsbereitschaft, Recht/ToS,
Kostenmodell, internationale Nachfrage). Alle Zahlen mit Quelle; Unverifiziertes ist als solches markiert.

---

## 1. Urteil vorweg

**Ein klassisches SaaS-Abo auf der Streamer-Zielgruppe ist nach Beweislage schwach. Der eine
Premium-Feature, den man intuitiv bauen würde — serverseitiges Auto-Archiv — ist zugleich der
juristisch gefährlichste Schritt, den dieses Projekt machen kann.**

Das ist kein Pessimismus, sondern das Ergebnis dreier unabhängiger Befunde, die alle in dieselbe
Richtung zeigen. Die tragfähige Monetarisierung liegt woanders und ist zu ~90 % bereits gebaut.

---

## 2. Der juristische Befund (entscheidungsrelevant, nicht nur „Risiko")

| Fund | Bedeutung |
|---|---|
| **Twitch Developer Agreement**: „Do not store copies of Twitch Content … unless (a) prior written authorization, (b) control the rights", mit **24-Stunden-Obergrenze** | Serverseitiges Archiv ist ein glatter Vertragsbruch, kein Graubereich |
| **ToS §7** nimmt „resale or **commercial use** of the Twitch Services or the Materials" ausdrücklich aus der Lizenz aus | Geldnehmen verschiebt die Bewertung |
| **Fox News v. TVEyes** (2d Cir. 2018, No. 15-3885) — bezahlter serverseitiger Archivdienst, 500 $/Monat — **in der Berufung verloren** | Direkter Präzedenzfall für genau das Geschäftsmodell |
| **Cartoon Network v. CSC** (Cablevision, 2d Cir. 2008) — bei client-initiierter Aufnahme liefert **der Kunde** das „volitional element", nicht der Betreiber | Die heutige Architektur ist juristisch **tragend**, nicht nur billig |
| **17 U.S.C. §512(c)(1)(B)** — Safe Harbor entfällt bei „direct financial benefit" aus kontrollierbarer Aktivität | Bezahlung schwächt den Schutz aktiv |
| Safe Harbor setzt registrierten DMCA-Agenten voraus (Neuregistrierung alle 3 Jahre) — **derzeit nicht vorhanden** | Selbst der bestehende Schutz ist unvollständig |

**Konsequenz:** Die Client-seitigkeit ist kein Kostentrick, sondern das juristische Fundament.
Serverseitiges Speichern fremder Streams **und** dafür Geld nehmen reproduziert exakt den
TVEyes-Sachverhalt. Nicht ohne Anwalt. Ich empfehle es auch mit Anwalt nicht.

---

## 3. Zahlungsbereitschaft: die Zielgruppe kann überwiegend nicht zahlen

- **Twitch-Einkommen ist extrem konzentriert** (Leak Okt 2021, 4,9 Mio. Konten, 889 Mio. $ Auszahlungen
  Jan–Sep 2021): Top 1 % nahmen ~die Hälfte. Von denen, die überhaupt etwas verdienten, machten
  **~50 % ≤ 28 $** und **75 % ≤ 120 $** — insgesamt, nicht monatlich.
- **StreamElements**: 111 Mio. $ Kapital, ~23 Mio. Creator, alles kostenlos, **nie profitabel**.
- **„Keep It Live"** (Jan 2026): StreamElements bat 23 Mio. Creator, ~300.000 $/Monat Serverkosten
  mitzutragen → **~2.000 $ von 80 Personen in 30 Tagen**. *(Einzelquelle, als unsicher markiert.)*
- **OBS Studio**, meistgenutzte Streaming-Software der Welt: **2.309 €/Monat** von 12.144 Patreon-Mitgliedern.
- r/Twitch ist ausgeprägt preisresistent; Standardantwort auf jedes Bezahltool ist die kostenlose Alternative.

**Gegenbeweis — es wird sehr wohl gezahlt, aber nur für zwei Dinge:**
- **OpusClip** ~20 Mio. $ Umsatz 2025 (+150 % YoY) → **KI-Arbeit**, die der Nutzer selbst nicht leisten kann
- **Restream** ~15 Mio. $ 2024 → **unbeaufsichtigte Server**, die ein Browser-Tab nicht ersetzen kann

Beides ist für vodfetch entweder nicht vorhanden (KI) oder juristisch versperrt (Server-Archiv).

---

## 4. Wo die Kategorie die Paywall zieht

Wettbewerbsbefund, ausnahmslos: **niemand verlangt Geld für den Download selbst.** Bezahlt wird an fünf
Stellen, alle serverseitig: Rechenleistung (KI-Clips, Untertitel), Speicher/Aufbewahrungsdauer,
Parallelität, Wasserzeichen-Entfernung, Auflösung.

| Anbieter | Preis | hinter der Paywall |
|---|---|---|
| StreamLadder | 9 / 15 / 27 $ | 720p→1080p, Wasserzeichen, Exportlimits |
| Eklipse | 24,99 $/Mo (179,99 $/Jahr) | KI-Highlight-Erkennung |
| OpusClip | 15 / 29 $ | Credits; **Speicher verfällt nach 3 Tagen** im Free-Tier |
| Kapwing | 24 $ (16 $ jährl.) | Wasserzeichen, 4K, Credits |
| **StreamRecorder.io** | *(nicht publiziert)* | **genau Auto-Recording**: frei = 720p/3 Kanäle/5 Tage; Premium = 8K/100 Kanäle/60 Tage |

StreamRecorder.io ist der einzige direkte Beleg, dass Auto-Recording verkäuflich ist — und betreibt
genau das Modell, das vertraglich/juristisch problematisch ist.

---

## 5. Kostenmodell (falls doch jemals serverseitig)

Basis: 1080p60 = 6.160 kbps CBR = **2,772 GB je aufgezeichneter Stunde**.

| Stack | Grenzkosten je aufgez. Stunde (30 T. Speicher + 1 Download) |
|---|---|
| Hetzner + Cloudflare R2 | **0,0424 $** |
| Hetzner + Backblaze B2 | **0,0199 $** |
| alles AWS | 0,3166 $ |
| **ohne Speicherung**, direkte Übergabe an die Cloud des Nutzers | **0,0038 $** |

100 Streams à 4 h/Monat ≈ 21 $/Monat gesamt. **Rechenleistung ist ein Rundungsfehler** — Aufnehmen ist
kein Transcoding, nur HLS-Segmente ziehen. Der Kostentreiber ist ausschließlich **Speicher**.

Der Fall „nicht speichern, sofort übergeben" ist **11× billiger als R2** — und juristisch der einzige
serverseitige Pfad, der überhaupt diskutabel wäre (kein Archiv, keine Bibliothek, keine Suche über
fremde Inhalte). Bleibt trotzdem am 24-Stunden-Passus des Developer Agreements zu prüfen.

---

## 6. Internationale Nachfrage — zwei teure Fallen

StreamsCharts, Woche 28.06.–04.07.2026 (~303 Mio. h): **Englisch 49 %**, Russisch 12 %, Deutsch 7 %,
Japanisch 7 %, Französisch 6 %.

- **Russland ist die größte Falle im Datensatz**: 12 % der Sehdauer — Platz 2, das 3,5-fache des
  deutschen Volumens — und monetarisiert bei **null** (Google Regional Monetization Pause).
- **Korea streichen**: Twitch hat den Betrieb dort am **27.02.2024** eingestellt (Netzentgelte).
- ARPU: US 6,21 $ · UK 6,05 $ · **FR 2,50 $** · **DE 2,30 $** · PL 1,73 $ · **TR 0,18 $** (≈3 % der US-Rate).

**Nur Deutsch und Französisch nehmen beide Hürden** (relevantes Twitch-Volumen *und* tragfähige
Werbeerlöse). Japanisch hätte die Rate, ist aber sprachlich der teuerste Lokalisierungsfall.

---

## 7. Empfehlung

### 7.1 Was NICHT gebaut wird
**Serverseitiges Auto-Archiv gegen Bezahlung.** Vertragsbruch laut Developer Agreement, TVEyes ist
direkter Präzedenzfall, Bezahlung entzieht Safe Harbor. Der Erwartungswert ist negativ.

### 7.2 Der ehrliche Hauptpfad: Werbung + SEO, richtig gemacht
Null Rechtsdelta, null Markenbruch, null Infrastruktur — und bereits gebaut: 195.480 Wörter Inhalt,
111 indexierte URLs, sauberes Audit. **Der Engpass ist die AdSense-Freigabe, nicht das Produkt.**
Bei US-RPM 6,21 $ ist das die einzige Erlösquelle, die ohne neue Risiken skaliert.
Lokalisierung ausschließlich **DE + FR**, und diesmal redaktionell statt maschinell.

### 7.3 Vor jedem Backend: Nachfrage messen, nicht vermuten
Eine Preis-/Warteliste-Seite kostet einen Tag und liefert echte Kaufabsicht. Bei dieser Beweislage
wäre es fahrlässig, zuerst zu bauen. **Kill-Kriterium: <2 % Conversion auf die Warteliste → Thema beendet.**

### 7.4 Falls doch bezahlt: die einzige verteidigbare Linie
> Kostenlos bleibt alles, was **dein Browser** kann. Bezahlt würde nur, was **eine Maschine braucht,
> die nie schläft** — und selbst das nur ohne Speicherung fremder Inhalte.

Damit bricht keine der veröffentlichten Zusagen, weil sie sich auf das Werkzeug beziehen, das kostenlos bleibt.

---

## 8. Der Markenkonflikt, der zuerst gelöst sein muss

Die Seite legt sich heute **wörtlich** fest:

| Zusage | Dateien |
|---|---|
| „100% free — no trial, **no paywall**, no 'premium' upsell" | 35 |
| „No Twitch login, no sign-up and **no paywall**" | 45 |
| „…funded by a couple of small ads and has **no paywall or premium tier**" | 6 (inkl. **FAQ-JSON-LD**) |

Der letzte Satz steht in strukturierten Daten, die KI-Systeme zitieren. Das Projekt hat für so eine
Rücknahme schon einmal bezahlt (Rückzug von „no ads / no tracking" in 14 Sprachen). Eine Paywall ohne
vorherige, saubere Auflösung dieser Zusagen kostet mehr Vertrauen, als sie einbringt.

---

## 9. Offene Punkte für die Eigentümerentscheidung

1. **Risikoappetit**: Ist serverseitige Verarbeitung überhaupt eine Option — auch nach TVEyes?
2. **Markenposition**: Sollen die „no paywall"-Zusagen bestehen bleiben? (Meine Empfehlung: ja.)
3. **DMCA-Agent registrieren?** ~6 $ Gebühr, schützt bereits den heutigen Betrieb.
4. **DE/FR-Lokalisierung** redaktionell — freigeben?

---

## 10. Belastbarkeitsgrenzen dieser Analyse

- **Keine Semrush-Daten** in dieser Session (API-Kontingent erschöpft) — alle Suchvolumina stammen aus
  früheren Ubersuggest-Exporten oder Drittaggregatoren und sind **unbestätigt**.
- **Reddit war für direkten Abruf gesperrt** — Schmerzpunkt-Zitate stammen aus Sekundärquellen.
- **Twitch ToS/Developer Agreement** konnten nicht im Original abgerufen werden (JS-gerendert); die
  Zitate stammen aus Sekundärquellen und sollten vor jeder Entscheidung im Original geprüft werden.
- StreamRecorder.io-Preise und einzelne Wettbewerberpreise sind nicht primärbelegt.
