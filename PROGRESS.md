# Projektstand V1.2

ToolForge Pilot V1.2 ist der aktuelle Funktionsstand. V1.2 führt das neue Branding, einen aufgeräumten Dokumentationsstand und eine deutlich kleinere Startlast ein; alle Funktionen aus V1.1 bleiben erhalten. Die vollständige Suite umfasst **150 automatisierte Tests** und lief mit einer bekannten Starlette-TestClient-Warnung ohne Fehlschlag.

Der vollständige Abgleich steht in [ABNAHME.md](ABNAHME.md); Testumfang, Umgebung und Grenzen in [TESTBERICHT.md](TESTBERICHT.md). Die Umsetzung ist im [Entwicklungspfad](TOOLFORGE_ROADMAP.md) als zwölfte Etappe eingeordnet.

## V1.2-Schwerpunkte

- V7-Logo als Tool-Marke in Sidebar, Abschlussbildschirm und Tutorial.
- „by DigitEgal“ mit der V6-Wortmarke als Bild, passend skaliert und auch im hellen Design lesbar.
- Cockpit, Hilfe, Projektverwaltung, Analyse, Entwicklungsbereich und Codeeditor werden erst bei Bedarf geladen.
- Initialer JavaScript-Block: rund 261 kB statt rund 955 kB; CodeMirror bleibt ein separater, bedarfsgeladener Block.
- Gehashte Vite-Assets dürfen ein Jahr lang unverändert im Browser-Cache liegen; `index.html` bleibt `no-cache`.
- Ein konsolidierter Testbericht ersetzt die versionsspezifischen Einzelberichte und Umgebungsdateien.
- Historische Anforderungsabgleiche und die Basisspezifikation liegen im Ordner `docs/archiv/`.
- API `1.2.0`, Workbench-Stage `12`, Frontend `1.2.0`, Installer `1.2`.

## Funktionsbasis aus V1.1

- Inkrementeller Projektindex mit Symbolen, Importen, Abhängigkeiten und belegter Kontextabdeckung.
- Empirische Modell-/Kontextmessung mit Wiederholungen, Qualitätsstreuung, Tokens/s und VRAM-Spitzen.
- Plan-Vorschau mit Risiko, Aufwand, Abhängigkeiten und betroffenen geprüften Teilen.
- Anwendungsabnahme über deklarierte CLI-, HTTP- und Headless-Browser-Szenarien; Teständerungen werden gesondert geprüft.
- Gepinnte Aider-/Controller-Umgebungen, Docker-Digests und portable Presets.
- Aufgaben-Graph mit Prioritäten, Blockierungen und ausdrücklicher Freigabe paralleler Dateikonflikte.
- SSE-Aktualisierung und globale Rückfragenbenachrichtigung; langsames Polling bleibt Fallback.
- Recherche mit Domainfilter, geöffneten Quellen, Textbelegen und Cache.
- Projekt-Export/Import, Logrotation, Plan-Sicherungen, optionales Tray und vorbereiteter Windows-Installer.
- Sandbox-Ressourcenregler, Image-/Netzwerkverwaltung, Loopback-Ports und Container-Paketinstallation.

Optionale nächste Schritte stehen in [NAECHSTE_SCHRITTE.md](NAECHSTE_SCHRITTE.md).
