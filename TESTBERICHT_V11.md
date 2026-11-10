# Testbericht ToolForge Pilot V1.1

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
