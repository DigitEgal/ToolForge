# Entwicklungspfad — Stand V1.1

01 Projektverwaltung und Pilot: integriert.
02 Entwicklungsbereich: Dateiliste nach Ordnerpfaden, CodeMirror-Editor, konfliktgeprüftes Speichern und Sicherungen.
03 Python ausführen: Projektumgebung, Argumente, Live-Protokoll, Abbruch.
04 Prüfen & testen: pytest, Ruff und mypy mit dokumentierter optionaler Installation.
05 Git-Versionierung: Initialisierung, Status, Diff, ausgewählte Commits und Historie.
06 KI-Unterstützung: LM-Studio-Vorschläge mit Diff und ausdrücklicher Übernahme.
07 Visuelle Workflows: Knotengraph, Eingangsverknüpfungen, Validierung und sequenzielle Ausführung.
08 Durchgängige Abnahme: CSV prüfen, Duplikate entfernen, Excel exportieren und Ergebnis prüfen.
09 Docker-Ausführung für Projektbefehle: optional integriert.
10 Explizite interne Sandbox-Netzwerke: integriert; Docker Desktop separat erforderlich.
11 Analyse & Betrieb: inkrementeller Index, empirische Messreihen, Plan-Vorschau, Anwendungsabnahme, Aufgaben-Graph, Recherchebelege, Presets, Export/Import, Logrotation, Tray und Installer.

## Querschnitt V1.1

- Vollständige inkrementelle Projektanalyse mit Symbolen, Abhängigkeiten und belegter Kontextabdeckung.
- Empirische Modell-/Kontextmessung pro Hardware, Quantisierung und Aufgabentyp.
- Plan-Vorschau vor Übernahme größerer Änderungen inklusive Risiko, Aufwand und betroffenen geprüften Teilen.
- Echte CLI-/HTTP-/Browser-Anwendungsabnahme mit getrennter Teständerungsprüfung.
- Reproduzierbare Umgebungen durch gepinnte Aider-/Controller-Pakete, Docker-Digests und Presets.
- Aufgaben-Graph mit Prioritäten und ausdrücklicher Freigabe paralleler Dateikonflikte.
- SSE-Aktualisierung und globale Rückfragen außerhalb des Projektcockpits.
- Recherche mit Domainfilter, geöffneten Quellen und Textbelegen.
- Projekt-Export/Import, Plan-Sicherungen, Logrotation, optionales Tray und vorbereiteter Windows-Installer.
- Sandbox-Ressourcenregler, Loopback-Ports, Image-/Netzwerkverwaltung und Container-Pakete.

Grenzen und Bedienung stehen in README.md. Noch offen: Git-Branches/Push/Pull, Debugger, parallele Workflow-Ausführung und Mehrfacheingänge. Die Verfügbarkeit der Funktionen bedeutet nicht, dass beliebiger vom Modell erzeugter Code fachlich korrekt ist. Details: [ABNAHME_V11.md](ABNAHME_V11.md).
