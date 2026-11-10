# Historische Basisspezifikation 0.6

Der aktuelle Anforderungsabgleich einschließlich 0.7/0.8 steht in ABNAHME_V08.md. Die folgenden Angaben dokumentieren den früheren Stand.

# ToolForge Pilot 0.6 — Implementierungsumfang

Lokale Python-/FastAPI-/SQLite-Anwendung mit gebauter React-/TypeScript-Oberfläche.
Der vollständige Anforderungskatalog und die Zuordnung der 9 Probleme sowie 5
Zusatzfunktionen stehen in README.md. Die ursprüngliche Workbench-Spezifikation
liegt unverändert im Ordner specification.

## Komponenten
- backend/main.py: Projekt-API, Persistenz, lokale Zugriffsprüfung, Frontend-Auslieferung.
- backend/pilot_service.py: Projektbestand, Einstellungen, Modelle, Hintergrundaufträge.
- toolforge_pilot/core.py: Prüfungen, Aider-Batchmodus, Prozessbaum, Zustandsautomat.
- toolforge_pilot/profiles.py: Modellkontext, Planer, Aufgabenaufteilung und Versionen.
- toolforge_pilot/installations.py: getrennte Freigaben und Installationsjournal.
- frontend/src: Projektverwaltung, Dashboard, Planbearbeitung und Einstellungen.
- tests und backend/tests: reproduzierbare Engine-, Fehler- und API-Tests.

- backend/workspace.py: Editor, Jobs, Git und kontrollierte KI-Vorschläge.
- backend/workflows.py: DAG-Validierung, CSV-/Python-Knoten und XLSX-Abnahme.

## Abnahmegrundsatz
Nur bestandene Prüfkommandos liefern einen geprüften Aufgabenstatus. Agententext
oder Exit-Code allein liefern keinen Erfolgsnachweis. Originale Abnahmekriterien
bleiben bei Kontextaufteilung erhalten. Rückfragen und Installationsfreigaben sind
sichtbar, Starts und automatische Wiederholungen sind budgetiert.

## Ausführung
Normaler Aufruf: Start_ToolForge_Pilot.cmd oder python start_toolforge.py.
Die alte Desktop-Ansicht ist nur über Start_Pilot_Desktop.cmd separat erreichbar.
