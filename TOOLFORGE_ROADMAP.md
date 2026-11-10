# Entwicklungspfad — Stand V1.0

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

## Querschnitt V1.0

- Projektgruppen und Kachel-/Listenansicht für wachsende Projektbestände.
- Geführte UI- und Entwickler-Tutorials mit Wiederaufruf über die Hilfe.
- Modell-Vorabcheck mit drei bis sechs Kandidaten, kleinen Kontexttoleranzen und Ein-Klick-Ablauf bis zum Start.
- Automatische Auflösung fehlgeschlagener Quelltext-Builds (z. B. Pillow) über PyPI-Wheels und optionale Recherche.
- Sauberes Beenden inklusive des von ToolForge gestarteten Chrome-/Edge-App-Fensters.
- Deinstallationsskript für eigene Umgebungen und Buildartefakte.

Grenzen und Bedienung stehen in README.md. Noch offen: Git-Branches/Push/Pull, Debugger, parallele Workflow-Ausführung und Mehrfacheingänge. Die Verfügbarkeit der Funktionen bedeutet nicht, dass beliebiger vom Modell erzeugter Code fachlich korrekt ist. Details: ABNAHME_V10.md.
