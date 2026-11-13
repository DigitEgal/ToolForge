# Anforderungsabgleich V1.3

Basis: ToolForge V1.2 einschließlich aller Regressionen aus 0.1 bis V1.2. Geprüft wurde der Code-, API- und UI-Stand. Reale GPU-, Docker-, Aider-, OpenCode-, Tray- und Signaturprüfungen bleiben im Testbericht gesondert abgegrenzt; die automatisierten Tests verwenden dafür isolierte Projekte und simulierte Schnittstellen.

Historische Abgleiche: [0.8](docs/archiv/ABNAHME_V08.md) · [V1.0](docs/archiv/ABNAHME_V10.md) · [V1.1](docs/archiv/ABNAHME_V11.md)

## V1.3-Pflichtpunkte

| ID | Anforderung | Umsetzung | Beleg |
|---|---|---|---|
| V13-1 | Desktop-Pilot über „Pilot öffnen“ tatsächlich starten | Die Sidebar-Schaltfläche ruft `POST /api/pilot/open` auf. `PilotLauncher` startet `start_toolforge_pilot.py` bevorzugt mit `pythonw.exe` aus `.venv`, schreibt Startbefehl und Ausgabe nach `%APPDATA%\ToolForgePilot\desktop-start.log` und meldet Fehlstarts mit Protokollauszug. „Cockpit öffnen“ bleibt ein separater Browser-Weg. | `backend/tests/test_api.py::test_open_pilot_and_opencode_console_routes`, Quellprüfung, echter Start-Smoke-Test mit laufendem `pythonw.exe`. |
| V13-2 | Vorabcheck nach Fehlern und Planänderungen wiederholbar | `PreflightPanel` bietet dauerhaft sichtbar „Vorabcheck erneut ausführen“ und „Kandidaten erneut laden“. Der Bericht speichert `candidates`, `judge`, `kind`, `context_tokens`, `source_mode`, `preference`, `skipped_sources` und gemessene `alternatives`. Geänderte Aufgabe, Quellen-Vorauswahl oder Reihenfolge werden als veraltet markiert; bei geänderter Vorauswahl werden Kandidaten frisch geladen. Der letzte Bericht bleibt auch nach einem Fehler sichtbar. | API-Test `test_session_can_rerun_preflight_from_stored_candidates`, Routing-/Preflight-Tests, Quellprüfung. |
| V13-3 | Kleine Modelle unter 16 GB zuverlässiger machen | Kompaktere Prompts mit Definition of Done, Abnahmekriterien und Prüf-Checkliste; `small_model_mode` bevorzugt ganze Dateien statt Diffs; Top-p wird an Aider übergeben; Python-Dateien werden vor der nächsten Reparatur per `ast` syntaktisch geprüft. Aufgabenaufteilung und frische Kontextfenster bleiben erhalten. | Python-Tests, Quellprüfung, `npm run build`. |
| V13-4 | Kostenlose LLMs ohne zusätzliche Einrichtung anbieten | `toolforge_pilot/opencode.py` findet den lokalen OpenCode-Dienst über dessen Dienstdatei, authentifiziert sich lokal und liest den kostenlosen Modellkatalog. Vorabcheck, Planung, Hilfe und Aider-Brücke nutzen die freien Modelle; ein Konto oder API-Schlüssel ist nicht erforderlich. | `tests/test_opencode.py`, Quellprüfung, realer Katalogtest. |
| V13-5 | Gemeinsames Free-Tageslimit korrekt behandeln | Alle `-free`-Modelle teilen ein Kontingent. Bei `shared_quota`/`rate_limit` wird die gesamte Free-Quelle bis zum gemeldeten Reset gesperrt; es folgt kein Free-zu-Free-Modellwechsel. Erlaubte lokale oder bezahlte API-Quellen übernehmen nur, wenn die Vorauswahl sie enthält; Nur Free hält mit Erklärung an. | `test_generate_stops_on_shared_quota_without_free_model_switch`, `test_generate_reports_shared_quota_with_retry_after`, `test_planning_quota_falls_back_only_to_allowed_local_source`, `test_free_only_quota_never_falls_back_to_local_or_api`. |
| V13-6 | Modellquellen-Presets, Reihenfolge und Modelle pro Quelle | Unter **Einstellungen → Modellquellen** stehen Nur Lokal, Nur Free, Nur API, Free & Lokal, Lokal & API und Free & API bereit. MAX Quality, Preis/Leistung und Kostensparend legen die Quellen-Reihenfolge fest. Jede Quelle hat ein eigenes Modellfeld; die aktive Quelle bleibt beim laufenden Auftrag zuerst. Ungültige Quellen-Kombinationen werden serverseitig abgelehnt. | `tests/test_routing.py`, `test_configure_validates_preset_and_keeps_per_source_models`, UI-Quellprüfung. |
| V13-7 | Version im gesamten Projekt auf V1.3 anheben | FastAPI und `/api/workbench` melden `1.3.0`, die Workbench-Stage ist `13`. Frontend-Paket und Lockfile tragen `1.3.0`; Sidebar, Roadmap, Startbanner, Setup-Ausgabe, Hilfe, Installer, Buildskript und Dokumentation nennen V1.3 beziehungsweise dreizehn Etappen. | API-Test, Quellprüfung, `npm run build`. |
| V13-8 | Alle bisherigen Funktionen weiter prüfen | Die vollständige V1.2-Suite bleibt erhalten; hinzugekommen sind Tests für OpenCode-Katalog, gemeinsames Quota-Verhalten, Quellen-Presets, Routing-Studio, API-Quelle, Studio-Fassade, OpenAI-Brücke, Dienstdatei und wiederholten Vorabcheck. | [TESTBERICHT.md](TESTBERICHT.md), vollständiger Testlauf. |
| V13-9 | OpenCode ohne Startverzögerung prüfen und bedienen | `ModelSourcesPanel` bietet Status prüfen, Dienst starten und „Konsole öffnen“. Diese Aktionen werden ausschließlich auf Klick ausgeführt; `open_console` startet ein sichtbares Terminal im Projektordner. Der normale ToolForge-Start ruft weder Status noch Konsole auf. | `backend/tests/test_api.py::test_open_pilot_and_opencode_console_routes`, Quellprüfung, Start-Smoke-Test. |
| V13-10 | Bezahlte API als ausdrücklich erlaubte Quelle | OpenAI-kompatible API mit Basisadresse, Sitzungsschlüssel und eigenem Modellfeld. Der Schlüssel bleibt in der Sitzung und wird nicht gespeichert; die API wird nur innerhalb einer Vorauswahl mit API verwendet. | `tests/test_routing.py`, Quellprüfung. |

## Funktionsbasis V1.2

- V7-Tool-Logo und V6-DigitEgal-Wortmarke in Sidebar, Abschlussbildschirm und Tutorial.
- Verzögertes Laden von Cockpit, Hilfe, Projektverwaltung, Analyse, Entwicklungsbereich und CodeMirror.
- Gehashte Assets mit langfristigem Cache; `index.html` bleibt `no-cache`.
- Konsolidierter Testbericht und archivierte historische Anforderungsabgleiche.
- API `1.2.0`, Workbench-Stage `12`, Frontend `1.2.0`, Installer `1.2`.

## Marken- und Versionsabgleich

- Tool-Logo: `LogoV7_OnlyLOGO.png` (1815 × 1815, transparent) in Sidebar, Shutdown-Karte und Tutorial-Willkommen.
- Wortmarke: `LogoV6_textONLY.png` (2657 × 748, transparent) mit Größenverhältnis 3,55 : 1; keine Verzerrung durch feste Breite.
- Der Link „by DigitEgal“ bleibt ein einzelner, extern geöffneter Link ohne zusätzliches SVG-„D“.
- API: `1.3.0`; Workbench: Stage `13`; Frontend: `1.3.0`; Installer-Definition: `1.3`.
- Die dreizehnte Etappe heißt **OpenCode Free & kleine Modelle** und beschreibt kostenlose Modelle, Modellquellen-Presets, gemeinsames Free-Kontingent und kompaktere Prompts.

## Teständerungen gegenüber V1.2

- `backend/tests/test_api.py` erwartet API-Version `1.3.0` und Workbench-Stage `13`; `test_open_pilot_and_opencode_console_routes` prüft „Pilot öffnen“ und die OpenCode-Konsole.
- `backend/tests/test_api.py` und `backend/tests/test_api_v11.py` decken die Quellenplanung und die unveränderten API-Funktionen ab.
- `tests/test_opencode.py` prüft Katalogfilter, Erlaubnisliste, gemeinsames Tageslimit ohne Free-Modellwechsel, Fehler ohne Fallback, Studio-Fassade, OpenAI-Brücke und Dienstdatei.
- `tests/test_routing.py` prüft Quellen-Reihenfolgen, Präfixe, Quota-Sperre, API-Modell-Fallback, Preset-Validierung und Quota-Ausweichpfade.
- `tests/test_preflight.py::test_session_can_rerun_preflight_from_stored_candidates` prüft den erneuten Vorabcheck mit gespeicherten Kandidaten und Auswertungsmodell.
- Die bisherigen V1.2-Tests für Index, Plan-Diff, Graph, Anwendungsabnahme, Benchmarks, Recherche, Umgebungen, Export/Import, Logrotation, SSE, Sandbox und Asset-Cache bleiben aktiv.
- `npm run build` prüft weiterhin TypeScript und den Produktionsbuild; die einzige große Chunk-Warnung betrifft den bewusst verzögert geladenen CodeMirror-Editor.

## Prüfgrenzen

- Die automatisierten Tests simulieren LM-Studio-, Docker- und Modellantworten. Reale Modellqualität, VRAM-Werte, Tokens/s und Quantisierungen müssen auf der Zielhardware gemessen werden. Die OpenCode-Tests verwenden Fakes; ein realer Free-Lauf ist vom Tageslimit abhängig.
- Ein echter Docker-Build, ein realer Aider-Lauf und ein signierter Installer wurden in dieser Umgebung nicht ausgeführt. Der Installer ist vorbereitet; ohne Zertifikat bleibt er unsigniert.
- Die Browser-Abnahme nutzt einen installierten Chrome/Edge im Headless-Modus. Ohne Browser schlägt ein deklariertes Browser-Szenario nachvollziehbar fehl.
- Tray und Browser-App-Fenster werden nur gestartet, wenn die jeweiligen optionalen Komponenten beziehungsweise Browser vorhanden sind.
- Ein visueller Screenshot ersetzt keine vollständige Bedienabnahme aller Tutorial-Schritte auf jedem Zielsystem.
