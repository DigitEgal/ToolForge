# LM Studio und Modell-Vorabcheck – ToolForge Pilot V1.4

## Bedienung

1. LM Studio starten, lokalen Server aktivieren. Benötigt wird die Native REST API v1 mit `/api/v1/models`, `/load` und `/unload`. Andere Anwendungen am selben Modellserver während des Vergleichs pausieren.
2. ToolForge über `Start_ToolForge.cmd` öffnen, Projekt verbinden. Unter Einstellungen API-Adresse und gegebenenfalls Token speichern.
3. Unter Aufgabenplan das konkrete Ziel eingeben. Für einen Quellenvergleich einen repräsentativen Text mit Anfang, Mitte, Ende und bekannten Prüfpunkten mitgeben.
4. Im Modell-Vorabcheck ein Testprofil wählen und „Installierte Modelle prüfen & Kandidaten vorschlagen“ drücken. Drei bis sechs Modelle sowie ein allgemeines Auswertungsmodell auswählen. Es werden nur tatsächlich vom Server gemeldete Modellschlüssel verwendet.
5. Kontextbudget prüfen (Ausgangswert 20.000), optional zwei Temperaturen testen. Vorabcheck starten.
6. Arbeitsproben, Laufzeit, Formatprüfung und Bewertung ansehen. „Empfehlung übernehmen & Modell laden“ drücken. Erst danach den Aufgabenplan erzeugen und die Entwicklung starten.
7. Alternativ „Automatisch: Vorabcheck → Empfehlung → Plan → Start“ verwenden. Der Ablauf übernimmt die Empfehlung, erzeugt den Plan und startet die Ausführung ohne weitere Klicks; Fehler werden an der jeweiligen Phase angezeigt.

Kleine Abweichungen zwischen angeforderter und tatsächlich geladener Kontextgröße sind zulässig, wenn der geladene Wert höchstens `max(512, 2 %)` unter der Anforderung liegt. ToolForge übernimmt dann den tatsächlich geladenen Wert als geprüftes Budget. Deutlich kleinere Kontexte werden weiterhin abgewiesen.

## Empirische Messreihe (seit V1.1)

Die Messreihe ergänzt den Vorabcheck um wiederholte Arbeitsproben über mehrere Kontextgrößen. Sie misst Tokens/s aus den Nutzungsdaten, VRAM-Spitzen über die Native API und die Streuung der Qualitätsbewertung. Ergebnisse werden pro Hardware-Fingerprint, Modell, Quantisierung, Aufgabentyp und maximalem Kontext zwischengespeichert und können im Bereich **Analyse & Betrieb** gestartet werden.

Die Empfehlung ist eine gemessene Stichprobe für diese Maschine, keine globale Rangliste. Vor einem Lauf andere Modellserver und GPU-Anwendungen pausieren, dieselbe Probe verwenden und die Quantisierung dokumentieren. Ein Kontext, der auf einer GPU schnell wirkt, kann auf einer anderen Hardware oder bei anderer Quantisierung ungeeignet sein. Die Messreihe ersetzt weder den Vorabcheck noch die fachliche Prüfung der erzeugten Ergebnisse.

Die Weboberfläche enthält diese Funktion. Der separat startbare alte Tkinter-Desktop-Pilot enthält sie nicht. Bestehende Projekte ohne Vorabcheck können weiter manuell arbeiten. Sobald ein Vorabcheck begonnen wurde, ist für Planung/Start eine gültige übernommene Empfehlung erforderlich. Eine geänderte Aufgabenbeschreibung erfordert einen neuen Check vor der Planerstellung; geänderte Einstellungen oder ein extern gewechseltes Modell werden ebenfalls erkannt.

## Ablauf und Grenzen

Alle Kandidaten bekommen dieselbe Arbeitsprobe mit demselben Ausgabelimit. Es werden keine generierten Codeausschnitte ausgeführt. Formatfehler, abgeschnittene Antworten, Antwortzeiten und verfügbare Tokenstatistiken werden gespeichert. Das allgemeine Modell bekommt anonymisierte Proben in gemischter Reihenfolge. Bewertungsgewichtung: Korrektheit 40 %, Erfüllung 30 %, Klarheit 20 %, Laufzeit 10 %. Diese Punkte sind ein Modellurteil, keine objektiv gemessene Korrektheit. Manuelle Prüfung bleibt nötig.

Der Bewerter darf nur eine gültige, tatsächlich getestete Probe empfehlen. Modell und Temperatur werden aus dieser Probe übernommen, Kontext und Ausgabelimit durch die Anwendung festgelegt. Der Kontext wird beim Laden überprüft. Zusätzlich kann die empirische Messreihe mehrere Kontextgrößen auf derselben Hardware vergleichen; sie ersetzt den Vorabcheck nicht, sondern liefert die gemessene Grundlage für die Auswahl. Das Profil „Großer Kontext“ priorisiert ein installiertes Modell mit großer deklarierter Kontextgrenze. Ob es Quellen zuverlässig verarbeitet, zeigt erst eine geeignete Arbeitsprobe; ein großes Limit allein belegt keine Qualität.

Der Speicherwechsel erfolgt sequenziell über die API desselben Servers: alle gemeldeten Instanzen entladen, leere Instanzliste bestätigen, ein Modell laden, Instanz und Kontext bestätigen. Auch das Auswertungsmodell wird am Ende entladen. Bei Fehlern wird abgebrochen. Eine leere Instanzliste ist keine separate Messung des freien GPU-Speichers; externe Anwendungen können weiterhin VRAM belegen. Es gibt keine automatische Verkleinerung des Kontexts nach einem Ladefehler, damit Ergebnisse vergleichbar bleiben. Kontext anschließend reduzieren und erneut starten.

Parallel gestartete ToolForge-Projekte werden innerhalb desselben Serverprozesses gesperrt. Mehrere ToolForge-Prozesse und andere LM-Studio-Clients teilen diese Sperre nicht. Stoppen erfolgt zwischen Serveraufrufen; eine laufende HTTP-Anfrage kann bis zum eingestellten Timeout dauern. Ergebnisse liegen in `.toolforge/preflight.json` und versioniert in `.toolforge/preflight-history/`.

Bei unzureichendem Auswertungskontext bleiben die Proben erhalten; der Lauf endet mit einer konkreten Fehlermeldung. Weniger Temperaturen/Kandidaten oder ein größeres Kontextbudget wählen. Für reasoning-lastige Modelle kann das knappe Proben-Ausgabelimit zu abgeschnittenen Antworten führen; solche Antworten werden ausgeschlossen. Ein fehlgeschlagener kurzer Test bedeutet deshalb nicht automatisch, dass das Modell für die eigentliche Aufgabe ungeeignet ist.

## Standardeinstellungen

- **Kontext:** 20.000 als Ausgangswert behalten, sofern Modell und Speicher ihn unterstützen. Für kurze Aufgaben als eigenen Versuch 8.192 oder 12.288 testen. Kontext enthält Eingabe, Ausgabe und Systemanteile. Ein hoher Wert ist kein allgemeiner Qualitätsregler. Größere Werte müssen tatsächlich geladen werden.
- **Temperatur:** Kein globales Optimum. Für klassische Coding-Instruct-Modelle sind 0,2 und 0,7 sinnvolle Vergleichspunkte; für Präsentationsstruktur 0,4 und 0,8. Das sind eigene Testvorschläge, keine Herstellerstandards. Gemma 4 und gpt-oss starten im Vergleich bei 1,0, Qwen3.5 bei 0,6. Zweiter Vergleichspunkt siehe Tabelle.
- **Weitere Samplingparameter:** Zunächst das passende Modellpreset behalten. Top-p, Top-k, Min-p und Strafen nicht gleichzeitig mit der Temperatur verändern; sonst lässt sich der Unterschied nicht sauber zuordnen. ToolForge übergibt aktuell Temperatur und Ausgabelimit ausdrücklich, die übrigen Samplingwerte kommen vom Server. Für reproduzierbare Vergleiche deshalb die LM-Studio-Presets ebenfalls dokumentieren.
- **Prompt-Template:** Modellpassendes Template beibehalten, besonders bei gpt-oss und Reasoning-Modellen. Keinen allgemeinen Chat-Wrapper erzwingen.
- **GPU/Cache:** Automatische Speicheranpassung zunächst beibehalten. Flash Attention kann auf unterstützten Engines Speicherbedarf senken und Geschwindigkeit verbessern; vor/nach Änderung mit derselben Probe messen. KV-Cache-Quantisierung nicht ohne Qualitätsvergleich umstellen. Q4 und Q8 sind getrennte Messkandidaten, keine austauschbaren Qualitätsstufen.
- **Parallelität:** Für diesen Vergleich nur eine Modellinstanz verwenden. Ein zusätzlich aktiviertes JIT-/Auto-Evict-Verhalten ersetzt den geprüften Entladeablauf nicht.

## Alle 15 vorgegebenen Modellvarianten

Die Rollen sind Testeinsätze, keine Rangliste. „Präsentation“ bezeichnet Inhalt und Struktur, keinen Nachweis visueller Folienqualität. Nicht alle Modellschlüssel werden bei jeder Installation genau so angezeigt. ToolForge nutzt die tatsächlichen Schlüssel aus LM Studio. Bei einem gemeinsamen Schlüssel für mehrere Quantisierungen zuerst in LM Studio die gewünschte Variante auswählen; die gemeldete Quantisierung wird in den Proben dokumentiert. Zwei Varianten unter demselben Schlüssel lassen sich in diesem Lauf nicht getrennt auswählen; dazu getrennte Läufe durchführen.

| Modell | Testeinsatz | Temperaturen im Coding-/Allgemeinprofil | Herstellerwert / Einordnung |
|---|---|---|---|
| qwen/qwen2.5-coder-14b | Coding, Codeanalyse | 0,2 / 0,7 | Eigene Testvorschläge |
| deepseek-coder-v2-lite-instruct | Zweite Coding-Perspektive | 0,2 / 0,7 | Eigene Testvorschläge |
| google/gemma-4-e4b | Allgemein, Präsentationsstruktur, Auswertung | 1,0 / 0,7 | Gemma-4-IT-Konfiguration: T 1,0, top-p 0,95 [4]; Instruct-Variante verwenden |
| qwen/qwen3.5-9b | Allgemein, Coding, Auswertung | 0,6 / 1,0 | Hersteller unterscheidet Modus/Aufgabe [5]; vollständiges passendes Preset beachten |
| ministral-3-8b-instruct-2512@q4_k_m | Allgemein, Präsentationsstruktur | 0,2 / 0,7 | Eigene Testvorschläge |
| ministral-3-8b-instruct-2512@q8_0 | Derselbe Test als Q8-Vergleich | 0,2 / 0,7 | Eigene Testvorschläge |
| meta-llama-3.1-8b-instruct@q4_k_s | Allgemeine Vergleichsbasis | 0,2 / 0,7 | Eigene Testvorschläge |
| meta-llama-3.1-8b-instruct@q8_0 | Derselbe Test als Q8-Vergleich | 0,2 / 0,7 | Eigene Testvorschläge |
| qwen2.5-coder-7b-instruct@q4_k_m | Kleiner Coding-Kandidat | 0,2 / 0,7 | Eigene Testvorschläge |
| qwen2.5-coder-7b-instruct@q8_0 | Derselbe Test als Q8-Vergleich | 0,2 / 0,7 | Eigene Testvorschläge |
| ministral-3-3b-instruct-2512@q4_k_m | Kleine allgemeine Arbeitsproben | 0,2 / 0,7 | Eigene Testvorschläge |
| ministral-3-3b-instruct-2512@q8_0 | Derselbe Test als Q8-Vergleich | 0,2 / 0,7 | Eigene Testvorschläge |
| gpt-oss-20b | Allgemeine Auswertung / Reasoning | 1,0 / 0,7 | T 1,0 in offiziellem Nutzungsbeispiel [6], keine Garantie eines Optimums |
| mistralai/devstral-small-2-2512 | Coding-Arbeitsprobe | 0,2 / 0,7 | Eigene Testvorschläge; tatsächlichen Speicherbedarf prüfen |
| mistralai/codestral-22b-v0.1 | Coding-Arbeitsprobe | 0,2 / 0,7 | Eigene Testvorschläge; tatsächlichen Speicherbedarf prüfen |

Im Präsentationsprofil werden die eigenen 0,2/0,7-Testpaare zu 0,4/0,8. Die besonderen Testpaare für Gemma 4, Qwen3.5 und gpt-oss bleiben erhalten. Das allgemeine Auswertungsmodell nutzt den ersten Temperaturwert seiner Familie. Als Auswerter ein allgemeines Instruct-Modell wählen; die Oberfläche erlaubt zur Flexibilität auch andere installierte Modelle.

## CLI-Alternative für einen manuellen Speicherwechsel

Die integrierte Funktion benötigt kein `lms` im PATH. Wenn du manuell testen möchtest, beendet dieses Windows-Skript den Ablauf bei Fehlern; es ersetzt nicht die zusätzliche Instanzprüfung der Anwendung:

```bat
@echo off
echo Entlade alle Modelle aus dem Grafikspeicher...
lms unload --all
if errorlevel 1 exit /b 1
lms load qwen/qwen2.5-coder-14b --context-length 20000
if errorlevel 1 exit /b 1
```

Den tatsächlichen Modellschlüssel einsetzen. Vor einem großen Modell kann `lms load MODELL --context-length 20000 --estimate-only` eine Speicherschätzung liefern [1]. Das ist eine Schätzung, keine garantierte freie VRAM-Messung.

## Quellen (geprüft 09.11.2026)

1. https://lmstudio.ai/docs/cli/local-models/load
2. https://lmstudio.ai/docs/developer/rest/list
3. https://lmstudio.ai/docs/developer/rest/load und https://lmstudio.ai/docs/developer/rest/unload
4. https://huggingface.co/google/gemma-4-E4B-it/blob/main/generation_config.json
5. https://huggingface.co/Qwen/Qwen3.5-9B
6. https://github.com/openai/gpt-oss

Reale Hardwaremessungen auf deinem Rechner und echte Modellqualitätsvergleiche wurden bei der Erstellung dieses Pakets nicht durchgeführt. Die Messreihe ist implementiert und durch simulierte Tests abgesichert; die Zielhardware muss separat gemessen werden.
