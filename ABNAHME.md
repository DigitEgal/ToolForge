# Anforderungsabgleich V1.2

Basis: ToolForge V1.1 einschließlich aller Regressionen aus 0.1 bis V1.1. Geprüft wurde der Code-, API- und UI-Stand. Reale GPU-, Docker-, Aider-, Tray- und Signaturprüfungen bleiben im Testbericht gesondert abgegrenzt; die automatisierten Tests verwenden dafür isolierte Projekte und simulierte Schnittstellen.

Historische Abgleiche: [0.8](docs/archiv/ABNAHME_V08.md) · [V1.0](docs/archiv/ABNAHME_V10.md) · [V1.1](docs/archiv/ABNAHME_V11.md)

## V1.2-Pflichtpunkte

| ID | Anforderung | Umsetzung | Beleg |
|---|---|---|---|
| V12-1 | V7-Logo als Tool-Logo verwenden | `frontend/src/BrandMark.tsx` importiert `frontend/logos/LogoV7_OnlyLOGO.png` und rendert es als quadratisches Bild. Sidebar, Abschlussbildschirm und Willkommensdialog verwenden denselben Wrapper; die Größe wird über `.brand-logo` und responsive Regeln gesteuert. | Quellprüfung, TypeScript-/Vite-Build, Headless-Chrome-Screenshot. |
| V12-2 | „by DigitEgal“ etwas vergrößern und „DigitEgal“ durch die V6-Wortmarke ersetzen | `frontend/src/DigitEgalLogo.tsx` zeigt „by“ plus `LogoV6_textONLY.png`. Die Wortmarke hat 20 px Bildhöhe (Sidebar 18 px), das „by“ 13 px (Sidebar 12 px); der Sidebar-Eintrag ist horizontal zentriert. Das Seitenverhältnis 2657 × 748 bleibt durch `width:auto` erhalten. Eine dunkle, kleine Trägerfläche hält die weißen Bildbuchstaben auch im hellen Design lesbar. Es bleibt genau ein Link auf <https://digitegal.de>. | Quellprüfung, Bildmaße, Build, Screenshot in Dark und Light. |
| V12-3 | Testberichte zusammenführen und Altlasten entfernen | `TESTBERICHT.md` enthält den aktuellen V1.2-Bericht und die Archivabschnitte 0.1–0.6, 0.7, 0.8, V1.0 und V1.1. Die Einzelberichte und separaten Umgebungsdateien wurden entfernt. Historische Anforderungsabgleiche liegen unter `docs/archiv/`; nicht mehr verwendete SVG-Logo-Duplikate und das reine Linkdokument `IMPLEMENTATION_PLAN.md` wurden entfernt. | Dateibaum, Linkprüfung, `git status`. |
| V12-4 | Architektur und Ladegeschwindigkeit verbessern | `App.tsx` lädt `PilotPanel`, `HelpPanel` und `ProjectManager` per `React.lazy`/`Suspense`. `PilotPanel` lädt `AdvancedPanel` und `DeveloperPanel` erst beim Öffnen des jeweiligen Tabs; `DeveloperPanel` lädt den CodeMirror-Editor erst beim Öffnen einer Datei. Der initiale JavaScript-Block sank von 954,99 kB auf 261,38 kB (80,99 kB gzip). Der Editor bleibt als separater 611,61-kB-Block ausschließlich bei Bedarf. | `npm run build`, Chunk-Ausgabe, Quellprüfung. |
| V12-5 | Statische Assets schneller wiederholen | Die HTTP-Middleware setzt für `/assets/` `Cache-Control: public, max-age=31536000, immutable`; `/api/` bleibt `no-store`, `index.html` bleibt `no-cache`. Vite erzeugt gehashte Dateinamen, sodass neue Versionen sofort neue URLs erhalten. | `backend/tests/test_api.py::test_version_and_static_cache_headers`; realer Smoke-Test. |
| V12-6 | Version im gesamten Projekt auf V1.2 anheben | FastAPI und `/api/workbench` melden `1.2.0`, die Workbench-Stage ist `12`. Frontend-Paket und Lockfile tragen `1.2.0`; Sidebar, Roadmap, Startbanner, Setup-Ausgabe, Hilfe, Installer, Buildskript und Dokumentation nennen V1.2 beziehungsweise zwölf Etappen. | API-Test, Quellprüfung, `npm run build`. |
| V12-7 | Alle bisherigen Funktionen weiter prüfen | Die vollständige V1.1-Suite bleibt erhalten; hinzugekommen ist die Prüfung von Version, Stage und Asset-Cache. Ergebnis: **150 bestanden**, eine bekannte Starlette-TestClient-Warnung, kein Fehlschlag. | [TESTBERICHT.md](TESTBERICHT.md), vollständiger Testlauf. |

## Marken- und Versionsabgleich

- Tool-Logo: `LogoV7_OnlyLOGO.png` (1815 × 1815, transparent) in Sidebar, Shutdown-Karte und Tutorial-Willkommen.
- Wortmarke: `LogoV6_textONLY.png` (2657 × 748, transparent) mit Größenverhältnis 3,55 : 1; keine Verzerrung durch feste Breite.
- Der Link „by DigitEgal“ bleibt ein einzelner, extern geöffneter Link ohne zusätzliches SVG-„D“.
- API: `1.2.0`; Workbench: Stage `12`; Frontend: `1.2.0`; Installer-Definition: `1.2`.
- Die zwölfte Etappe heißt **Marke & Performance** und beschreibt Branding, konsolidierte Berichte und geteilte Ladebereiche.

## Teständerungen gegenüber V1.1

- `backend/tests/test_api.py` erwartet API-Version `1.2.0` und Workbench-Stage `12`.
- Neuer Test `test_version_and_static_cache_headers` prüft `index.html` (`no-cache`), gehashte Assets (`immutable`) und die FastAPI-Version.
- Die bisherigen V1.1-Tests für Index, Plan-Diff, Graph, Anwendungsabnahme, Benchmarks, Recherche, Umgebungen, Export/Import, Logrotation, SSE und Sandbox bleiben unverändert aktiv.
- `npm run build` prüft weiterhin TypeScript und den Produktionsbuild; die einzige große Chunk-Warnung betrifft den bewusst verzögert geladenen CodeMirror-Editor.

## Prüfgrenzen

- Die automatisierten Tests simulieren LM-Studio-, Docker- und Modellantworten. Reale Modellqualität, VRAM-Werte, Tokens/s und Quantisierungen müssen auf der Zielhardware gemessen werden.
- Ein echter Docker-Build, ein realer Aider-Lauf und ein signierter Installer wurden in dieser Umgebung nicht ausgeführt. Der Installer ist vorbereitet; ohne Zertifikat bleibt er unsigniert.
- Die Browser-Abnahme nutzt einen installierten Chrome/Edge im Headless-Modus. Ohne Browser schlägt ein deklariertes Browser-Szenario nachvollziehbar fehl.
- Tray und Browser-App-Fenster werden nur gestartet, wenn die jeweiligen optionalen Komponenten beziehungsweise Browser vorhanden sind.
- Ein visueller Screenshot ersetzt keine vollständige Bedienabnahme aller Tutorial-Schritte auf jedem Zielsystem.
