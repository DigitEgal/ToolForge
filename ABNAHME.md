# Anforderungsabgleich V1.4

Basis: ToolForge V1.3 einschließlich aller Regressionen aus 0.1 bis V1.3. Geprüft wurde der Code-, API- und UI-Stand. Reale GPU-, Docker-, Aider-, OpenCode-, Tray- und Signaturprüfungen bleiben im Testbericht gesondert abgegrenzt; die automatisierten Tests verwenden dafür isolierte Projekte und simulierte Schnittstellen.

Historische Abgleiche: [0.8](docs/archiv/ABNAHME_V08.md) · [V1.0](docs/archiv/ABNAHME_V10.md) · [V1.1](docs/archiv/ABNAHME_V11.md)

## V1.4-Pflichtpunkte

| ID | Anforderung | Umsetzung | Beleg |
|---|---|---|---|
| V14-1 | Steckengebliebene Aufgaben an weitere Modelle übergeben | `Engine` erkennt wiederholte Fehlversuche, Hänger, Kontextlimits und blockiert zurückgelassene Aufgaben. Die geordnete `handoff_models`-Liste wird sequenziell versucht; der aktive Adapter wird für den Versuch getauscht und nach Erfolg wiederhergestellt. Jeder Versuch wird pro Aufgabe protokolliert. | `tests/test_v14.py`, `toolforge_pilot/core.py`, `toolforge_pilot/collaboration.py`, Quellprüfung. |
| V14-2 | Ergebnisse durch andere Modelle unabhängig prüfen | Nach bestandener Aufgabenprüfung und als abschließendes Projektgate bewerten ein oder mehrere Prüfer das Ergebnis. Ersteller einer Aufgabe und aktives Hauptmodell sind ausgeschlossen. Mindestzustimmungen, strenge Ablehnung und Reparatur nach Ablehnung sind konfigurierbar. | `tests/test_v14.py::test_independent_review_excludes_creator_and_gates_completion`, `tests/test_v14.py::test_review_rejection_triggers_repair_then_approval`, Quellprüfung. |
| V14-3 | Übergabe- und Prüferauswahl im Vorabcheck und zur Laufzeit konfigurierbar | `PreflightPanel` und `CollaborationPanel` bieten je einen `RoleEditor` mit Hinzufügen, Entfernen und Verschieben. Rollen werden als `Quelle::Modell` gespeichert, gegen den aktuellen Modellbestand validiert und über `POST /settings` sowie `/runtime/options` auch während eines Laufs übernommen. | `backend/tests/test_api_v14.py::test_collaboration_roles_use_qualified_keys_and_runtime_updates`, `backend/tests/test_api_v14.py::test_preflight_validates_role_models_against_live_inventory`, UI-Quellprüfung. |
| V14-4 | Modelle für den Vorabcheck auswählbar und Vorabcheck überspringbar | Kandidaten und Auswertungsmodell bleiben einzeln wählbar; `skip_preflight` erlaubt Planung und Start ohne bestätigten Vergleich. Ein späterer Vorabcheck bleibt möglich, Empfehlungen werden weiterhin nur nach Übernahme aktiv. | `backend/tests/test_api_v14.py::test_preflight_options_expose_role_picker_and_skip_flag`, Quellprüfung. |
| V14-5 | Oberfläche per EN\|DE-Umschalter vollständig übersetzen | `I18nProvider`/`useI18n`/`tr` übersetzen App, Cockpit, Vorabcheck, Modellquellen, Analyse, Entwicklung, Hilfe und Tutorials. Der Umschalter steht neben Ton und Design; die Auswahl liegt unter `localStorage`-Schlüssel `toolforge-language`. | `npm run build`, Quellprüfung, Screenshot-Prüfung. |
| V14-6 | README und Schnellstart zweisprachig mit Sprachlinks | `README.md` (englischer Standard) und `README.de.md` verlinken einander am Anfang; `QUICKSTART.txt` und `SCHNELLSTART.txt` ebenso. Beide READMEs führen V1.4, Funktionen, Installation, Sicherheit, Grenzen und Versionsgeschichte. | Quellprüfung der Dateien. |
| V14-7 | Hilfe, Tutorials und nutzernahe Dokumente in beiden Sprachen | `help/en/` enthält vier englische Dokumente; `/api/help?lang=` und der Hilfechat liefern die gewählte Sprache. Vier Tutorials (`main`, `pilot`, `collaboration`, `developer`) decken UI, Cockpit, Übergabe & Prüfung sowie Entwicklung ab und sind vollständig lokalisiert. | `backend/assistance.py`, `frontend/src/Tutorial.tsx`, Quellprüfung. |
| V14-8 | Docker-Build-/Update-Fehler „Auftrag: failed“ beheben | `sandbox_status` prüft Docker-CLI und Linux-Daemon, `require_daemon` bricht Build-, Netzwerk- und Paketaufträge synchron mit HTTP 422 und klarer Meldung ab. Statusfelder und Frontend-Polling zeigen Daemon-Fehler sofort; ein fehlender Daemon führt nicht mehr zu einem hängenden Hintergrundauftrag. | `backend/tests/test_api_v14.py::test_sandbox_build_rejects_unreachable_daemon_immediately`, `backend/tests/test_api_v14.py::test_sandbox_status_distinguishes_cli_and_daemon`, Quellprüfung. |
| V14-9 | Version im gesamten Projekt auf V1.4 anheben | FastAPI und `/api/workbench` melden `1.4.0`, die Workbench-Stage ist `14`. Frontend-Paket und Lockfile tragen `1.4.0`; Sidebar, Roadmap, Startbanner, Setup-Ausgabe, Hilfe, Installer, Buildskript und Dokumentation nennen V1.4 beziehungsweise vierzehn Etappen. | API-Test, Quellprüfung, `npm run build`. |
| V14-10 | Alle bisherigen Funktionen weiter prüfen | Die vollständige V1.3-Suite bleibt erhalten; hinzugekommen sind Tests für Handoff-Reihenfolge, Ersteller-Ausschluss, Ablehnungsreparatur, Rollenvalidierung, übersprungenen Vorabcheck, Collaboration-API, Docker-Daemon-Prüfung und das Projektgedächtnis. | [TESTBERICHT.md](TESTBERICHT.md), vollständiger Testlauf (189 bestanden). |
| V14-11 | Modellunabhängiges Projektgedächtnis über Durchgänge und Modellwechsel hinweg | `ProjectMemory` speichert verdichtete Fehler, Reparaturen, Übergaben, Prüfablehnungen, Entscheidungen, Installationslösungen und Ergebnisse in der bestehenden Projekt-Zustandsdatenbank. Einträge werden dedupliziert, redigiert und auf 500 Datensätze begrenzt; ein kompakter Auszug fließt mit festem Zeichenlimit in Planung und Aufgabenprompts ein. Unter Analyse & Betrieb → Projektgedächtnis sind Einträge einsehbar, ergänzbar, abschaltbar und löschbar. | `tests/test_memory.py`, `backend/tests/test_api_v14.py::test_project_memory_lists_notes_clears_and_can_be_disabled`, Quellprüfung, `npm run build`. |

## V1.3-Pflichtpunkte (Funktionsbasis)

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
- API: `1.4.0`; Workbench: Stage `14`; Frontend: `1.4.0`; Installer-Definition: `1.4`.
- Die vierzehnte Etappe heißt **Übergabe & unabhängige Prüfung** und beschreibt Mehrmodell-Übergabe, Ersteller-Ausschluss, Prüferlisten, optionalen Vorabcheck, EN/DE-Oberfläche und den diagnostizierten Docker-Build.
- Die dreizehnte Etappe bleibt als Funktionsbasis dokumentiert: **OpenCode Free & kleine Modelle**.

## Teständerungen gegenüber V1.3

- Neu: `tests/test_v14.py` prüft Handoff-Reihenfolge und Modellwechsel, Ersteller-Ausschluss, Ablehnungsreparatur, Rollenbereinigung und das abschließende Prüfgate.
- Neu: `backend/tests/test_api_v14.py` prüft Collaboration-Modelle und -Einstellungen, Vorabcheck-Rollen samt Live-Validierung, übersprungenen Vorabcheck, Docker-Daemon-Pflicht und Daemon-Status.
- `backend/tests/test_api.py` erwartet API-Version `1.4.0` und Workbench-Stage `14`.
- `tests/test_v08.py` prüft weiterhin die Hilfedokumente; `help/en/` wird über `help_documents('en')` abgedeckt.
- Die bisherigen V1.3-Tests für OpenCode, Routing, Quell-Presets, gemeinsames Quota, kleinen Modus und wiederholten Vorabcheck bleiben aktiv.
- `npm run build` prüft weiterhin TypeScript und den Produktionsbuild; die einzige große Chunk-Warnung betrifft den bewusst verzögert geladenen CodeMirror-Editor.

## Prüfgrenzen

- Die automatisierten Tests simulieren LM-Studio-, Docker-, OpenCode- und Modellantworten. Reale Modellqualität, VRAM-Werte, Tokens/s und Quantisierungen müssen auf der Zielhardware gemessen werden. Die OpenCode-Tests verwenden Fakes; ein realer Free-Lauf ist vom Tageslimit abhängig.
- Ein echter Docker-Build, ein realer Aider-Lauf und ein signierter Installer wurden in dieser Umgebung nicht ausgeführt. Die Docker-Daemon-Prüfung ist mit simulierten Statusantworten abgedeckt; Docker Desktop lief in der Testumgebung nicht. Der Installer ist vorbereitet; ohne Zertifikat bleibt er unsigniert.
- Die Browser-Abnahme nutzt einen installierten Chrome/Edge im Headless-Modus. Ohne Browser schlägt ein deklariertes Browser-Szenario nachvollziehbar fehl.
- Tray und Browser-App-Fenster werden nur gestartet, wenn die jeweiligen optionalen Komponenten beziehungsweise Browser vorhanden sind.
- Ein visueller Screenshot ersetzt keine vollständige Bedienabnahme aller Tutorial-Schritte auf jedem Zielsystem.
- Die EN/DE-Übersetzung ist quellgeprüft und gebaut, aber nicht mit muttersprachlichem Review aller Zeichenketten abgenommen.
