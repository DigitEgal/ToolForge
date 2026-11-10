# Modelle und Aufgaben

## Vorabcheck
Im Aufgabenplan Ziel beschreiben, Testprofil wählen und installierte Modelle laden. Bis zu drei Kandidaten mit denselben Arbeitsproben vergleichen. Optional werden zwei Temperaturen erprobt. Ein allgemeines Modell bewertet die anonymisierten Proben; eine gültige Empfehlung wird erst nach Übernehmen aktiv. Vor jedem Modellwechsel werden vorhandene Instanzen entladen und der geladene Kontext überprüft. Details und alle 15 Modellvarianten: LM_STUDIO_PRESETS.md im Programmordner.
20.000 Kontexttokens sind ein Ausgangswert, kein Qualitätsoptimum. Temperatur wird pro Modell/Anfrage gesetzt. Große Modelle oder Kontexte können mehr Speicher benötigen. Bei Ladefehlern nicht weitere Modelle zusätzlich laden. Assistenzanfragen für Hilfe/Verbesserungen stellen das vorherige Arbeitsmodell wieder her.

## Planen und Ausführen
Plan erstellen speichert versioniertes JSON im Projekt. Start / Fortsetzen führt die Aufgaben im Abhängigkeitsgraphen aus. JSON-Import bleibt möglich. Unveränderte Aufgaben behalten ihre Prüfbelege; geänderte Anforderungen werden erneut geprüft. Ausgabegrenzen und Schleifen werden begrenzt. Eine Reparaturentscheidung prüft zuerst Umgebungs-, Verbindungs-, Format- und Umfangsprobleme. Aufteilung ist für echte Kontext-/Ausgabegrenzen vorgesehen, nicht für jeden Fehler.

## Fragen, Pause und Fortschritt
Fehlt Information, wird nur die betreffende Aufgabe zurückgestellt. Unabhängige Aufgaben ohne gemeinsame betroffene Dateien laufen weiter. Sind alle übrigen Aufgaben abhängig, zeigt Warum Aufgaben warten die Blockierungen. Antworten werden vor dem nächsten Durchlauf berücksichtigt. Alle offenen Fragen sind im Cockpit sichtbar. Ton über Lautsprechersymbol/Lautstärke einstellen; Browser erlauben Ton erst nach einer Nutzerinteraktion.
Nach Lauf pausieren hält an einer Durchlaufgrenze an. Pause zurücknehmen hebt eine noch ausstehende Pause auf. Nach bereits erfolgter Pause Start / Fortsetzen verwenden. Jetzt stoppen fordert Abbruch an; laufende Modell-HTTP-Anfragen können bis zum Timeout dauern.
Aktuell geprüft bezeichnet gültige Prüfnachweise. Bereits umgesetzt zählt Aufgaben, die mindestens einmal erfolgreich waren. Erneut zu prüfen bedeutet geänderte Eingaben oder Abhängigkeiten. Eine neue Erweiterung vergrößert den Gesamtumfang; deshalb kann der prozentuale Anteil berechtigt sinken. Erledigte, unbetroffene Aufgaben werden nicht erneut bearbeitet. Unbekannte ältere Prüfnachweise werden bei der Migration einmal neu geprüft, nicht ungeprüft übernommen.
