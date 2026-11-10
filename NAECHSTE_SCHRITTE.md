# Nützliche nächste Optimierungen (Stand V1.0, noch nicht umgesetzt)

1. **Vollständige, inkrementelle Projektanalyse:** Dateisymbole/Abhängigkeiten indexieren, Änderungen gezielt neu lesen und große Projekte in mehreren belegten Teilschritten analysieren. Derzeit werden Quelltextausschnitte mit Abdeckungsanzeige verwendet.
2. **Empirische Modell-/Kontextoptimierung:** Mehrere Kontextgrößen, wiederholte Arbeitsproben, Tokens/s, VRAM-Spitzen und Qualitätsstreuung messen; Ergebnisse pro Hardware, Modellquantisierung und Aufgabentyp zwischenspeichern. Die aktuelle Familienvorauswahl allein belegt kein bestes Modell.
3. **Plan-Diff und Änderungsvorschau:** Vor Übernahme größerer Erweiterungen einen visuellen Vergleich von Abhängigkeiten, Aufwand, neuen Tests und betroffenen bereits geprüften Teilen anbieten.
4. **Abnahme durch echte Anwendungsszenarien:** Automatisierte Browser-/CLI-Abnahme des entwickelten Zieltools statt ausschließlich vom Plan deklarierter Tests; Teständerungen gesondert reviewen.
5. **Reproduzierbare Umgebungen:** Versionsgebundene Aider-/Prüfwerkzeugpakete, Docker-Digests und exportierte Presets samt Installations-Lockfiles. Aktuell verwendet das Setup die bei Installation auflösbare Aider-Version und prüft deren benötigte Schnittstelle.
6. **Aufgabenansicht als Graph:** Blockierungen und Dateikonflikte visuell darstellen; fachliche Prioritäten und explizite Freigabe gemeinsamer Dateien ergänzen.
7. **Ereignisbasierte Aktualisierung:** Server-Sent Events anstelle regelmäßiger Statusabfragen, globale Rückfragenbenachrichtigung auch außerhalb des Projektcockpits.
8. **Recherchequalität:** Domainfilter, Quellenöffnung mit Textbelegen, Suchcache und nachprüfbare Zuordnung eines Recherchetreffers zur Fehlerbehebung. Derzeit werden Suchtreffer-Snippets verwendet.
9. **Betrieb und Wiederherstellung:** Tray-Symbol, signierter Windows-Installer, einheitlicher Export/Import kompletter Projekte, Rotation der Diagnosejournale und Sicherung vor jeder größeren Planänderung.
10. **Sandbox-Komfort:** Image-/Netzwerkverwaltung und Ressourcenregler in der UI, freigebbare Ports für Vorschauen, Paketinstallation gezielt im Container. Derzeit werden Projektimages bewusst separat gebaut.
11. **Frontend-Code-Splitting:** Das Vite-Bundle liegt nach dem V1.0-Ausbau bei rund 926 kB (309 kB gzip). Editor, Workflows und seltene Panels per dynamischem Import aufteilen und den 500-kB-Hinweis beseitigen.
12. **Automatisierte UI-Abnahme:** Geführte Tutorials, Projektgruppen, Kachel-/Listenansicht und den Ein-Klick-Ablauf mit einem echten Browser-End-to-End-Test absichern. Die aktuelle Prüfung beschränkt sich auf TypeScript und Produktionsbuild.
