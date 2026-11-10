# Testbericht ToolForge Pilot V1.0

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

Umgebungsdaten: `TEST_ENVIRONMENT_V10.json`. Vollständiger Anforderungsabgleich: `ABNAHME_V10.md`.
