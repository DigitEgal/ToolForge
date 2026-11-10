# Testbericht Version 0.7 – 09.11.2026

- `python -m pytest -q tests backend/tests`: **104 bestanden**, eine Deprecation-Warnung der FastAPI/Starlette-Testumgebung.
- `npm run build`: TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich. Bestehende Größenwarnung zum JavaScript-Bundle (>500 kB).
- Neue Prüfungen: sequenzielle Wechsel, persistierte Arbeitsproben, ungültige Kandidaten, fehlende Modelle, Kontextüberschreitung, fehlgeschlagenes Entladen, abweichender geladener Kontext, Abbruch, ungültige Auswertung/Sieger, ungültige Proben, Fehler beim abschließenden Entladen, veraltete Einstellungen sowie kompletter Session-Ablauf von Vergleich über Übernahme bis Planerstellung.
- LM-Studio-Antworten in diesen Tests sind simuliert. Kein echter Modellserver, GPU-Speicherbenchmark oder Qualitätsvergleich auf Nutzerhardware.
- Visuelle Browserprüfung nicht abgeschlossen: Chromium war nicht installiert, beide Downloadversuche lieferten ungültige Archive. Die Oberfläche wurde kompiliert, aber hier nicht im Browser visuell verifiziert.

Die früher im Gespräch genannten 107 Tests sind keine Testzahl dieses Pakets. Maßgeblich ist der oben angegebene hier ausgeführte Lauf.
