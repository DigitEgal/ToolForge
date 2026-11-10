# Projektstand V1.1

ToolForge Pilot V1.1 ist der aktuelle Funktionsstand. Die zehn V1.1-Optimierungen sind umgesetzt und durch 149 automatisierte Tests sowie einen lokalen API-/SSE-Smoke-Test abgesichert. Der vollständige Abgleich steht in [ABNAHME_V11.md](ABNAHME_V11.md); Testumfang und Grenzen in [TESTBERICHT_V11.md](TESTBERICHT_V11.md).

Die Webworkbench ist der aktuelle Funktionsumfang. Der ältere Tkinter-Pilot enthält nicht die neuen Webbereiche. Bitte neue Funktionen über `Start_ToolForge.cmd` nutzen.

## V1.1-Schwerpunkte

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
