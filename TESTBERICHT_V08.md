# Testbericht ToolForge Pilot 0.8

> **Historischer Stand 0.8.** Aktueller Bericht: [TESTBERICHT_V11.md](TESTBERICHT_V11.md).

Prüfdatum: 09.11.2026. Basis: bereitgestellte Version 0.7, vollständig erhalten und erweitert.

## Automatisierte Tests

`python -m pytest -q tests backend/tests`: **125 bestanden**, eine Deprecation-Warnung aus Starlette/FastAPI zur TestClient-httpx-Anbindung. Keine fehlgeschlagenen Tests.

Enthalten sind alle bisherigen Tests sowie 21 neue Tests für gezielte Invalidierung, Fortschrittserhalt, Planverträge, unabhängige Aufgaben, Reparaturstrategien, Websuche-Opt-in/Journal, Geheimnisredaktion, Pausewiderruf, einmalige Werkzeuginstallation, additive Erweiterungen, Fehlererhalt, veraltete Vorschläge, Dockerargumente/-Cleanup, Hilfeabdeckung, Laufzeitoptionen, Python-Escapes im Container, Aider-Setup Modellwiederherstellung bei Assistenzfehlern und parallele Nicht-Modelljobs trotz belegtem Modell-Lock.

Ein früherer Test zur sofortigen Aufteilung nach GUARD_REPEAT wurde auf GUARD_CONTEXT umgestellt: Aufteilung nach einem echten Kontextlimit bleibt erforderlich; pauschale Aufteilung bei Wiederholung widerspricht der neuen Anforderung P6. Die neue Strategieprüfung testet ausdrücklich, dass GUARD_REPEAT nicht automatisch aufteilt.

## Frontend

`npm --prefix frontend run build`: TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich. Hinweis des Bundlers: Das JavaScript-Bundle überschreitet 500 kB. Dies ist eine Optimierungsmöglichkeit, kein Buildfehler.

Chromium-Bedienprüfung mit echter lokaler ToolForge-API und simuliertem LM-Studio-Server:

- Projekt anlegen/verbinden und Einstellungen speichern.
- Textuelle Erweiterung einplanen.
- KI-Verbesserungsvorschläge anfordern, auswählen und einplanen.
- Alle sechs Entwicklungstabs in der verlangten Reihenfolge öffnen.
- Hilfe öffnen, Modell wählen und eine dokumentgestützte Antwort anzeigen.
- Modell-Vorabcheck mit drei Kandidaten und zwei Temperaturen: sechs Proben, Auswertung, Übernahme und anschließende Planerstellung.
- Desktopansicht 1440×1000 und schmale Ansicht 390×844; kein horizontaler Dokumentüberlauf, keine JavaScript-Seitenfehler im getesteten Ablauf.
- Screenshots intern auf Darstellung geprüft; Abstände und Buttonumbruch korrigiert.

Die Testantworten belegen die technische Integration, nicht die Qualität realer Modelle. Tonsteuerung wurde kompiliert und visuell geprüft; der tatsächlich hörbare Ton auf der Zielmaschine ist nicht nachgewiesen.

## Nicht als real getestet ausgeben

- Windows-CMD/pythonw/Taskmanager, Installer-Downloads und tatsächliche Aider-Ausführung unter Windows.
- Reale Aider-Entwicklungsläufe mit Nutzerprojekten und lokalem LM Studio.
- VRAM-Verbrauch, GPU-Freigabe, Modellqualität und Quantisierungsvergleich.
- Echter Docker-Imagebau, Containerkommunikation und Docker Desktop unter Windows. Die Befehlsbildung, Netzwerkoptionen und Cleanup-Aufrufe wurden automatisiert simuliert.
- Live-Verfügbarkeit von DuckDuckGo. Providerbindung, deaktivierter Zustand und Fehlerprotokollierung wurden simuliert geprüft.

Das Setup führt auf der Zielmaschine selbst eine echte Aider-Version-/Optionsprüfung aus. Docker-, Modellserver- und Suchfehler werden angezeigt bzw. protokolliert, nicht als erfolgreicher Lauf ausgegeben.

## Empfohlener kurzer Zielsystemtest

1. Setup in einem neuen Ordner ausführen; Aider-Prüfung muss erfolgreich enden.
2. Workbench starten, Hilfedokumente öffnen; über UI und danach über Stop_ToolForge.cmd beenden.
3. Ein kleines Testprojekt mit unabhängigen Aufgaben und einer absichtlichen Rückfrage ausführen; Hinweiston und Antwortfortsetzung prüfen.
4. Vorabcheck mit zwei kleinen installierten Modellen durchführen; nach Übernahme geladenen Kontext in LM Studio vergleichen.
5. Wenn benötigt: Docker-Prüfumgebung bauen und eine harmlose Python-Datei ausführen. Netzwerk erst danach bewusst freigeben.

Umgebungsdaten: TEST_ENVIRONMENT_V08.json. Vollständiger Anforderungsabgleich: ABNAHME_V08.md.
