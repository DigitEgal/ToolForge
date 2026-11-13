# Entwicklungspfad — Stand V1.3

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
12 Marke & Performance: V7-Tool-Logo, V6-DigitEgal-Wortmarke, konsolidierte Berichte und verzögertes Laden großer Oberflächenbereiche.
13 OpenCode Free & kleine Modelle: kostenlose Modelle ohne Zusatzkonto, Modellquellen-Presets statt Free-Modellwechsel bei Tageslimits, konfigurierbare Reihenfolge, kompaktere Prompts, ganze Dateien, Top-p und Syntaxprüfung.

## V1.3-Schwerpunkte

- OpenCode Free als lokale Brücke zum kostenlosen OpenCode-Inferenzdienst; kein zusätzliches Konto und kein API-Schlüssel in ToolForge.
- Gemeinsames Free-Tageslimit: Bei Erschöpfung wird die Free-Quelle gesperrt und nur auf erlaubte lokale oder bezahlte API-Quellen ausgewichen; ein anderer Free-Modellname schafft kein zusätzliches Kontingent. Reihenfolge und erlaubte Quellen sind einstellbar.
- Verbesserte Ergebnisse kleiner Modelle durch kompaktere Prompts, Abnahmekriterien, Checklisten, ganze Dateien und eine Syntaxprüfung vor Reparaturschritten.
- Desktop-Pilot-Schaltfläche startet das echte Pilot-Fenster; „Pilot öffnen“ und „Cockpit öffnen“ sind getrennt.
- Vorabcheck nach Fehlern oder Planänderungen mit gespeicherten Kandidaten wiederholbar.
- Versionsstand durchgängig V1.3 beziehungsweise `1.3.0`, Workbench-Stage `13`.

## V1.2-Schwerpunkte

- Einheitliches Branding aus `frontend/logos`: V7-Logo in Sidebar, Abschlussbildschirm und Tutorial, V6-Wortmarke im verlinkten „by DigitEgal“.
- Geteilte Frontend-Bereiche: Cockpit, Hilfe, Projektverwaltung, Analyse, Entwicklungsbereich und Codeeditor werden erst bei Bedarf geladen.
- Der initiale JavaScript-Block sinkt von rund 955 kB auf rund 261 kB; der CodeMirror-Editor bleibt als eigener, bedarfsgeladener Block erhalten.
- Gehashte Vite-Assets werden mit `Cache-Control: public, max-age=31536000, immutable` ausgeliefert; `index.html` bleibt `no-cache`.
- Ein konsolidierter Testbericht ersetzt die versionsspezifischen Einzelberichte; alte Umgebungsdateien und nicht mehr verwendete Logo-Duplikate wurden entfernt.
- Versionsstand durchgängig V1.2 beziehungsweise `1.2.0`, Workbench-Stage `12`.

## Basis aus V1.1

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

Grenzen und Bedienung stehen in README.md. Noch offen: Git-Branches/Push/Pull, Debugger, parallele Workflow-Ausführung und Mehrfacheingänge. Die Verfügbarkeit der Funktionen bedeutet nicht, dass beliebiger vom Modell erzeugter Code fachlich korrekt ist. Details: [ABNAHME.md](ABNAHME.md), [TESTBERICHT.md](TESTBERICHT.md).
