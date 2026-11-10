# ToolForge Pilot 0.8

Lokale Workbench mit Projektverwaltung, Editor, Aider-Pilot, geprüften Aufgabenplänen, Modellvergleich, Erweiterungsplanung, Hilfe und optionaler Docker-Ausführung.

## Installation und Start unter Windows

1. Alten ToolForge-Server beenden. ZIP in einen neuen Programmordner entpacken.
2. `Setup_ToolForge.cmd` ausführen. Erforderlich: Python 3.11 oder neuer und Internetzugang. Das Setup erstellt `.venv` für die Workbench und `.aider-venv` für Aider. Bei Bedarf lädt uv Python 3.12 für Aider. Eine echte Aider-Aufruf- und Optionsprüfung muss erfolgreich sein.
3. `Start_ToolForge.cmd` oder `Start_ToolForge_Pilot.cmd` öffnen. Die Weboberfläche erscheint unter http://127.0.0.1:8000. In Chrome/Edge öffnet sich ein eigenes App-Fenster, das beim Beenden automatisch geschlossen wird. Kein dauerhaftes CMD-Fenster; Zugriffslogs sind ausgeschaltet.
4. Bei Problemen `Start_ToolForge_Debug.cmd` verwenden; zusätzlich `runtime/startup.log` prüfen.
5. Zum Beenden den Button oben in der UI oder `Stop_ToolForge.cmd` verwenden. Bei nicht reagierender API schreibt das Stoppskript eine instanzbezogene Wächterdatei. Ein vollständig eingefrorener Betriebssystemprozess erfordert den Taskmanager.

Das Frontend ist fertig gebaut und mitgeliefert. Node.js ist für die normale Nutzung nicht nötig. Für Frontend-Entwicklung: `npm ci`, `npm run build` im Ordner frontend.

## Deinstallation unter Windows

`Deinstallieren_ToolForge.cmd` ausführen. Das Skript entfernt `.venv`, `.aider-venv`, `frontend/node_modules`, `frontend/dist`, `runtime` und Python-Caches. Auf Wunsch werden auch die gespeicherten ToolForge-Daten im Benutzerprofil (`%APPDATA%\ToolForgePilot`) gelöscht. Eigene Projektordner werden nie verändert. Anschließend den Programmordner manuell löschen. Ohne Rückfragen: `python uninstall_toolforge.py --yes`, Daten behalten: zusätzlich `--keep-data`.

## Vorhandene Projekte übernehmen

Bei ausgeschaltetem Server `backend/data` aus dem bisherigen Programmordner in den neuen übernehmen, um die Projektliste zu erhalten. Die bisherigen Arbeitsordner weiterverwenden; sie dürfen nicht im ToolForge-Programmordner liegen. Die neue `.venv` und `.aider-venv` durch Setup erstellen lassen, nicht alte virtuelle Umgebungen kopieren. Im Projekt verbleiben `.toolforge/active-plan.json`, Planversionen und Protokolle. Der zugehörige laufende Zustand wird zusätzlich im ToolForgePilot-Datenordner des Benutzers gespeichert.

Alte Prüfnachweise ohne Dateibelege werden einmal neu geprüft. Danach bleibt unverändert geprüfte Arbeit erhalten. Unter Einstellungen bei Bedarf Projekt-Basis-Python und den neuen Aider-Python-Pfad prüfen.

## Arbeitsablauf

Projekt verbinden → Aufgabenbeschreibung → optionaler Modell-Vorabcheck → Empfehlung übernehmen → Plan erstellen → Start / Fortsetzen. Änderungen an einem bestehenden Tool über **Entwicklungsbereich → Verbesserungen** einreichen. Das erweitert den Plan, statt das Projekt neu zu beginnen.

Die Entwicklungstabs stehen in dieser Reihenfolge: **Verbesserungen · Dateien & Editor · KI-Änderungen · Ausführen & Prüfen · Git · Workflows**. Unter **Hilfe** stehen Bedienungsdokumente und ein lokaler, dokumentgestützter Hilfechat.

### Neu in 0.8

- Aider wird getrennt installiert und geprüft. Die manuelle Installation der drei Prüfwerkzeuge braucht keine allgemeine automatische pip-Freigabe mehr.
- Verdeckter Serverstart; die UI öffnet in einem eigenen Chrome-/Edge-Fenster, das beim Beenden automatisch geschlossen wird. Andere Browser zeigen einen Hinweisbildschirm. Stoppskript und Debugstart bleiben vorhanden.
- Aufgabenbezogene Dateibelege, abhängige Wiederholungsprüfungen und abschließende Integrationsprüfung. Kein pauschales Zurücksetzen aller erledigten Aufgaben.
- Unabhängige Arbeit läuft bei Rückfragen weiter. Blockierungsgründe sind sichtbar; eingehende Antworten werden an der nächsten Aufgabengrenze priorisiert.
- Ausstehende Pause zurücknehmen; Hinweiston mit Lautstärke und Stummschaltung.
- Erweiterungen während laufender oder abgeschlossener Projekte; KI-Vorschläge nach auswählbaren Bereichen, einzeln bestätigbar. Änderungen an bereits analysiertem Code verhindern die Übernahme veralteter Vorschläge.
- Dokumentgestützte Hilfe; Assistenzmodelle wechseln sequenziell und stellen das Arbeitsmodell wieder her.
- Optionale DuckDuckGo-Suche und ausführliche Diagnosen. Die Schalter lassen sich in der Übersicht für den nächsten Durchlauf ändern. Pakete und Modellkonfiguration werden dadurch nicht freigegeben/geändert.
- Fehlerabhängige Reparaturstrategien statt pauschaler Aufgabenverkleinerung.
- Fehlgeschlagene Quelltext-Builds (z. B. Pillow unter Python 3.11 ohne zlib) werden automatisch über PyPI-Metadaten und optional die Websuche auf eine neuere Version mit passendem Wheel aufgelöst. Der Plan wird mit der geprüften Version neu versioniert und die Aufgabe erhält den Befund als Hinweis.
- Ein Klick im Vorabcheck führt den kompletten Ablauf aus: Vorabcheck → Empfehlung übernehmen → Plan erstellen → Ausführung starten.
- Kleine Kontextabweichungen (Rundung durch LM Studio) brechen den Vorabcheck nicht mehr ab; der tatsächlich geladene Wert wird als geprüftes Budget übernommen.
- Drei bis sechs Kandidaten im Vorabcheck wählbar.
- Deinstallationsskript für Umgebungen, Buildartefakte und optional Benutzerdaten.
- Optionale Docker-Ausführung für Python, Prüfungen und Python-Workflowknoten; explizit gemeinsame interne Netzwerke.

## Dokumentation und Prüfbelege

- [Abnahme und vollständiger Anforderungsabgleich](ABNAHME_V08.md)
- [Testbericht 0.8](TESTBERICHT_V08.md)
- [LM-Studio-Presets und alle 15 Modellvarianten](LM_STUDIO_PRESETS.md)
- [Start und Projekte](help/01_Start_und_Projekte.md)
- [Modelle und Aufgaben](help/02_Modelle_und_Aufgaben.md)
- [Entwicklungsbereich](help/03_Entwicklungsbereich.md)
- [Recherche, Diagnose und Sandbox](help/04_Recherche_Diagnose_Sandbox.md)
- [Nützliche nächste Optimierungen](NAECHSTE_SCHRITTE.md)

## Grenzen der Ausführung

Modelle müssen in LM Studio installiert sein. Der Vorabcheck benötigt die Native REST API v1. Die Modellbewertung ist eine Stichprobe, keine Garantie des objektiv besten Modells. Kontextgröße wird als geladenes Budget geprüft, noch nicht über mehrere Größen optimiert. Die KI-Projektanalyse arbeitet mit begrenzten Quelltextausschnitten und weist ungelesene Teile aus.

Docker ist optional und muss separat vorhanden sein. Editor, Git, Aider-Dateiänderungen und lokale Paketinstallation bleiben auf dem Host; die Containeroption ist keine vollständige Virtualisierung der Workbench. Details zu Netzwerken, Paketen und Projektmounts stehen in der Hilfe. Der alte separat startbare Tkinter-Pilot wird mitgeliefert; neue Oberflächenfunktionen sind in der Webworkbench verfügbar.

## Entwicklertests

`python -m pip install -r requirements-dev.txt`

`python -m pytest -q tests backend/tests`

`npm --prefix frontend run build`

Die Tests verwenden isolierte Projekte. Reale Modellqualität, Windows-GPU-Verhalten und Docker Desktop müssen auf der Zielmaschine zusätzlich geprüft werden; sie werden nicht durch simulierte Antworten ersetzt.
