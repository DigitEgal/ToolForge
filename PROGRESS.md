# Projektstand V1.3

ToolForge Pilot V1.3 ist der aktuelle Funktionsstand. V1.3 ergänzt kostenlose OpenCode-Modelle ohne Zusatzkonto, klar wählbare Modellquellen-Presets statt riskanter Free-Modellwechsel, mehr Zuverlässigkeit für kleine Modelle sowie einen reparierten Desktop-Pilot und einen wiederholbaren Vorabcheck; alle Funktionen aus V1.2 bleiben erhalten. Die vollständige Suite umfasst **174 automatisierte Tests** und lief mit einer bekannten Starlette-TestClient-Warnung ohne Fehlschlag.

Der vollständige Abgleich steht in [ABNAHME.md](ABNAHME.md); Testumfang, Umgebung und Grenzen in [TESTBERICHT.md](TESTBERICHT.md). Die Umsetzung ist im [Entwicklungspfad](TOOLFORGE_ROADMAP.md) als dreizehnte Etappe eingeordnet.

## V1.3-Schwerpunkte

- OpenCode Free als Modellquelle: lokaler Dienst, keine zusätzlichen Zugangsdaten, Nutzung für Vorabcheck, Planung, Hilfe und Aider-Brücke; Konsole und Status nur auf Klick.
- Sechs Modellquellen-Presets (Nur Lokal, Nur Free, Nur API, Free & Lokal, Lokal & API, Free & API) mit den Reihenfolgen MAX Quality, Preis/Leistung und Kostensparend; pro Quelle ein eigenes Modellfeld.
- Alle Free-Modelle teilen sich das Tageskontingent. Ein Modellname wechselt kein Kontingent; bei Erschöpfung wird nur auf erlaubte lokale oder bezahlte API-Quellen ausgewichen.
- Kleine Modelle: kompaktere Projektübersicht, ganze Dateien statt riskanter Diffs, Top-p-Steuerung, strengere Formatprüfung und Syntaxfehler mit Zeilenausschnitten.
- „Pilot öffnen“ startet das Desktop-Fenster tatsächlich; Fehlstarts nennen das Startprotokoll.
- Vorabcheck bleibt nach Fehlern sichtbar und lässt sich mit gespeicherten Kandidaten erneut ausführen; geänderte Aufgabe oder Quellen-Vorauswahl werden markiert, übersprungene Kandidaten und gemessene Ausweichquellen angezeigt.
- API `1.3.0`, Workbench-Stage `13`, Frontend `1.3.0`, Installer `1.3`.

## Funktionsbasis aus V1.2

- V7-Logo und V6-DigitEgal-Wortmarke in Sidebar, Abschlussbildschirm und Tutorial.
- Cockpit, Hilfe, Projektverwaltung, Analyse, Entwicklungsbereich und Codeeditor werden erst bei Bedarf geladen.
- Initialer JavaScript-Block rund 261 kB; CodeMirror bleibt ein separater Block.
- Gehashte Vite-Assets sind langfristig cachebar; `index.html` bleibt `no-cache`.
- Konsolidierter Testbericht und archivierte historische Anforderungsabgleiche.

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
