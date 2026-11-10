# Anforderungsabgleich Version 0.8

> **Historischer Stand 0.8.** Aktueller Abgleich: [ABNAHME_V10.md](ABNAHME_V10.md). Die hier dokumentierten Funktionen sind in V1.0 erhalten; die Regressionstests stehen im aktuellen Bericht.

Die Aufgabenliste enthält sechs nummerierte Probleme (auch wenn einleitend fünf genannt wurden). Alle sechs wurden berücksichtigt. „Implementiert“ beschreibt den Code- und UI-Stand; reale Windows-/GPU-/Docker-Tests sind gesondert im Testbericht abgegrenzt.

## Neue Probleme

| ID | Lösung | Prüfbeleg |
|---|---|---|
| P1 Aider fehlt | Setup installiert Aider in eigener Umgebung, prüft Version und benötigte Optionen; eigener Interpreter in Einstellungen | Setup-Test; Adapter-Regressionsprüfungen |
| P2 Prüfwerkzeuge verweigert | Expliziter Installationsklick gibt nur pytest/Ruff/mypy einmalig frei; Projektumgebung und Journal bleiben Pflicht | Einmalfreigabetest, keine Änderung von allow_pip |
| P3 CMD/API-Ausgaben | Hidden-Launcher, deaktivierte Access-Logs, UI-Beenden, instanzbezogener Stop-Wächter, Debugstart | Quellprüfung und API-/Startpfade; Windows-Lauf offen |
| P4 Rückfrage stoppt alles | Bestehende unabhängige Ausführung erhalten, Planungsvorgaben verbessert, Blockierungsgründe sichtbar, Antworten vor nächstem Auftrag priorisiert | Mehrfachfragen, Reihenfolge a–b–a–c, Antwort während laufender Aufgabe |
| P5 Fortschritt zurückgesetzt | Aufgabenbezogene Belege, nur betroffene Aufgaben und Abhängigkeiten erneut prüfen; „umgesetzt“, „aktuell geprüft“, „erneut prüfen“ getrennt; Abschlussintegration | Unabhängige Aufgabe bleibt VERIFIED; unveränderte Aufgabe nicht erneut editiert; Vertragsänderung invalidiert |
| P6 Immer kleinere Aufgaben | Diagnose wählt Umgebung/Verbindung, gezielte Reparatur, Format-/Umfangskorrektur oder echte Kontextaufteilung; Webhinweise optional | Strategieklassifikation; Kontextaufteilung bleibt getestet |

## Sieben Verbesserungen

| ID | Umsetzung | Prüfbeleg |
|---|---|---|
| V1 Pause zurücknehmen | Ausstehendes Pause-Event in Session und Engine löschen | Widerrufstest |
| V2 Erweiterungen/Tabfolge | Verbesserungen zuerst; Zusatzpläne mit neuen IDs, Zustanderhalt, Dateikonfliktabhängigkeiten; Queue an Aufgabengrenzen | Additiver Plan-/Fehler-/Queue-Test; Browserflow |
| V3 KI-Vorschläge | Sieben wählbare Kategorien, Modellvorauswahl, begrenzte Bestandsanalyse mit Abdeckungsanzeige, Einzelwahl, Bestätigung, Veraltungsprüfung | Browser inklusive Auswahl/Einplanung; veraltete Vorschläge abgelehnt |
| V4 Hilfe | Vier Dokumente in Hauptnavigation; modellgestützter Hilfechat mit Dokumentkontext | Browserfrage und Antwort; Dokumentabdeckung |
| V5 Hinweiston | Ton bei neuem Frageereignis, Lautstärkeregler, Stummschaltung, Testton; Browserinteraktion nötig | React/TypeScript geprüft; UI-Steuerung vorhanden, akustische Wahrnehmung nicht hier geprüft |
| V6 DuckDuckGo | Opt-in, nur DuckDuckGo, kurze abgeleitete Fehleranfrage, begrenzte Treffer, jeder Versuch in websearch.jsonl | Ausgeschaltet ohne Netzwerkaufruf; Providerzwang und Fehlerjournal simuliert |
| V7 Detaildiagnose | Opt-in, Detaildaten/Tracebacks, Redaktion von Schlüsseln; Schalter ab nächster Aufgabengrenze | Redaktionstest, Laufzeitflag-Test |

## Frühere Anforderungen erneut geprüft

| Version | Vollständiger Funktionsumfang aus der Liste | Stand |
|---|---|---|
| 0.7 | Bis zu drei Modelle, Arbeitsproben, Temperaturen, allgemeine Auswertung, Entladen vor Laden, 15 Modellvarianten/Preset-Hinweise, 20.000 Startkontext | Beibehalten; Backendtests und Browserlauf mit drei Modellen/sechs Proben, Übernahme und Planerstellung |
| 0.6 / 02 | Dateibaum, Codeeditor, sicheres Speichern | Beibehalten; Pfad-/Konflikt-/Backupprüfungen |
| 0.6 / 03 | Python-Umgebung, Start, Abbruch, Live-Ausgabe | Beibehalten; Prozess-/Abbruchtests |
| 0.6 / 04 | Tests, Linting, Typprüfung | Beibehalten; einmalige Werkzeuginstallation korrigiert |
| 0.6 / 05 | Git-Diff, Commit, Historie | Beibehalten; Git-/API-Regressionsprüfungen |
| 0.6 / 06 | Modellanbindung, kontrollierte Dateiänderungen | Beibehalten; Diff-/Versionskonfliktprüfungen |
| 0.6 / 07 | Visuelle Workflows und Toolverbindungen | Beibehalten; Workflowvalidierung und Browser-Tab geprüft |
| 0.6 / 08 | CSV validieren, deduplizieren, Excel exportieren | Beibehalten; automatisierte Abnahmetests |
| 0.6 / 09–10 | Sandbox und verbindbare Sandbox-Netzwerke | In der Ausgangsversion nicht vorhanden; jetzt optional für Projektbefehle implementiert, Docker-Kommandos/Netzwerkoptionen/Cleanup getestet; echter Docker-Lauf offen |
| 0.5 / P1 | Generierten Plan anzeigen, als JSON speichern und aktivieren; Import | Beibehalten; API- und Browserprüfungen |
| 0.5 / Funktion1 | Umbenennen, Archivieren, Löschen mit kontrollierter Paketbereinigung | Beibehalten; geteilte/globale Pakete und wiederherstellbare Löschung getestet |
| 0.5 / Reihenfolge | Unabhängige Aufgaben trotz offener Fragen, Antworten neu priorisieren | Beibehalten und Blockierungsanzeige ergänzt |
| 0.5 / Fehlermeldungen | Frische Aider-Aufrufe ohne benötigten Summarizer; Rückmeldedatei bestimmt IDs; pytest über python -m | Adapter-/Meldungs-/Interpretertests; kein echter Aider-LLM-Lauf hier |
| 0.4 | Schleifen-/Tokenlimits erkennen, frischer Kontext, begrenzte Neuplanung und Gesamtprüfung | Beibehalten; Strategieauswahl vor Aufteilung ergänzt |
| 0.3 / P1 | Windows-Konsole / prompt_toolkit | Batch-Flags, keine Fancy-Eingabe, getrennte Aider-Umgebung; Windows-Zieltest offen |
| 0.3 / P2 | JSON direkt speichern und nutzen | Beibehalten |
| 0.3 / P3 | Modellwarnungen/Website verhindern, Metadaten übergeben | Adapter-Argumenttests |
| 0.3 / P4 | Kontextgröße hinterlegen | Profilvalidierung, geladene Instanz prüfen |
| 0.3 / P5 | Plan mit Modell/Kontext abgleichen, neue Version speichern | Beibehalten; unveränderte fertige Aufgaben bewahren |
| 0.3 / P6–7 | Fehler vor Rückfrage diagnostizieren; konkrete Frage | Beibehalten; optionale Recherche und Strategieprotokoll ergänzt |
| 0.3 / P8 | Temperatur einstellbar | Einstellungen und modellbezogene Profile erhalten |
| 0.3 / P9 | Protokolle im Projekt, Ordner aufrufbar | Beibehalten; neue Journale ebenfalls unter .toolforge |
| 0.2 / 1 | Projekt einlesen, Dashboard, fortsetzen | Beibehalten; Status-/API-Tests |
| 0.2 / 2–4 | Automatische pip-/Chocolatey-/npm-Freigaben | Getrennte Freigaben erhalten; explizite Prüftoolinstallation ändert diese nicht |
| 0.2 / 5 | Installationsübersicht und README | Journale erhalten; manuelle Prüfwerkzeuginstallation aktualisiert auch den Projektstatus |

## Zusätzliche notwendige Korrekturen

- Assistenzanfragen stellen das Arbeitsmodell auch bei Fehlern wieder her.
- Abgebrochene Erweiterungsplanung wird nach Neustart als unterbrochen angezeigt, nicht endlos als laufend.
- Stopp verhindert die nachträgliche Übernahme eines gerade generierten Erweiterungsplans.
- Sandbox-Kommandos erhalten Python-Escapezeichen unverändert; nach Timeout wird der Container selbst entfernt.
- Docker-Neubau überschreibt ein angepasstes Dockerfile nicht.
- Integrationsprüfung hat eine Wiederholungsgrenze für nur in Kombination fehlschlagende Tests.
- Entwicklungsbereich fragt seinen Jobzustand nur ab, wenn er sichtbar ist; Access-Log-Spam entfällt.
- Hilfe und Assistenzfelder haben eigene Abstände und umbrechende Buttons für schmale Ansichten.

- Reine Python-/Prüf-/Workflowjobs blockieren den Modellserver-Lock nicht. So können verschiedene Projektcontainer gleichzeitig laufen und das freigegebene interne Netzwerk nutzen. Modellverwendende Aufträge bleiben serialisiert.
