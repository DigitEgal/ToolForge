# Nützliche nächste Optimierungen (Stand V1.1)

Die zehn V1.1-Punkte aus der vorherigen Liste sind umgesetzt; Details stehen in [ABNAHME_V11.md](ABNAHME_V11.md). Offen bleiben vor allem Zielsystem- und Komfortarbeiten:

1. **Frontend-Code-Splitting:** Das Vite-Bundle liegt weiterhin bei rund 955 kB (316 kB gzip). Editor, Workflows und seltene Panels per dynamischem Import aufteilen und den 500-kB-Hinweis beseitigen.
2. **Automatisierte UI-Abnahme:** Geführte Tutorials, Projektgruppen, Kachel-/Listenansicht, Plan-Vorschau und den Ein-Klick-Ablauf mit einem echten Browser-End-to-End-Test absichern. Die aktuelle Prüfung beschränkt sich auf TypeScript, Produktionsbuild und einzelne Headless-Szenarien.
3. **Zielhardware-Messreihe:** Reale LM-Studio-Läufe für mehrere Quantisierungen, Kontexte und Aufgabentypen durchführen und die gemessenen Empfehlungen in Presets dokumentieren.
4. **Docker-Zielsystemabnahme:** Image-Build, interne Netzwerke, Loopback-Ports und Paketinstallation mit laufendem Docker-Daemon prüfen.
5. **Signierter Installer:** Inno Setup und ein Code-Signaturzertifikat auf einem Build-Rechner bereitstellen, Installer bauen, signieren und Installation/Deinstallation testen.
6. **Tray-Abnahme:** `requirements-tray.txt` auf Windows installieren und Start, Öffnen, Beenden sowie Absturzverhalten des Tray-Symbols prüfen.
7. **Recherche-Anbieter:** Neben DuckDuckGo einen zweiten optionalen Anbieter mit gleicher Domain-/Belegprüfung evaluieren; Suchlatenz und Ausfallverhalten messen.
8. **Große Projekte:** Index und Kontextbudget mit mehreren tausend Dateien und langen Monorepos belastbar messen; gegebenenfalls weitere Kürzungs- und Priorisierungsstrategien ergänzen.
