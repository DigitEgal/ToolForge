# Projektstand V1.4

ToolForge Pilot V1.4 ist der aktuelle Funktionsstand. V1.4 ergänzt die Mehrmodell-Übergabe für steckengebliebene Aufgaben, eine unabhängige Ergebnisprüfung durch andere Modelle, im Vorabcheck und zur Laufzeit konfigurierbare Rollen, einen optionalen Vorabcheck, eine vollständige EN/DE-Oberfläche samt Hilfe und Tutorials sowie einen diagnostizierten Docker-Build; alle Funktionen aus V1.3 bleiben erhalten.

Der vollständige Abgleich steht in [ABNAHME.md](ABNAHME.md); Testumfang, Umgebung und Grenzen in [TESTBERICHT.md](TESTBERICHT.md). Die Umsetzung ist im [Entwicklungspfad](TOOLFORGE_ROADMAP.md) als vierzehnte Etappe eingeordnet.

## V1.4-Schwerpunkte

- Geordnete Übergabeliste `Quelle::Modell`: Das Hauptmodell wird bei wiederholten Fehlversuchen, Hängern, Kontextlimits oder blockierten Aufgaben sequenziell durch die konfigurierten Modelle ersetzt und nach Erfolg wiederhergestellt.
- Unabhängige Ergebnisprüfung nach bestandener Aufgabenprüfung und als abschließendes Projektgate; Ersteller einer Aufgabe und aktives Hauptmodell sind ausgeschlossen.
- Mindestzustimmungen, strenge Ablehnung und Reparatur nach Ablehnung sind einstellbar. Prüfer erhalten genau das konfigurierte Modell ohne stillen Ersatz.
- Übergabe- und Prüferlisten sind im Vorabcheck und unter „Übergabe & Prüfung“ auch während eines Laufs änderbar; die Auswahl wird gegen den aktuellen Modellbestand geprüft.
- Vorabcheck ist optional und über „Vorabcheck überspringen“ abschaltbar; Empfehlungen werden weiterhin nur nach ausdrücklicher Übernahme aktiv.
- Vollständige EN/DE-Oberfläche über `EN | DE` neben Ton und Design, inklusive Hilfe, vier Tutorials, README und Schnellstart; die Auswahl bleibt im Browser gespeichert.
- Docker-Build prüft vor Build-, Netzwerk- und Paketaufträgen die Docker-CLI und den Linux-Daemon und meldet fehlende Daemons sofort statt eines hängenden „Auftrag: failed“.
- API `1.4.0`, Workbench-Stage `14`, Frontend `1.4.0`, Installer `1.4`.

## Funktionsbasis aus V1.3

- OpenCode Free als Modellquelle: lokaler Dienst, keine zusätzlichen Zugangsdaten, Nutzung für Vorabcheck, Planung, Hilfe und Aider-Brücke; Konsole und Status nur auf Klick.
- Sechs Modellquellen-Presets (Nur Lokal, Nur Free, Nur API, Free & Lokal, Lokal & API, Free & API) mit den Reihenfolgen MAX Quality, Preis/Leistung und Kostensparend; pro Quelle ein eigenes Modellfeld.
- Alle Free-Modelle teilen sich das Tageskontingent. Ein Modellname wechselt kein Kontingent; bei Erschöpfung wird nur auf erlaubte lokale oder bezahlte API-Quellen ausgewichen.
- Kleine Modelle: kompaktere Projektübersicht, ganze Dateien statt riskanter Diffs, Top-p-Steuerung, strengere Formatprüfung und Syntaxfehler mit Zeilenausschnitten.
- „Pilot öffnen“ startet das Desktop-Fenster tatsächlich; Fehlstarts nennen das Startprotokoll.
- Vorabcheck bleibt nach Fehlern sichtbar und lässt sich mit gespeicherten Kandidaten erneut ausführen.

## Funktionsbasis aus V1.2

- V7-Logo und V6-DigitEgal-Wortmarke in Sidebar, Abschlussbildschirm und Tutorial.
- Cockpit, Hilfe, Projektverwaltung, Analyse, Entwicklungsbereich und Codeeditor werden erst bei Bedarf geladen.
- Initialer JavaScript-Block rund 261 kB in V1.3, durch V1.4 auf rund 280 kB gewachsen; CodeMirror bleibt ein separater Block.
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
