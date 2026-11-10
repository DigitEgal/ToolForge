# Anforderungsabgleich V1.0

> **Historischer Stand V1.0.** Aktueller Abgleich: [ABNAHME.md](../../ABNAHME.md). Die V1.0-Funktionen sind in V1.1 und V1.2 erhalten.

Basis: bereitgestellte Version 0.8 einschließlich aller früheren Stände. Geprüft wurde der Code- und UI-Stand; reale Windows-, GPU-, Docker-, Browser- und Aider-Läufe sind im Testbericht gesondert abgegrenzt. Maßgeblich ist die gelieferte Versionshistorie von 0.1 bis V1.0.

## V1.0-Pflichtpunkte

| ID | Anforderung | Umsetzung | Beleg |
|---|---|---|---|
| V10-1 | Build-Fehler von Pillow selbst lösen, per Websuche recherchieren und den Plan neu entwerfen | `InstallManager.resolve_python_package` erkennt fehlgeschlagene Quelltext-Builds, fragt PyPI-Metadaten nach der neuesten Version mit passendem Wheel ab, nutzt optional die DuckDuckGo-Recherche und wiederholt die Installation mit gepinnter Version. `last_resolution` dokumentiert Ausgangs- und Zielversion. `Engine.apply_install_resolution` versioniert den Plan neu, schreibt die geprüfte Version in den Auftrag und ergänzt den Befund als Hinweis. Fehlgeschlagene Versionsmarker werden verworfen. | `tests/test_improvements.py`: Quelltext-Build-Fehler, PyPI-Auswahl, Wiederholungsbefehl, Plan-Neuversionierung und Diagnose. |
| V10-2 | Browser bei „ToolForge beenden“ schließen | Der Start öffnet auf Windows ein eigenes, verfolgtes Chrome-/Edge-`--app`-Fenster mit eigenem Profil. Der Server registriert den Shutdown-Hook und beendet genau diesen Prozess. Zusätzlich versucht die UI `window.close()` und zeigt bei Browser-Blockade einen Abschlussbildschirm. | Quellprüfung `start_toolforge.py` (Start, Track, `close_ui`) und `App.tsx`; echter Windows-Lauf im Testbericht als offen ausgewiesen. |
| V10-3 | Ein Klick: Vorabcheck → Empfehlung → Plan → Start | `PreflightPanel.autopilot` speichert Einstellungen, startet den Vorabcheck, pollt den Zustand, übernimmt die Empfehlung, erzeugt den Plan und startet die Ausführung. Fehler und Phasen werden sichtbar gemeldet. | TypeScript-/Vite-Build; Ablauf über die vorhandenen 202-Endpunkte. Kein Live-LM-Studio-Lauf in dieser Prüfung. |
| V10-4 | Kleine Kontextabweichungen akzeptieren | `context_tolerance` erlaubt `max(512, 2 %)` unter dem angeforderten Wert; `context_compatible` prüft die Grenze. Der tatsächlich von LM Studio geladene Wert wird als `Studio.actual_context` übernommen und als geprüftes Budget gespeichert. Deutlich kleinere Werte werden weiterhin abgewiesen. | `tests/test_preflight.py`: 20.224 statt 20.000 wird übernommen; 4.096 statt 20.000 wird abgelehnt. |
| V10-5 | Drei oder mehr Vorabcheck-Kandidaten auswählbar | `MAX_CANDIDATES = 6`; die Oberfläche bietet 3, 4, 5 oder 6 Kandidaten an. Jeder Kandidat erhält dieselben Arbeitsproben; mehr als sechs werden serverseitig abgewiesen. | `tests/test_preflight.py`: drei Kandidaten ergeben sechs Proben (zwei Temperaturen), sieben Kandidaten werden abgelehnt; Frontend-Build. |
| V10-6 | Deinstallationsskript | `Deinstallieren_ToolForge.cmd` und `uninstall_toolforge.py` entfernen `.venv`, `.aider-venv`, `frontend/node_modules`, `frontend/dist`, `runtime`, `.pytest_cache` und `__pycache__`. Auf Wunsch wird `%APPDATA%\ToolForgePilot` gelöscht. Eigene Projektordner werden nie angefasst. Optionen: `--yes`, `--keep-data`. | Quellprüfung und Smoke-Test in einer temporären Kopie: ToolForge-Verzeichnisse entfernt, ein simulierter Projektordner blieb erhalten, `--keep-data` ließ die Daten stehen. Kein Lauf gegen ein produktives Benutzerprofil. |

## v0.9-Nachzügler

Diese Punkte waren für 0.9 vorgesehen, fehlten im übernommenen Stand und wurden mit V1.0 nachgezogen.

| ID | Anforderung | Umsetzung | Beleg |
|---|---|---|---|
| V09-1 | Geführte Tutorials | `Tutorial.tsx` mit Spotlight-Verdunkelung, `data-tour`-Zielen, Haupt- und Entwickler-Tour, Willkommensdialog, Abbrechen, `Esc`, Wiederaufruf über die Hilfe und automatischem Start der Entwickler-Tour beim ersten Besuch. | Frontend-Build; Sichtprüfung der Komponenten und Selektoren. |
| V09-2 | Projektgruppen | Neue SQLite-Tabelle `project_groups`, `projects.group_id`, Migration auf `PRAGMA user_version=4`, CRUD unter `/api/groups`, Zuordnung über Projekt-PATCH. Beim Löschen einer Gruppe bleiben Projekte erhalten und werden „Ohne Gruppe“ zugeordnet. | `backend/tests/test_api.py::test_project_groups_cluster_and_move` sowie Migrationstest. |
| V09-3 | Listenansicht | Umschalter **Kacheln / Liste** mit gespeicherter Auswahl, Gruppenabschnitten, Zeilenzuordnung und Gruppenauswahl in den Projektdetails. | Frontend-Build; TypeScript-Prüfung. |
| V09-4 | DigitEgal-Branding | Sidebar zeigt „by DigitEgal“ unter der Wortmarke und einen kompakten Hinweis unten; SVG-Logos unter `docs/assets`. | Quellprüfung, Frontend-Build. |
| V09-5 | MIT-Lizenz | `LICENSE` mit MIT-Text, Copyright 2026 DigitEgal. | Dateiprüfung. |

## Frühere Versionen – Regression

| Version | Kernumfang | Stand V1.0 |
|---|---|---|
| 0.1 | Projektverwaltung, lokale Persistenz, FastAPI/SQLite/React-Grundgerüst | Erhalten; API- und Migrationstests. |
| 0.2 | Projekt einlesen, Dashboard, Fortsetzen; getrennte pip-/Chocolatey-/npm-Freigaben; Installationsübersicht | Erhalten; Scan-, Freigabe- und Journaltests. |
| 0.3 | Aider-Batchmodus, Plan-JSON, Modellwarnungen, Kontext- und Temperaturübergabe, Diagnose vor Rückfrage, Projektprotokolle | Erhalten; Adapter- und Planprüfungen. |
| 0.4 | Schleifen-/Tokenlimits, frischer Kontext, begrenzte Neuplanung, Gesamtprüfung | Erhalten; Strategie- und Kontextaufteilungstests. |
| 0.5 | Plan anzeigen/speichern/importieren, Umbenennen/Archivieren/Löschen mit Paketbereinigung, unabhängige Aufgaben trotz Rückfragen, frische Aider-Aufrufe | Erhalten; API-, Lebenszyklus- und Reihenfolgetests. |
| 0.6 | Editor mit Konfliktschutz, Python-Ausführung, pytest/Ruff/mypy, Git, KI-Diffs, visuelle Workflows, CSV-/Excel-Abnahme | Erhalten; Workspace-, Git-, Workflow- und Abnahmetests. Sandbox folgte in 0.8. |
| 0.7 | Modell-Vorabcheck mit bis zu drei Modellen, Arbeitsproben, zwei Temperaturen, allgemeine Auswertung, 15 Presets, 20.000 Startkontext | Erhalten und auf 3–6 Kandidaten erweitert; Preflight-Tests. |
| 0.8 | Sechs gemeldete Probleme und sieben Verbesserungen: Aider-Setup, Prüfwerkzeugfreigabe, verdeckter Start, Rückfragen, Fortschrittserhalt, Reparaturstrategien, Pause, Erweiterungen, Hilfe, Ton, Websuche, Diagnose | Erhalten; vollständige Zuordnung in `ABNAHME_V08.md`, Regressionen in der Gesamttestsuite. |
| 0.8 / 09–10 | Optionale Docker-Ausführung und explizite interne Sandbox-Netzwerke | Erhalten; Kommando-, Netzwerk- und Cleanup-Tests; echter Docker-Lauf offen. |

## Zusätzliche V1.0-Korrekturen

- SQLite-Verbindungen werden über einen schließenden Kontextmanager geführt; das vermeidet Windows-Dateisperren nach dem Schließen der Datenbank.
- Die Projektgruppen-Migration ergänzt `group_id` und `project_groups` ohne bestehende Projekte zu verlieren.
- Die API meldet `1.0.0`; Frontend, Desktop-Titel, Startbanner, Setup-Ausgabe und User-Agent tragen V1.0.
- Fehlgeschlagene Installationsmarker werden entfernt, damit die korrigierte Version nicht blockiert wird.
- Die Hilfe beschreibt Tutorials, Gruppen, Listenansicht, Browser-Schließen und den automatischen Vorabcheck-Ablauf.

## Prüfgrenzen

Automatisiert geprüft sind die Python- und API-Pfade einschließlich Gruppen, Migration, Kontexttoleranz, Kandidatenzahl, Pillow-Auflösung und Plan-Neuversionierung sowie der TypeScript-/Vite-Build. Nicht in dieser Umgebung geprüft wurden ein echter Windows-Browserstart mit Schließen, reale LM-Studio-Modelle, GPU-/VRAM-Verhalten, ein echter Aider-Entwicklungslauf, Docker Desktop und das Löschen eines produktiven Benutzerdatenordners. Diese Grenzen stehen ausführlich im [konsolidierten Testbericht](../../TESTBERICHT.md).
