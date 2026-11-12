# Nützliche nächste Optimierungen (Stand V1.3)

Die V1.3-Punkte sind umgesetzt; Details stehen in [ABNAHME.md](ABNAHME.md). Der initiale JavaScript-Block liegt weiterhin bei rund 261 kB, der Editor wird separat geladen. Offen bleiben vor allem Zielsystem-, Mess- und Komfortarbeiten:

1. **Automatisierte UI-Abnahme:** Geführte Tutorials, Projektgruppen, Kachel-/Listenansicht, Plan-Vorschau und den Ein-Klick-Ablauf mit einem echten Browser-End-to-End-Test absichern. Die aktuelle Prüfung beschränkt sich auf TypeScript, Produktionsbuild, Screenshots und einzelne Headless-Szenarien.
2. **Zielhardware-Messreihe:** Reale LM-Studio-Läufe für mehrere Quantisierungen, Kontexte und Aufgabentypen durchführen und die gemessenen Empfehlungen in Presets dokumentieren.
3. **Docker-Zielsystemabnahme:** Image-Build, interne Netzwerke, Loopback-Ports und Paketinstallation mit laufendem Docker-Daemon prüfen.
4. **Signierter Installer:** Inno Setup und ein Code-Signaturzertifikat auf einem Build-Rechner bereitstellen, Installer bauen, signieren und Installation/Deinstallation testen.
5. **Tray-Abnahme:** `requirements-tray.txt` auf Windows installieren und Start, Öffnen, Beenden sowie Absturzverhalten des Tray-Symbols prüfen.
6. **Recherche-Anbieter:** Neben DuckDuckGo einen zweiten optionalen Anbieter mit gleicher Domain-/Belegprüfung evaluieren; Suchlatenz und Ausfallverhalten messen.
7. **Große Projekte:** Index und Kontextbudget mit mehreren tausend Dateien und langen Monorepos belastbar messen; gegebenenfalls weitere Kürzungs- und Priorisierungsstrategien ergänzen.
8. **Backend-Latenz:** Snapshot-Erzeugung, SQLite-Zugriffe und Verzeichnis-Scans bei sehr großen Projekten profilieren; messbare Engpässe gezielt optimieren.
