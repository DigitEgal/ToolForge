<p align="center">
  <img src="docs/assets/toolforge-logo.svg" alt="ToolForge – Local Workbench" width="360">
</p>

<p align="center">
  <strong>Lokale Vibe-Coding-Workbench für Python-Tools:</strong><br>
  planen, prüfen, entwickeln, testen, versionieren und verbinden – auf deinem Rechner.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-V1.0-b8a3ff" alt="Version V1.0">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-2f3640" alt="Windows und Linux">
  <img src="https://img.shields.io/badge/tests-132%20passed-2ea44f" alt="132 Tests bestanden">
  <img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="MIT-Lizenz">
</p>

---

## Was ist ToolForge?

ToolForge verbindet eine Projektverwaltung mit einem kontrollierten KI-Entwicklungsablauf. Du beschreibst ein Ziel, vergleichst optional lokale Modelle in einem Vorabcheck und lässt daraus einen prüfbaren Aufgabenplan erzeugen. Aider bearbeitet die Aufgaben anschließend schrittweise; bestandene Prüfkommandos – nicht bloßer Agententext – liefern den Erfolgsnachweis.

Alles läuft lokal. Die Workbench ist standardmäßig nur unter `http://127.0.0.1:8000` erreichbar. Cloud-Dienste und ein KI-Anbieter sind für die Grundfunktionen nicht erforderlich.

> **Für wen?** Technisch erfahrene Einzelanwender, die lokale Modelle (z. B. LM Studio) und Aider nutzen möchten, dabei aber Pläne, Dateiänderungen, Tests und Freigaben im Blick behalten wollen.

## Funktionsumfang

| Bereich | Funktionen |
|---|---|
| **Projekte** | Anlegen, öffnen, durchsuchen, archivieren, löschen mit Bereinigungsvorschau; Kachel- und Listenansicht; Projektgruppen; wiederherstellbare Ordnerlöschung; getrennte pip-/Chocolatey-/npm-Freigaben |
| **Pilot** | Zielbeschreibung, Modell-Vorabcheck, prüfbarer Aufgabenplan, Aider-Batchausführung, Rückfragen, Pause/Fortsetzen, Reparaturstrategien, Erweiterungen ohne Neustart, Fortschrittserhalt, Projektprotokolle |
| **Modellvergleich** | Drei bis sechs Kandidaten, identische Arbeitsproben, ein oder zwei Temperaturen, anonymisierte Auswertung, Empfehlung mit ausdrücklicher Übernahme, Kontextprüfung inklusive kleiner LM-Studio-Rundungsabweichungen |
| **Entwicklung** | Dateibaum und CodeMirror-Editor, konfliktgeprüftes Speichern mit Sicherungen, Python-Ausführung mit Live-Ausgabe und Abbruch, pytest/Ruff/mypy, Git-Status/Diff/ausgewählte Commits/Historie |
| **KI-Unterstützung** | Einzeldatei-Vorschläge mit Diff und ausdrücklicher Übernahme; Erweiterungsvorschläge nach Kategorien; dokumentgestützter Hilfechat |
| **Workflows** | Visueller Knotengraph, Validierung, CSV prüfen, Duplikate entfernen, Excel exportieren, Python-Knoten |
| **Recherche & Diagnose** | Optionale DuckDuckGo-Suche mit Journal, ausführliche Fehlerprotokolle mit Redaktion von Geheimnissen |
| **Sandbox** | Optionale Docker-Ausführung für Projektbefehle und Python-Workflowknoten, explizite interne Netzwerke |
| **Bedienung** | Dark/Light Design, Hinweiston mit Lautstärke, geführte UI- und Entwickler-Tutorials, Hilfe direkt in der App |
| **Betrieb** | Verdeckter Start, eigenes Chrome-/Edge-App-Fenster mit automatischem Schließen, Stoppskript, Debugstart, Deinstallationsskript |

## Neu in V1.0

- **Pillow-Buildfehler werden selbst gelöst:** Scheitert ein Quelltext-Build, sucht ToolForge per PyPI-Metadaten nach einer passenden Wheel-Version, recherchiert optional den Fehler und installiert die geprüfte Version erneut. Der Plan wird neu versioniert und die Aufgabe erhält den Befund.
- **Browser schließt mit:** Wurde die UI in einem von ToolForge gestarteten Chrome-/Edge-App-Fenster geöffnet, beendet „ToolForge beenden“ auch dieses Fenster.
- **Ein Klick bis zum Start:** Vorabcheck → Empfehlung übernehmen → Plan erstellen → Ausführung starten.
- **Kleine Kontextabweichungen sind kein Abbruch:** Der von LM Studio tatsächlich geladene Wert wird als geprüftes Budget übernommen.
- **Drei bis sechs Kandidaten** im Modell-Vorabcheck.
- **Deinstallationsskript** für ToolForge-eigene Umgebungen, Buildartefakte und optional Benutzerdaten.
- **V1.0-Oberfläche:** Projektgruppen, Kachel-/Listenansicht, geführte Tutorials, DigitEgal-Branding und MIT-Lizenz.

Die vollständige Zuordnung steht in [ABNAHME_V10.md](ABNAHME_V10.md). Die v0.9-Nachzügler und alle Regressionen von 0.1 bis 0.8 sind dort ebenfalls dokumentiert.

## Installation unter Windows

**Voraussetzungen**

- Windows 10/11
- Python 3.11 oder neuer
- Internetverbindung für Setup und Pakete
- Optional: [LM Studio](https://lmstudio.ai/) mit aktivierter Native REST API v1
- Optional: Docker Desktop für die Sandbox

**Schritte**

1. ZIP in einen neuen Programmordner entpacken. Einen eventuell laufenden alten ToolForge-Server vorher beenden.
2. `Setup_ToolForge.cmd` ausführen. Das Setup legt `.venv` für die Workbench und `.aider-venv` für Aider an und prüft Aider tatsächlich auf Version und benötigte Optionen.
3. `Start_ToolForge.cmd` öffnen. Die UI startet unter `http://127.0.0.1:8000`; unter Chrome/Edge öffnet sich ein eigenes App-Fenster.
4. Beim ersten Start führt ein Willkommensdialog in das UI-Tutorial ein.
5. LM Studio starten, Modell laden und die Serveradresse unter **Einstellungen** prüfen.

```text
Setup_ToolForge.cmd        einmalig einrichten
Start_ToolForge.cmd        Workbench starten
Start_ToolForge_Debug.cmd  bei Startproblemen; Log unter runtime/startup.log
Stop_ToolForge.cmd         Notfall-Stopp bei hängender UI
```

Node.js ist für die normale Nutzung nicht erforderlich – das gebaute Frontend liegt bei.

### Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python start_toolforge.py
```

Für Aider gilt derselbe getrennte Ansatz wie unter Windows; Details stehen in der Hilfe.

## Erster Arbeitsablauf

1. **Projekt anlegen** und einen Arbeitsordner außerhalb des ToolForge-Programmordners verbinden.
2. **Ziel beschreiben** und im Vorabcheck drei bis sechs installierte Modelle vorschlagen lassen.
3. **Vorabcheck starten** oder direkt **„Automatisch: Vorabcheck → Empfehlung → Plan → Start“** wählen.
4. Empfehlung prüfen, Plan ansehen und die Ausführung starten. Offene Rückfragen erscheinen im Cockpit.
5. Bestehende Tools über **Entwicklungsbereich → Verbesserungen** erweitern, statt neu zu beginnen.
6. Mit **Dateien & Editor**, **Ausführen & Prüfen**, **Git** und **Workflows** weiterarbeiten.

Die Entwicklungs-Tabs folgen dem Ablauf: **Verbesserungen · Dateien & Editor · KI-Änderungen · Ausführen & Prüfen · Git · Workflows**.

## Deinstallation

```text
Deinstallieren_ToolForge.cmd
```

Entfernt `.venv`, `.aider-venv`, `frontend/node_modules`, `frontend/dist`, `runtime`, `.pytest_cache` und Python-Caches. Auf Wunsch wird `%APPDATA%\ToolForgePilot` gelöscht. **Eigene Projektordner werden nie verändert.** Danach den Programmordner manuell löschen.

Ohne Rückfragen:

```powershell
python uninstall_toolforge.py --yes
python uninstall_toolforge.py --yes --keep-data
```

## Sicherheit und Datenschutz

- **Lokal:** Serverbindung an `127.0.0.1`, CORS auf lokale Adressen begrenzt, Zugriffslogs standardmäßig aus.
- **Keine stillen Cloud-Aufrufe:** Websuche ist opt-in und nutzt ausschließlich DuckDuckGo. Jeder Versuch – auch Fehler und null Treffer – landet im Projektjournal.
- **Keine pauschalen Rechte:** pip-, Chocolatey- und npm-Installationen sind getrennt freigebbar; Prüfwerkzeuge haben eine eigene Einmal-Freigabe.
- **Geheimnisse:** API-Schlüssel werden in Logs redigiert; ausführliche Diagnosen sind opt-in.
- **Projektordner bleiben unangetastet:** Löschvorgänge sind auf ToolForge-eigene Daten und bestätigte Projektordner begrenzt.
- **Docker ist optional:** Ohne Docker laufen Befehle auf dem Host. Die Containeroption ist keine vollständige Virtualisierung der Workbench.

## Dokumentation

- [Abnahme und Anforderungsabgleich V1.0](ABNAHME_V10.md)
- [Testbericht V1.0](TESTBERICHT_V10.md)
- [Testumgebung V1.0](TEST_ENVIRONMENT_V10.json)
- [Entwicklungspfad](TOOLFORGE_ROADMAP.md)
- [LM Studio und Modell-Vorabcheck](LM_STUDIO_PRESETS.md)
- [Start und Projekte](help/01_Start_und_Projekte.md)
- [Modelle und Aufgaben](help/02_Modelle_und_Aufgaben.md)
- [Entwicklungsbereich](help/03_Entwicklungsbereich.md)
- [Recherche, Diagnose und Sandbox](help/04_Recherche_Diagnose_Sandbox.md)
- [Nächste Optimierungen](NAECHSTE_SCHRITTE.md)

Die Hilfe ist auch direkt in der App unter **Hilfe** erreichbar.

## Entwicklung und Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests backend/tests
npm --prefix frontend run build
```

Der Frontend-Build führt `tsc --noEmit` und den Vite-Produktionsbuild aus. Die Tests verwenden isolierte Projekte und simulierte Modell-/Docker-Antworten. Reale Modellqualität, GPU-/VRAM-Verhalten, Docker Desktop, echte Aider-Läufe und der Windows-Browserstart müssen auf der Zielmaschine zusätzlich geprüft werden. Details und Grenzen: [TESTBERICHT_V10.md](TESTBERICHT_V10.md).

### Projektstruktur

```text
backend/            FastAPI, Projekt-API, Pilot-Brücke, Workspace, Workflows
toolforge_pilot/    Engine, Aider-Adapter, Vorabcheck, Installationen, Recovery
frontend/src/       React-/TypeScript-Oberfläche inklusive Tutorials
tests/              Engine-, Pilot- und Regressionstests
backend/tests/      API-, Datenbank- und Migrationsprüfungen
help/               Bedienungsdokumente für die App
docs/assets/        ToolForge- und DigitEgal-Logos
```

## Bekannte Grenzen

- LM Studio muss installiert sein und die Native REST API v1 bereitstellen. Der Vorabcheck ist eine Stichprobe, keine Garantie für das objektiv beste Modell.
- Die Kontextgröße wird als geladenes Budget geprüft, aber nicht über mehrere Größen empirisch optimiert.
- Die KI-Projektanalyse arbeitet mit begrenzten Quelltextausschnitten und weist ausgelassene Dateien aus.
- Docker, Aider und GPU-Verhalten werden nicht durch simulierte Tests ersetzt.
- Ein vollständig eingefrorener Betriebssystemprozess muss im Taskmanager beendet werden. ToolForge beendet niemals pauschal fremde Python-Prozesse.
- Ein Browser außerhalb des ToolForge-App-Fensters darf per Skript nicht geschlossen werden; dort erscheint ein Abschlussbildschirm.

## Versionsgeschichte

| Version | Schwerpunkt |
|---|---|
| 0.1 | Projektverwaltung, lokale Persistenz, Workbench-Grundgerüst |
| 0.2 | Projektanalyse/Dashboard, getrennte Paketfreigaben, Installationsjournal |
| 0.3 | Aider-Batchmodus, Plan-JSON, Modellwarnungen, Kontext/Temperatur, Diagnose, Logs |
| 0.4 | Schleifen-/Tokenlimits, frischer Kontext, begrenzte Neuplanung, Gesamtprüfung |
| 0.5 | Plan speichern/importieren, Projektlebenszyklus, unabhängige Aufgaben trotz Rückfragen |
| 0.6 | Editor, Python-Ausführung, Qualitätsprüfungen, Git, KI-Diffs, Workflows, CSV/Excel-Abnahme |
| 0.7 | Modell-Vorabcheck, Arbeitsproben, 15 Presets, 20.000 Startkontext |
| 0.8 | Sechs Probleme und sieben Verbesserungen: Setup, Rückfragen, Fortschritt, Reparatur, Hilfe, Ton, Websuche, Diagnose |
| 0.9 | Projektgruppen, Listenansicht, Tutorials, Branding – in V1.0 nachgezogen |
| **V1.0** | **Pillow-Selbstreparatur, Browser-Schließen, Ein-Klick-Ablauf, Kontexttoleranz, 3–6 Kandidaten, Deinstallation** |

## Lizenz und Credits

MIT-Lizenz – siehe [LICENSE](LICENSE). Copyright © 2026 **DigitEgal**.

ToolForge nutzt unter anderem FastAPI, Uvicorn, SQLite, React, TypeScript, Vite, CodeMirror und Aider. LM Studio und Docker sind optionale, separat zu installierende Werkzeuge.
