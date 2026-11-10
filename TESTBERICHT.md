# Testbericht ToolForge Pilot V1.2

> **Aktueller Bericht mit vollständiger Versionshistorie.** Dieser Bericht ersetzt die früheren Einzeldateien `TESTBERICHT_V01-06.md`, `TESTBERICHT_V07.md`, `TESTBERICHT_V08.md`, `TESTBERICHT_V10.md` und `TESTBERICHT_V11.md`. Die Abschnitte ab **Archiv V1.1** dokumentieren die damaligen Prüfstände unverändert als historische Nachweise.

## Aktueller Stand V1.2

Prüfdatum: 10.11.2026. Basis: ToolForge V1.1 einschließlich aller bisherigen Regressionen. Die Prüfung erfolgte mit der ausgelieferten Controller-Umgebung `.venv` und dem gebauten Frontend.

### Automatisierte Tests

```text
.venv\Scripts\python.exe -m pytest -q tests backend/tests
150 passed, 1 warning in 133.27s (0:02:13)
```

Die Warnung betrifft die bekannte Starlette-Deprecation im TestClient (`httpx` statt `httpx2`); sie ist kein Fehlschlag. Gegenüber V1.1 ist ein Test hinzugekommen:

- `backend/tests/test_api.py::test_version_and_static_cache_headers` prüft die FastAPI-Version `1.2.0`, `index.html` mit `Cache-Control: no-cache` und ein gehashtes Asset unter `/assets/` mit `public, max-age=31536000, immutable`.
- `backend/tests/test_api.py::test_health_and_empty` erwartet jetzt Workbench-Version `1.2.0` und Stage `12`.
- Alle V1.1-Prüfungen für Index, Plan-Diff, Aufgaben-Graph, Anwendungsabnahme, Benchmarks, Recherche, Umgebungen, Presets, Export/Import, Logrotation, SSE und Sandbox bleiben unverändert aktiv.
- Die vollständigen V1.0-, 0.8- und früheren Regressionen sind in derselben Suite enthalten.

### Branding und Oberfläche

- `frontend/src/BrandMark.tsx` bindet `frontend/logos/LogoV7_OnlyLOGO.png` als Tool-Logo ein. Sidebar, Abschlussbildschirm und Tutorial-Willkommen verwenden denselben Wrapper.
- `frontend/src/DigitEgalLogo.tsx` zeigt „by“ plus `frontend/logos/LogoV6_textONLY.png`. Die Wortmarke hat 20 px Bildhöhe (Sidebar 18 px), das „by“ 13 px (Sidebar 12 px). Der Eintrag ist in der Seitenleiste horizontal zentriert. Die Breite folgt automatisch dem Seitenverhältnis von 2657 : 748 (rund 3,55 : 1).
- Eine kleine dunkle Trägerfläche hinter der V6-Wortmarke hält die weißen Bildbuchstaben auch im hellen Design lesbar.
- Unten links bleibt genau ein externer Link auf <https://digitegal.de>.
- Headless-Chrome-Screenshots bei 1440 × 1000 in Dark und Light geprüft: Logo, Sidebar, zentrierte Wortmarke und Willkommensdialog werden korrekt gerendert. Die Wortmarke ist gut lesbar und gegenüber dem ersten Entwurf deutlich vergrößert.

### Frontend-Build und Ladeverhalten

```text
npm run build
toolforge-workbench@1.2.0
tsc --noEmit
vite build
```

Ergebnis: TypeScript-Prüfung und Produktionsbuild erfolgreich.

| Datei | Größe | gzip |
|---|---:|---:|
| `index.html` | 0,52 kB | 0,34 kB |
| CSS `index-ZEr_ceTT.css` | 32,68 kB | 7,55 kB |
| Initiales JavaScript `index-CBgv7wEd.js` | **261,38 kB** | **80,99 kB** |
| `PilotPanel` | 34,48 kB | 10,16 kB |
| `AdvancedPanel` | 22,49 kB | 5,91 kB |
| `DeveloperPanel` | 16,31 kB | 5,45 kB |
| `HelpPanel` | 3,48 kB | 1,46 kB |
| `ProjectManager` | 3,73 kB | 1,58 kB |
| `ImprovementPanel` | 5,14 kB | 2,09 kB |
| `CodeEditor` (CodeMirror, bedarfsgeladen) | 611,61 kB | 214,21 kB |
| `LogoV7_OnlyLOGO.png` | 48,48 kB | – |
| `LogoV6_textONLY.png` | 61,38 kB | – |

Der initiale JavaScript-Block sank von 954,99 kB (V1.1) auf 261,38 kB, gzip von 316,35 kB auf 80,99 kB. Cockpit, Hilfe, Projektverwaltung, Analyse, Entwicklungsbereich und Codeeditor werden per `React.lazy`/`Suspense` erst beim Öffnen geladen. Die einzige verbleibende Chunk-Warnung betrifft den bewusst verzögert geladenen CodeMirror-Editor und ist kein Buildfehler.

### Lokaler API-, SSE- und Cache-Smoke-Test

Die V1.2-Anwendung wurde mit der ausgelieferten `.venv` als echter Uvicorn-Server auf Port `8123` gestartet (temporäre Datenbank, temporärer Projektordner). Port `8000` war durch eine bereits laufende V1.0-Instanz belegt und wurde nicht verändert.

| Prüfung | Ergebnis |
|---|---|
| `/api/workbench` | Version `1.2.0`, Stage `12`, Pilot enthalten |
| Projekt anlegen und Ordner verbinden | erfolgreich |
| `/pilot/demo` | Planversion 1 aktiv |
| `/pilot/index` | Index aktuell, 2 Dateien |
| `/pilot/analysis` | 100 % Abdeckung, Manifest und Chunks vorhanden |
| `/pilot` Snapshot | enthält `index`, `graph`, `scenarios`, `benchmark`, `research`, `operations`, `environment` |
| Aufgaben-Graph | 3 Aufgaben erkannt |
| `/pilot/export` | ZIP mit `toolforge-transfer.json`, `README.md` und `main.py`; Manifestschlüssel `created_at`, `files`, `name`, `schema_version`, `source` |
| Session-SSE | erster Frame `event: snapshot` |
| Globales SSE | erster Frame `event: questions` |
| `/` | HTTP 200, ToolForge-Titel, `Cache-Control: no-cache` |
| Gehashtes Asset `/assets/index-CBgv7wEd.js` | HTTP 200, `Cache-Control: public, max-age=31536000, immutable` |

Damit sind Start, Datenbankanlage, Index, Analyse, Plan, Graph, Export, beide SSE-Kanäle und der neue Asset-Cache gegen einen echten lokalen Server nachgewiesen.

### V1.2-Nachweise im Einzelnen

| Punkt | Beleg | Grenze |
|---|---|---|
| V7-Tool-Logo | Quellprüfung `BrandMark.tsx`, TypeScript-/Vite-Build, Screenshot in Dark und Light | Keine vollständige Bedienabnahme aller Tutorial-Schritte. |
| V6-Wortmarke | Bildmaße 2657 × 748, CSS-Höhen 20/18 px, zentrierter Sidebar-Eintrag, Kontrastträger, ein externer Link | Keine Messung der subjektiven Lesbarkeit auf jedem Zielmonitor. |
| Testberichte konsolidiert | Diese Datei enthält V1.2 und die Archivstände 0.1–0.6, 0.7, 0.8, V1.0, V1.1 | Historische Einzeldateien und Umgebungsdateien wurden entfernt. |
| Code-Splitting | Build-Ausgabe: Initialblock 261,38 kB statt 954,99 kB; Editor separat | Kein Laborvergleich der Ladezeit auf langsamen Zielsystemen. |
| Asset-Cache | Automatisierter Test und realer Smoke-Test bestätigen `immutable` für `/assets/`, `no-cache` für `/` | Kein Test über einen längeren Browser-Cache-Zyklus. |
| Version und Stage | API `1.2.0`, Workbench Stage `12`, Frontend-Paket `1.2.0`, Installer `1.2` | Signierter Installer nicht gebaut. |
| Bisherige Funktionen | Vollständige Suite: **150 bestanden**, eine bekannte Warnung | Reale Modell-, Docker-, Aider-, Tray- und Signaturläufe bleiben offen. |

### Umgebung

- Controller: Python 3.11.9, Windows 10, Node.js 26.13.0, npm 11.20.0.
- Pakete: pytest 9.2.0, FastAPI 0.162.2, httpx 0.28.1, Uvicorn 0.54.0, Pydantic 2.14.3, Starlette 1.10.0.
- Aider im separaten `.aider-venv`: 0.86.2, gepinnt über `requirements-aider.txt`.
- Docker-CLI: 29.9.2; Docker Desktop Linux-Engine im Testzeitpunkt nicht erreichbar.
- Browser: Chrome 157.0.8103.50; Headless-Screenshots und der V1.1-Browserlauf waren erfolgreich.
- Installer: Inno Setup und Windows SDK/`signtool` fehlen; die Definition ist vorhanden, aber nicht als EXE gebaut.

### Nicht als real getestet

- GPU-/VRAM-Messung mit einem geladenen LM-Studio-Modell und reale Modellqualität.
- Docker-Image-Build, Container-Paketinstallation und Netzwerkbetrieb mit laufendem Docker-Daemon.
- Signierter Windows-Installer und eine vollständige Installations-/Deinstallationsrunde.
- Tray-Symbol mit installiertem `pystray`/Pillow.
- Aider-Ausführung gegen ein reales Modell.
- Dauerhafter Browser-Reconnect der SSE-Kanäle über Stunden.

Diese Punkte sind im Code vorbereitet und durch simulierte beziehungsweise Validierungstests abgesichert. Sie ersetzen keine Zielsystemabnahme.

---

# Archiv V1.1

Prüfdatum: 10.11.2026. Basis: ToolForge V1.0 einschließlich aller bisherigen Regressionen. Die Prüfung erfolgte mit der ausgelieferten Controller-Umgebung `.venv` und dem gebauten Frontend.

## Automatisierte Tests

```text
.venv\Scripts\python.exe -m pytest -q tests backend/tests
149 passed, 1 warning in 131.33s (0:02:11)
```

Die Warnung betrifft eine Starlette-Deprecation im TestClient (`httpx` statt `httpx2`); sie ist kein Fehlschlag. Gegenüber V1.0 sind 17 Tests hinzugekommen beziehungsweise wurden angepasst:

- `tests/test_v11.py`: Index, Plan-Diff und Sicherung, Aufgaben-Graph und Dateifreigaben, Szenarien und Testreview, Benchmarks, Recherche, Umgebungen/Presets, Projekt-Export/Import, Logrotation, EventHub und Sandbox-Ressourcen.
- `backend/tests/test_api_v11.py`: Index/Analyse, Planvorschau und Bestätigung, Graph, Umgebungssperre, Betriebsstatus, Presets, Projekt-Export, Sandbox-Fallback und SSE-Routen.
- `backend/tests/test_api.py`: Versionserwartung `1.1.0`.
- `tests/test_v08.py`: Aider-Setup prüft jetzt die Verwendung der gepinnten `requirements-aider.txt`.
- `toolforge_pilot/core.py`: Windows-Prozessbaumpüfung erhielt einen `taskkill /T`-Fallback gegen das kurze Zeitfenster vor der Job-Objekt-Zuordnung.

## Frontend

```text
npm run build
toolforge-workbench@1.1.0
tsc --noEmit
vite build
```

Ergebnis: TypeScript-Prüfung und Produktionsbuild erfolgreich.

- `index.html`: 0,52 kB
- CSS: 32,58 kB (7,53 kB gzip)
- JavaScript: 954,99 kB (316,35 kB gzip)

Der Bundler meldet weiterhin, dass das JavaScript-Bundle 500 kB überschreitet. Das ist eine bekannte Optimierungsaufgabe, kein Buildfehler. Der Build enthält das globale SSE-Fragenbanner, die Plan-Vorschau und den Bereich **Analyse & Betrieb**.

## Lokaler API- und SSE-Smoke-Test

Die V1.1-Anwendung wurde mit der ausgelieferten `.venv` als echter Uvicorn-Server auf Port `8123` gestartet (temporäre Datenbank, temporärer Projektordner). Port `8000` war durch eine bereits laufende V1.0-Instanz belegt und wurde nicht verändert.

| Prüfung | Ergebnis |
|---|---|
| `/api/workbench` | Version `1.1.0`, Stage `11` |
| Projekt anlegen und Ordner verbinden | erfolgreich |
| `/pilot/demo` | Planversion 1 aktiv |
| `/pilot/index` | Index aktuell, 2 Dateien |
| `/pilot/analysis` | 100 % Abdeckung im Testprojekt, Manifest und Chunks vorhanden |
| `/pilot` Snapshot | enthält `index`, `graph`, `scenarios`, `benchmark`, `research`, `operations`, `environment` |
| Aufgaben-Graph | 3 Aufgaben erkannt |
| `/pilot/export` | ZIP mit `toolforge-transfer.json` und `main.py` |
| Session-SSE | erster Frame `event: snapshot` |
| Globales SSE | erster Frame `event: questions` |

Damit sind Start, Datenbankanlage, Index, Analyse, Plan, Graph, Export und beide SSE-Kanäle gegen einen echten lokalen Server nachgewiesen.

## Reale und simulierte Prüfungen im Einzelnen

| Punkt | Beleg | Grenze |
|---|---|---|
| Inkrementeller Index | Automatisierte Index-/API-Tests und realer Smoke-Test: 2 Dateien indexiert, 100 % Analyseabdeckung | Kein Projekt mit mehreren tausend Dateien in dieser Umgebung. |
| Empirische Messreihe | `tests/test_v11.py`: 2 Kontexte × 2 Wiederholungen, Qualitätsstreuung, Tokens/s, VRAM-Spitze, Cache, Entladen | Kein realer LM-Studio-Lauf und keine echte GPU-Messung. |
| Plan-Diff/-Vorschau | API-Test: Hinzufügen, Versionswechsel, Risiko `high`, 422 ohne Bestätigung, Erfolg mit `confirm=true`; Plan-Sicherung | Keine visuelle Browserabnahme der Vorschau. |
| Anwendungsabnahme | CLI-Szenariotest; realer Headless-Chrome-Lauf gegen einen lokalen HTTP-Server: `passed=true`; Teständerungs-Diff und Review-Test | Kein echter externer Browser-/Netzwerkdienst. |
| Reproduzierbare Umgebung | Lockfile-Test, Umgebungssperre mit Controller-/Aider-Pins und Docker-Feld, Preset-Export/-Import | Kein realer Aider- und Docker-Lauf. |
| Aufgaben-Graph | Tests für parallele Freigabe, abhängige gemeinsame Datei, Prioritätsübernahme und kritischen Pfad; realer Snapshot mit 3 Aufgaben | Keine große Graph-Visualisierung im Browser geprüft. |
| SSE/Aktualisierung | EventHub-Test mit Session-/Global-Kanälen; realer SSE-Smoke-Test beider Endpunkte; Route-Registrierung im API-Test | Dauerhafter Browser-Reconnect wurde nicht über Stunden geprüft. |
| Recherche | Domainfilter, Ablehnung von Loopback/IP-Literalen, Cache-Hit, Belegtexte und Journal | Kein echter DuckDuckGo-/Netzwerklauf in der automatisierten Suite. |
| Betrieb/Wiederherstellung | ZIP-Export/-Import mit Manifest und Pfadprüfung, Logrotation, Plan-Sicherungen, Installer-/Tray-Status | Inno Setup und `signtool` sind auf dieser Maschine nicht installiert; der Installer wurde daher nicht kompiliert oder signiert. |
| Sandbox-Komfort | Ressourcen-/Portvalidierung, Docker-Kommandoaufbau, Image-/Netzwerk-/Paketfunktionen, graceful Fallback ohne Docker | Docker Desktop ist installiert, der Linux-Daemon lief nicht; kein realer Container-Build. |

## Umgebung

- Controller: Python 3.11.9, FastAPI 0.162.2, Uvicorn 0.54.0, Pydantic 2.14.3, Starlette 1.10.0, pytest 9.2.0.
- Node.js 26.13.0, npm 11.20.0.
- Aider im separaten `.aider-venv`: 0.86.2.
- Docker-CLI: 29.9.2; Docker Desktop Linux-Engine im Testzeitpunkt nicht erreichbar.
- Chrome ist installiert; der Headless-Browserlauf war erfolgreich.
- Inno Setup und Windows SDK/`signtool` fehlen; die Installer-Definition ist vorhanden, aber nicht als EXE gebaut.

## Nicht als real getestet

- GPU-/VRAM-Messung mit einem geladenen LM-Studio-Modell.
- Docker-Image-Build, Container-Paketinstallation und Netzwerkbetrieb mit laufendem Docker-Daemon.
- Signierter Windows-Installer und eine vollständige Installations-/Deinstallationsrunde.
- Tray-Symbol mit installiertem `pystray`/Pillow.
- Aider-Ausführung gegen ein reales Modell.

Diese Punkte sind im Code vorbereitet und durch simulierte beziehungsweise Validierungstests abgesichert. Sie ersetzen keine Zielsystemabnahme.

---

# Archiv V1.0

Prüfdatum: 10.11.2026. Basis: bereitgestellte Version 0.8, vollständig erhalten und um die V1.0-Pflichtpunkte sowie die fehlenden v0.9-Funktionen erweitert.

## Automatisierte Tests

```text
python -m pytest -q tests backend/tests
132 passed in 99.96s
```

Keine fehlgeschlagenen Tests. Die Suite umfasst alle bisherigen Prüfungen und neue Tests für Projektgruppen. Zusätzlich prüft der API-Test die Versionsausgabe `1.0.0` und die Migration bestehender Datenbanken auf `group_id` sowie `PRAGMA user_version=4`.

Enthalten sind unter anderem:

- Pillow-Quelltext-Buildfehler, PyPI-Wheel-Auswahl, Wiederholungsbefehl und Plan-Neuversionierung.
- Kontexttoleranz: 20.224 statt 20.000 geladene Tokens werden übernommen, 4.096 statt 20.000 abgelehnt.
- Drei Kandidaten ergeben sechs Proben; sieben Kandidaten werden abgewiesen.
- Projektgruppen-CRUD, Projektzuordnung, Umbenennen, Löschen mit erhaltener Projektliste und Migrationspfad.
- Alle Regressionen aus 0.1 bis 0.8: Engine, Fortschritt, Rückfragen, Erweiterungen, Websuche, Diagnose, Installationen, Editor, Git, Workflows, Sandbox-Kommandos und Hilfe.

## Frontend

```text
npm --prefix frontend run build
toolforge-workbench@1.0.0
tsc --noEmit
vite build
```

Ergebnis: TypeScript-Prüfung und Produktionsbuild erfolgreich. Die gebauten Dateien liegen unter `frontend/dist`:

- `index.html`: 0,52 kB
- CSS: 29,13 kB (6,90 kB gzip)
- JavaScript: 926,66 kB (309,49 kB gzip)

Der Bundler meldet lediglich, dass das JavaScript-Bundle 500 kB überschreitet. Das ist eine Optimierungsmöglichkeit, kein Buildfehler. Der Build enthält die V1.0-Oberfläche mit Projektgruppen, Listenansicht, Tutorials, Abschluss-Overlay und DigitEgal-Branding.

## Lokaler API-Smoke-Test

Die Anwendung wurde mit `python start_toolforge.py` als echter lokaler Server gestartet (`TOOLFORGE_NO_BROWSER=1`, temporäre Datenbank). Geprüft wurden:

| Prüfung | Ergebnis |
|---|---|
| `/api/health` | `ok` |
| `/api/workbench` | Version `1.0.0`, Stage 10 |
| `/api/groups` anlegen | Name getrimmt, Projektanzahl 0 |
| Projekt einer Gruppe zuordnen | `group_id` gesetzt, Gruppenanzahl 1 |
| Gruppe löschen | `removed=true`, ein Projekt „Ohne Gruppe“, Projekt bleibt erhalten |
| `/` | HTTP 200, ausgeliefertes Frontend enthält den ToolForge-Titel |
| `/api/shutdown` | `stopping`; Prozess beendet, Port 8000 freigegeben |
| Temporäre Daten | anschließend entfernt |

Damit sind Start, Datenbankmigration, Gruppen-API, statische Auslieferung und sauberer Shutdown des Servers lokal nachgewiesen. Ein Browser wurde dabei nicht geöffnet.

## V1.0-Nachweise im Einzelnen

| Punkt | Beleg | Grenze |
|---|---|---|
| Pillow-Selbstreparatur | `tests/test_improvements.py`: Buildfehler, Wheel-Auswahl, Retry, `last_resolution`, Plan-Version | Kein echter PyPI-/Netzwerklauf mit einer realen Pillow-Installation. |
| Browser schließen | Quellprüfung `start_toolforge.py` und `App.tsx`; Shutdown-Hook im Smoke-Test | Kein echter Chrome-/Edge-App-Fensterlauf unter Windows. |
| Ein-Klick-Ablauf | `PreflightPanel.autopilot`; TypeScript-/Vite-Build | Kein realer LM-Studio-Lauf. |
| Kontexttoleranz | `tests/test_preflight.py` | Kein echtes LM-Studio-Modell. |
| 3–6 Kandidaten | Backend-Test und UI-Auswahl; Build | Keine Messung mit sechs realen Modellen. |
| Deinstallation | Quellprüfung; Smoke-Test in einer temporären Kopie: eigene Verzeichnisse entfernt, Nutzerprojekt und Daten mit `--keep-data` erhalten | Kein Lauf gegen ein produktives Benutzerprofil. |
| Gruppen/Listenansicht | API-Test, Migrationstest, Frontend-Build, API-Smoke-Test | Keine Browserbedienung der Kachel-/Listenumschaltung. |
| Tutorials | `Tutorial.tsx`, `data-tour`-Selektoren, Hilfe-Buttons, Build | Keine visuelle Browserabnahme der Spotlight-Positionen. |

## Umgebung

- Controller: Python 3.11.9, Windows 10, Node.js 26.13.0, npm 11.20.0.
- Pakete: pytest 9.2.0, FastAPI 0.128.8, httpx 0.28.1, Uvicorn 0.54.0, Pydantic 2.12.5, Starlette 0.52.1.
- LM Studio, Docker, echte Aider-Läufe und Browser-Shutdown wurden nicht ausgeführt; die automatisierten Tests verwenden simulierte Modell- und Docker-Antworten.

## Nicht als real getestet

- Windows-CMD-/pythonw-Start, Taskmanager-Fälle und das tatsächliche Schließen eines Chrome-/Edge-App-Fensters.
- Reale Aider-Entwicklungsläufe mit Nutzerprojekten und lokalem LM Studio.
- Modellqualität, VRAM-Verbrauch, GPU-Freigabe und Quantisierungsvergleich.
- Echter Docker-Imagebau, Containerkommunikation und Docker Desktop unter Windows. Befehlsbildung, Netzwerkoptionen und Cleanup sind simuliert geprüft.
- Live-Verfügbarkeit von DuckDuckGo.
- Interaktive Bedienung der Tutorials, Projektgruppen und Listenansicht in einem echten Browser.
- Löschen eines produktiven `%APPDATA%\ToolForgePilot`-Ordners. Der Ablauf wurde nur in einer temporären Kopie geprüft.

## Empfohlener kurzer Zielsystemtest

1. In einem neuen Ordner `Setup_ToolForge.cmd` ausführen; die Aider-Prüfung muss erfolgreich enden.
2. Workbench starten, Willkommensdialog und UI-Tutorial durchgehen, Projekt anlegen und eine Projektgruppe testen.
3. Kachel- und Listenansicht umschalten, Projekt verschieben, Gruppe löschen und prüfen, dass das Projekt erhalten bleibt.
4. Vorabcheck mit drei kleinen installierten Modellen durchführen; den geladenen Kontext in LM Studio mit dem übernommenen Budget vergleichen.
5. Den Ein-Klick-Ablauf mit einer kleinen Aufgabe testen und im Entwicklungsbereich das Entwickler-Tutorial öffnen.
6. „ToolForge beenden“ testen: Das von ToolForge gestartete App-Fenster muss schließen; bei einem anderen Browser muss der Abschlussbildschirm erscheinen.
7. Optional einen Pillow-Buildfehler provozieren und prüfen, dass eine Wheel-Version gewählt und der Plan neu versioniert wird.
8. `Deinstallieren_ToolForge.cmd --keep-data` in einer Kopie testen; eigene Projektordner müssen unverändert bleiben.

---

# Archiv 0.8

Prüfdatum: 09.11.2026. Basis: bereitgestellte Version 0.7, vollständig erhalten und erweitert.

## Automatisierte Tests

`python -m pytest -q tests backend/tests`: **125 bestanden**, eine Deprecation-Warnung aus Starlette/FastAPI zur TestClient-httpx-Anbindung. Keine fehlgeschlagenen Tests.

Enthalten sind alle bisherigen Tests sowie 21 neue Tests für gezielte Invalidierung, Fortschrittserhalt, Planverträge, unabhängige Aufgaben, Reparaturstrategien, Websuche-Opt-in/Journal, Geheimnisredaktion, Pausewiderruf, einmalige Werkzeuginstallation, additive Erweiterungen, Fehlererhalt, veraltete Vorschläge, Dockerargumente/-Cleanup, Hilfeabdeckung, Laufzeitoptionen, Python-Escapes im Container, Aider-Setup Modellwiederherstellung bei Assistenzfehlern und parallele Nicht-Modelljobs trotz belegtem Modell-Lock.

Ein früherer Test zur sofortigen Aufteilung nach GUARD_REPEAT wurde auf GUARD_CONTEXT umgestellt: Aufteilung nach einem echten Kontextlimit bleibt erforderlich; pauschale Aufteilung bei Wiederholung widerspricht der neuen Anforderung P6. Die neue Strategieprüfung testet ausdrücklich, dass GUARD_REPEAT nicht automatisch aufteilt.

## Frontend

`npm --prefix frontend run build`: TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich. Hinweis des Bundlers: Das JavaScript-Bundle überschreitet 500 kB. Dies ist eine Optimierungsmöglichkeit, kein Buildfehler.

Chromium-Bedienprüfung mit echter lokaler ToolForge-API und simuliertem LM-Studio-Server:

- Projekt anlegen/verbinden und Einstellungen speichern.
- Textuelle Erweiterung einplanen.
- KI-Verbesserungsvorschläge anfordern, auswählen und einplanen.
- Alle sechs Entwicklungstabs in der verlangten Reihenfolge öffnen.
- Hilfe öffnen, Modell wählen und eine dokumentgestützte Antwort anzeigen.
- Modell-Vorabcheck mit drei Kandidaten und zwei Temperaturen: sechs Proben, Auswertung, Übernahme und anschließende Planerstellung.
- Desktopansicht 1440×1000 und schmale Ansicht 390×844; kein horizontaler Dokumentüberlauf, keine JavaScript-Seitenfehler im getesteten Ablauf.
- Screenshots intern auf Darstellung geprüft; Abstände und Buttonumbruch korrigiert.

Die Testantworten belegen die technische Integration, nicht die Qualität realer Modelle. Tonsteuerung wurde kompiliert und visuell geprüft; der tatsächlich hörbare Ton auf der Zielmaschine ist nicht nachgewiesen.

## Umgebung

- Python 3.12.14, Linux.
- Pakete: pytest 9.2.0, FastAPI 0.162.2, httpx 0.28.1, Uvicorn 0.54.0, Pydantic 2.14.2, Starlette 1.10.0.
- LM Studio und Docker in den automatisierten Tests simuliert.

## Nicht als real getestet ausgeben

- Windows-CMD/pythonw/Taskmanager, Installer-Downloads und tatsächliche Aider-Ausführung unter Windows.
- Reale Aider-Entwicklungsläufe mit Nutzerprojekten und lokalem LM Studio.
- VRAM-Verbrauch, GPU-Freigabe, Modellqualität und Quantisierungsvergleich.
- Echter Docker-Imagebau, Containerkommunikation und Docker Desktop unter Windows. Die Befehlsbildung, Netzwerkoptionen und Cleanup-Aufrufe wurden automatisiert simuliert.
- Live-Verfügbarkeit von DuckDuckGo. Providerbindung, deaktivierter Zustand und Fehlerprotokollierung wurden simuliert geprüft.

Das Setup führt auf der Zielmaschine selbst eine echte Aider-Version-/Optionsprüfung aus. Docker-, Modellserver- und Suchfehler werden angezeigt bzw. protokolliert, nicht als erfolgreicher Lauf ausgegeben.

## Empfohlener kurzer Zielsystemtest

1. Setup in einem neuen Ordner ausführen; Aider-Prüfung muss erfolgreich enden.
2. Workbench starten, Hilfedokumente öffnen; über UI und danach über Stop_ToolForge.cmd beenden.
3. Ein kleines Testprojekt mit unabhängigen Aufgaben und einer absichtlichen Rückfrage ausführen; Hinweiston und Antwortfortsetzung prüfen.
4. Vorabcheck mit zwei kleinen installierten Modellen durchführen; nach Übernahme geladenen Kontext in LM Studio vergleichen.
5. Wenn benötigt: Docker-Prüfumgebung bauen und eine harmlose Python-Datei ausführen. Netzwerk erst danach bewusst freigeben.

---

# Archiv 0.7

Prüfdatum: 09.11.2026.

- `python -m pytest -q tests backend/tests`: **104 bestanden**, eine Deprecation-Warnung der FastAPI/Starlette-Testumgebung.
- `npm run build`: TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich. Bestehende Größenwarnung zum JavaScript-Bundle (>500 kB).
- Neue Prüfungen: sequenzielle Wechsel, persistierte Arbeitsproben, ungültige Kandidaten, fehlende Modelle, Kontextüberschreitung, fehlgeschlagenes Entladen, abweichender geladener Kontext, Abbruch, ungültige Auswertung/Sieger, ungültige Proben, Fehler beim abschließenden Entladen, veraltete Einstellungen sowie kompletter Session-Ablauf von Vergleich über Übernahme bis Planerstellung.
- LM-Studio-Antworten in diesen Tests sind simuliert. Kein echter Modellserver, GPU-Speicherbenchmark oder Qualitätsvergleich auf Nutzerhardware.
- Visuelle Browserprüfung nicht abgeschlossen: Chromium war nicht installiert, beide Downloadversuche lieferten ungültige Archive. Die Oberfläche wurde kompiliert, aber hier nicht im Browser visuell verifiziert.

---

# Archiv 0.1–0.6

> Die frühere Datei `TESTBERICHT_V01-06.md` bündelte die Prüfungen bis 0.6. Erhalten sind die dort dokumentierten Stände 0.3 bis 0.6; die älteren Basisprüfungen aus 0.1 und 0.2 sind in den jeweiligen Regressionen der späteren Suiten enthalten.

## 0.6

Prüfdatum: 09.11.2026 · Linux · Python 3.12 · Node.js 24.

- **89 automatisierte Tests bestanden** (84,52 Sekunden). Eine Starlette-TestClient-DeprecationWarning ohne Testfehler.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich. Vite meldet einen großen JavaScript-Chunk (889 kB unkomprimiert); der Build ist erfolgreich.
- Neue Tests: sichere Pfade, Speicherkonflikte/Sicherungen, Binärdateien, Python-Ausführung/Abbruch, Git-Commits einschließlich Schutz fremder vorgemerkter Dateien, Workflow-Zyklen, CSV-Validierung, Export-Überschreibschutz und eigene Python-Knoten.
- KI-Vorschläge mit kontrollierter Modellantwort getestet: kein Schreiben vor Übernahme; veraltete Revision wird abgewiesen. Kein reales Sprachmodell in dieser Prüfung.
- API-Test: Dateien schreiben/lesen, Konflikt melden, Pfadausbruch verhindern, Workflow speichern, vollständige Abnahme und XLSX-Download.
- Chromium mit echtem Backend: Datei im CodeMirror-Editor erstellen und speichern, Python starten, Live-Ausgabe prüfen, Git initialisieren und ausgewählte Datei committen, CSV→Excel-Abnahme ausführen und Ergebnis herunterladen.
- Desktop-Editor und Workflow-Darstellung visuell geprüft; mobiler Viewport gerendert. Eine zunächst zu kleine SVG-Höhe wurde korrigiert.
- Export zusätzlich unabhängig mit openpyxl gelesen: Kopfzeile name/email und genau zwei Datensätze Ada/Linus. openpyxl ist hierfür nur Testwerkzeug, keine neue App-Abhängigkeit.

**Grenzen:** Windows-Startskripte, tatsächlicher LM-Studio-/Aider-Betrieb sowie reale Paketinstallation und Chocolatey-Deinstallation wurden hier nicht unter Windows ausgeführt. Die zugehörigen simulierten Regressionstests bestehen. Nicht jedes Layout und jede Kombination von Projektdateien wurde im Browser geprüft. Vollständige Funktionsgrenzen und Bedienung stehen in `README.md`.

## 0.5

Prüfdatum: 09.11.2026 · Linux · Python 3.12 · Node.js 24.

- **77 automatisierte Tests bestanden**, 20,63 Sekunden. Die bekannte Starlette-TestClient-DeprecationWarning bleibt ohne Testfehler bestehen.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich.
- Chromium gegen echtes Backend und kontrollierten lokalen Modell-API-Testserver: Planantwort zunächst ungültig, Reparatur erfolgreich, Anzeige im aktiven Editor und JSON-Datei tatsächlich gespeichert. Anschließend zweimal ungültige Antwort: sichtbarer Fehler im Plan-Reiter, vorhandener Plan erhalten.
- Browserprüfung: Umbenennen, Archivieren, Archivansicht, Wiederherstellen, Löschvorschau, Namensbestätigung und Entfernen des Projekteintrags. Arbeitsordner dabei erhalten. Keine JavaScript-Laufzeitfehler im geprüften Ablauf. Fehleransicht visuell kontrolliert.
- Scheduler-Test: A fragt, B läuft weiter; während B läuft wird die Antwort angenommen; anschließend A, danach das von A abhängige C. Alle Aufgaben erfolgreich geprüft.
- Weitere Tests: mehrere offene Fragen, keine Ausführung abhängiger Aufgaben, kontrollierte Meldungszuordnung, normalisierte pytest-Kommandos, Paketbereinigung und Journal, Schutz gemeinsam genutzter Umgebungen, globale Paketreferenzen einschließlich archivierter Projekte, wiederherstellbares Entfernen eines Arbeitsordners.

**Grenzen:** Keine reale Windows-/LM-Studio-Integration und keine reale Chocolatey-Deinstallation. Die Paketmanager-Ergebnisse wurden kontrolliert simuliert; Pfad-/Dateioperationen und Prozess-/Scheduler-Tests liefen tatsächlich. Der Planer wurde über einen lokalen HTTP-Testserver geprüft, nicht durch ein echtes Sprachmodell. Die Summarizer-Einstellung wurde anhand des Aider-Quellcodes und des erzeugten Aufrufs überprüft; die konkrete Shutdown-Fehlermeldung wurde hier nicht mit einem realen Aider reproduziert.

## 0.4

Prüfdatum: 09.11.2026 · Linux · Python 3.12 · Node.js 24.

- Vollständiger aktueller Python-Testlauf: **64 bestanden**, 19,87 Sekunden; eine unveränderte Starlette-DeprecationWarning.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich.
- Neue Tests prüfen gestückelte Tokenlimit-Meldungen, wiederholte Dateien/Codeblöcke, normale Ausgabe ohne Fehlalarm, Ausgabegrenze, Dateiumfang und echten Prozessabbruch.
- Tests zur Neuplanung prüfen begrenzte Modellanfragen, ungültige Antworten, erhaltene Integrationsprüfungen/Abhängigkeiten, Versionswechsel, fortgesetztes Budget, erfolgreiche Folgeausführung und das Verbot eines falschen Abschlusses nach Teilprüfungen.
- Der Modell-Teilplaner ist mit kontrollierten API-Antworten getestet. Ein realer LM-Studio-/Llama-8B-Lauf und Windows-Integration bleiben nicht durchgeführt.
- Die Browserprüfung stammt aus 0.3. Für 0.4 wurde der Frontend-Build erneut geprüft; der neue Neuplanungsabschnitt wurde nicht gesondert im Browser abgenommen.

## 0.3 – Browser- und Basisprüfung

Prüfdatum: 09.11.2026 · Linux · Python 3.12 · Node.js 24.

| Prüfung | Ergebnis |
|---|---|
| `python -m pytest backend/tests tests -q` | **52 bestanden**, 13,02 Sekunden |
| `npm run build` | TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich |
| Echter Browser gegen laufendes FastAPI-Backend | Chromium: Erstellung, Pflichtfeldvalidierung, Details und Ordnerzuordnung erfolgreich |
| Planübernahme im Browser | Beispielplan geladen, JSON direkt gespeichert und aktiviert |
| Browser → Pilot → Prozesse → Prüfungen | Drei Demoaufgaben nach einem Start automatisch abgeschlossen, tatsächliche Python-Abnahmen ausgeführt, 100 % |
| Persistenz im Browser | Neuladen und erneutes Öffnen zeigten weiterhin 3 von 3 geprüften Aufgaben |
| Dark-/Light-Mode | Umschaltung und gespeicherte Designwahl geprüft |
| Responsive Oberfläche | 1440 × 1000 und 390 × 844; kein horizontaler Seitenüberlauf; Screenshots visuell geprüft |
| JavaScript-Laufzeitfehler | Keine im getesteten Browserablauf |

Die Browserprüfung verwendete eine isolierte Testdatenbank und einen Testprojektordner. Sie installierte keine Abhängigkeiten in Benutzerprojekten. Browser-Testwerkzeuge werden nicht mitgeliefert und sind für den Betrieb nicht erforderlich.

### Abgedeckte automatisierte Fälle

- Sequenzielle Aufgaben, Budget und Fortsetzen, Reparaturen, Rückfragen und Antworten.
- Kein Erfolg nur durch Agententext oder Exit-Code; fehlende/falsche Meldungen.
- Gespeicherter Status, Projektsperre, Wiederanlauf, Neubewertung externer Änderungen.
- Pause/Stop, Prozess-Timeout und Prozessbaumbeendigung auf Linux.
- Ungültige Pläne, Pfadgrenzen, reservierte Windows-Namen, Geheimnisschwärzung.
- Windows-Batchoptionen im erzeugten Aider-Aufruf, TERM=dumb, Warnungs-/Scraping-Optionen.
- Modellmetadaten, Temperatur, echter geladener Kontext gegenüber theoretischer Grenze.
- Kontextabschätzung, Planaufteilung mit unveränderter Gesamtprüfung, Planversionierung.
- Automatische Verkleinerung des Dateiumfangs bei Laufzeit-Kontextüberschreitung.
- Lokale Protokollpfade, aktiver Plan und Laden bei fehlendem Controller-Zustand.
- Paketfreigaben aus, Paketnamenvalidierung, Installationsjournal und README-Eintrag.
- Erfolgreiche/fehlgeschlagene Installationen mit gemockten Paketmanager-Prozessen.
- Erneute Installation nach fehlender Umgebung, npx ohne Nachinstallation.
- Projekt-CRUD, Trimmen, Längengrenzen, UUID/UTC, Datenbankpersistenz und Migration.
- Lokale Origin-/Hostprüfung und mutierende API-Anfragen mit eigenem Header.
- API-Schlüssel nicht in gespeicherten Projekteinstellungen.

### Grenzen der Prüfung

**Nicht auf einem echten Windows-PC ausgeführt:** CMD-Starter, Windows-Konsolenhandles, Job-Object-Prozessbeendigung, native Ordnerauswahl und Explorer-Aufruf. Die Konstruktion wurde geprüft, ist aber kein Ersatz für einen echten Windows-Integrationstest.

**Kein echter LM-Studio-/LLM-Lauf:** Der lokale Server des Anwenders ist aus dieser Testumgebung nicht erreichbar. Modellmetadaten und Aider-Aufrufe wurden gezielt getestet; der automatische Ende-zu-Ende-Ablauf nutzt den ausdrücklich markierten DemoAdapter. Die Aider-Optionen und der prompt_toolkit-Initialisierungspfad wurden zusätzlich am Quellcode von aider-chat 0.86.2 überprüft. Modellqualität und vollständig erfolgreiche Aider-Edits mit dem konkreten LM-Studio-Modell sind hier nicht nachgewiesen.

**Keine echten Chocolatey-Systeminstallationen:** Freigabe, Kommando und Journal wurden mit kontrollierten Prozessantworten geprüft. Administratorrechte und konkrete Pakete müssen auf Windows verifiziert werden.

Eine Starlette-TestClient-DeprecationWarning weist auf eine künftige HTTPX-Umstellung hin. Sie beeinflusste keinen Test. Der Testlauf enthält keine fehlgeschlagenen oder übersprungenen Tests.

### Kurzer Windows-Abnahmelauf

1. Setup und normalen Starter ausführen; Workbench muss im Browser erscheinen.
2. Neues leeres Zielprojekt verbinden, Beispielplan laden, Simulation einschalten.
3. Start: drei Aufgaben müssen ohne weiteren Start auf „Geprüft“ wechseln.
4. Protokollordner öffnen: Explorer muss `<Projekt>\.toolforge\logs` anzeigen.
5. Workbench beenden/neustarten, Projekt erneut öffnen: gespeicherter Stand vorhanden.
6. Separates echtes Testprojekt: Simulation aus, Aider-Python und LM-Studio-Modell wählen.
7. Kleine Aufgabe mit messbarer Prüfung starten. Kein prompt_toolkit-Dialog und kein Browserfenster für Modellwarnungen; Kontext-/Temperaturwerte in Laufmetadaten prüfen.
8. Jede Installationsfreigabe einzeln mit einem gewünschten Testpaket prüfen; README und Journal kontrollieren. Chocolatey nur auf einem geeigneten Testsystem ausprobieren.
