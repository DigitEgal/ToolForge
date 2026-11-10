# Prüfbericht — ToolForge Pilot 0.6

09.11.2026 · Linux · Python 3.12 · Node.js 24.

- 89 automatisierte Tests bestanden (84,52 Sekunden). Eine Starlette-TestClient-DeprecationWarning ohne Testfehler.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich. Vite meldet einen großen JavaScript-Chunk (889 kB unkomprimiert); der Build ist erfolgreich.
- Neue Tests: sichere Pfade, Speicherkonflikte/Sicherungen, Binärdateien, Python-Ausführung/Abbruch, Git-Commits einschließlich Schutz fremder vorgemerkter Dateien, Workflow-Zyklen, CSV-Validierung, Export-Überschreibschutz und eigene Python-Knoten.
- KI-Vorschläge mit kontrollierter Modellantwort getestet: kein Schreiben vor Übernahme; veraltete Revision wird abgewiesen. Kein reales Sprachmodell in dieser Prüfung.
- API-Test: Dateien schreiben/lesen, Konflikt melden, Pfadausbruch verhindern, Workflow speichern, vollständige Abnahme und XLSX-Download.
- Chromium mit echtem Backend: Datei im CodeMirror-Editor erstellen und speichern, Python starten, Live-Ausgabe prüfen, Git initialisieren und ausgewählte Datei committen, CSV→Excel-Abnahme ausführen und Ergebnis herunterladen. Keine JavaScript-Laufzeitfehler im geprüften Ablauf.
- Desktop-Editor und Workflow-Darstellung visuell geprüft; mobiler Viewport gerendert. Eine zunächst zu kleine SVG-Höhe wurde korrigiert.
- Export zusätzlich unabhängig mit openpyxl gelesen: Kopfzeile name/email und genau zwei Datensätze Ada/Linus. openpyxl ist hierfür nur Testwerkzeug, keine neue App-Abhängigkeit.

## Grenzen der aktuellen Prüfung
Windows-Startskripte, tatsächlicher LM-Studio-/Aider-Betrieb sowie reale Paketinstallation und Chocolatey-Deinstallation wurden hier nicht unter Windows ausgeführt. Die zugehörigen simulierten Regressionstests bestehen. Nicht jedes Layout und jede Kombination von Projektdateien wurde im Browser geprüft. Vollständige Funktionsgrenzen und Bedienung stehen in README.md.

## Frühere Prüfungen

# Prüfbericht — ToolForge Pilot 0.5

09.11.2026 · Linux · Python 3.12 · Node.js 24.

- **77 automatisierte Tests bestanden**, 20,63 Sekunden. Die bekannte Starlette-TestClient-
  DeprecationWarning bleibt ohne Testfehler bestehen.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich.
- Chromium gegen echtes Backend und kontrollierten lokalen Modell-API-Testserver:
  Planantwort zunächst ungültig, Reparatur erfolgreich, Anzeige im aktiven Editor und
  JSON-Datei tatsächlich gespeichert. Anschließend zweimal ungültige Antwort: sichtbarer
  Fehler im Plan-Reiter, vorhandener Plan erhalten.
- Browserprüfung: Umbenennen, Archivieren, Archivansicht, Wiederherstellen, Löschvorschau,
  Namensbestätigung und Entfernen des Projekteintrags. Arbeitsordner dabei erhalten.
  Keine JavaScript-Laufzeitfehler im geprüften Ablauf. Fehleransicht visuell kontrolliert.
- Scheduler-Test: A fragt, B läuft weiter; während B läuft wird die Antwort angenommen;
  anschließend A, danach das von A abhängige C. Alle Aufgaben erfolgreich geprüft.
- Weitere Tests: mehrere offene Fragen, keine Ausführung abhängiger Aufgaben,
  kontrollierte Meldungszuordnung, normalisierte pytest-Kommandos, Paketbereinigung und
  Journal, Schutz gemeinsam genutzter Umgebungen, globale Paketreferenzen einschließlich
  archivierter Projekte, wiederherstellbares Entfernen eines Arbeitsordners.

## Grenzen
Keine reale Windows-/LM-Studio-Integration und keine reale Chocolatey-Deinstallation.
Die Paketmanager-Ergebnisse wurden kontrolliert simuliert; Pfad-/Dateioperationen und
Prozess-/Scheduler-Tests liefen tatsächlich. Der Planer wurde über einen lokalen
HTTP-Testserver geprüft, nicht durch ein echtes Sprachmodell. Die Summarizer-Einstellung
wurde anhand des Aider-Quellcodes und des erzeugten Aufrufs überprüft; die konkrete
Shutdown-Fehlermeldung wurde hier nicht mit einem realen Aider reproduziert.

## Frühere Prüfungen: Version 0.4

Datum: 09.11.2026. Linux, Python 3.12, Node.js 24.

- Vollständiger aktueller Python-Testlauf: **64 bestanden**, 19,87 Sekunden; eine unveränderte Starlette-DeprecationWarning.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich.
- Neue Tests prüfen gestückelte Tokenlimit-Meldungen, wiederholte Dateien/Codeblöcke,
  normale Ausgabe ohne Fehlalarm, Ausgabegrenze, Dateiumfang und echten Prozessabbruch.
- Tests zur Neuplanung prüfen begrenzte Modellanfragen, ungültige Antworten,
  erhaltene Integrationsprüfungen/Abhängigkeiten, Versionswechsel, fortgesetztes Budget,
  erfolgreiche Folgeausführung und das Verbot eines falschen Abschlusses nach Teilprüfungen.
- Der Modell-Teilplaner ist mit kontrollierten API-Antworten getestet. Ein realer
  LM-Studio-/Llama-8B-Lauf und Windows-Integration bleiben nicht durchgeführt.
- Die unten dokumentierte Browserprüfung stammt aus 0.3. Für 0.4 wurde der Frontend-Build
  erneut geprüft; der neue Neuplanungsabschnitt wurde nicht gesondert im Browser abgenommen.

## Vorherige Browser- und Basisprüfung (0.3)

Datum: 09.11.2026. Getestet unter Linux mit Python 3.12 und Node.js 24.

## Tatsächlich ausgeführt

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

Die Browserprüfung verwendete eine isolierte Testdatenbank und einen Testprojektordner.
Sie installierte keine Abhängigkeiten in Benutzerprojekten. Browser-Testwerkzeuge
werden nicht mitgeliefert und sind für den Betrieb nicht erforderlich.

## Abgedeckte automatisierte Fälle

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

## Grenzen der Prüfung

**Nicht auf einem echten Windows-PC ausgeführt:** CMD-Starter, Windows-Konsolenhandles,
Job-Object-Prozessbeendigung, native Ordnerauswahl und Explorer-Aufruf. Die Konstruktion
wurde geprüft, ist aber kein Ersatz für einen echten Windows-Integrationstest.

**Kein echter LM-Studio-/LLM-Lauf:** Der lokale Server des Anwenders ist aus dieser
Testumgebung nicht erreichbar. Modellmetadaten und Aider-Aufrufe wurden gezielt getestet;
der automatische Ende-zu-Ende-Ablauf nutzt den ausdrücklich markierten DemoAdapter.
Die Aider-Optionen und der prompt_toolkit-Initialisierungspfad wurden zusätzlich am
Quellcode von aider-chat 0.86.2 überprüft. Modellqualität und vollständig erfolgreiche
Aider-Edits mit dem konkreten LM-Studio-Modell sind hier nicht nachgewiesen.

**Keine echten Chocolatey-Systeminstallationen:** Freigabe, Kommando und Journal wurden
mit kontrollierten Prozessantworten geprüft. Administratorrechte und konkrete Pakete
müssen auf Windows verifiziert werden.

Eine Starlette-TestClient-DeprecationWarning weist auf eine künftige HTTPX-Umstellung hin.
Sie beeinflusste keinen Test. Der Testlauf enthält keine fehlgeschlagenen oder
übersprungenen Tests.

## Kurzer Windows-Abnahmelauf

1. Setup und normalen Starter ausführen; Workbench muss im Browser erscheinen.
2. Neues leeres Zielprojekt verbinden, Beispielplan laden, Simulation einschalten.
3. Start: drei Aufgaben müssen ohne weiteren Start auf „Geprüft“ wechseln.
4. Protokollordner öffnen: Explorer muss `<Projekt>\.toolforge\logs` anzeigen.
5. Workbench beenden/neustarten, Projekt erneut öffnen: gespeicherter Stand vorhanden.
6. Separates echtes Testprojekt: Simulation aus, Aider-Python und LM-Studio-Modell wählen.
7. Kleine Aufgabe mit messbarer Prüfung starten. Kein prompt_toolkit-Dialog und kein
   Browserfenster für Modellwarnungen; Kontext-/Temperaturwerte in Laufmetadaten prüfen.
8. Jede Installationsfreigabe einzeln mit einem gewünschten Testpaket prüfen; README und
   Journal kontrollieren. Chocolatey nur auf einem geeigneten Testsystem ausprobieren.
