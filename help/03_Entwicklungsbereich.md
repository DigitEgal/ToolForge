# Entwicklungsbereich

## Verbesserungen
Textuelle Erweiterungen können auch während der Entwicklung eingereicht werden. Sie werden an der nächsten Aufgabengrenze geplant; wenn gerade eine andere Assistenzfunktion läuft, spätestens beim nächsten Start. Bestehende Aufgaben werden nicht gelöscht. Jede Erweiterung erhält neue IDs, Dateikonflikte werden über Abhängigkeiten verknüpft. Fehlerhafte Pläne ersetzen den Bestandsplan nicht.
Für KI-Vorschläge die Bereiche Architektur, Codequalität, Funktionen, Darstellung, Geschwindigkeit, Tests und Sicherheit wählen. Ein allgemeines Modell kann vorgeschlagen oder manuell gewählt werden. Diese Vorauswahl ist keine objektive Rangliste. Der Analyseumfang nennt gelesene Ausschnitte und ausgelassene Dateien. Vorschläge einzeln markieren und bestätigen. Hat sich das Projekt inzwischen geändert, Analyse erneuern. Bei Fehlern eines Erweiterungsauftrags den korrigierten Wunsch erneut eingeben.

## Dateien & Editor
Datei wählen, bearbeiten und speichern, auch per Strg+S. Vorherige Inhalte werden gesichert. Bei externer Änderung verhindert ein Versionsvergleich das Überschreiben. Ungespeicherte Entwürfe werden im Browser zwischengespeichert. Binärdateien, Geheimnisdateien und interne Steuerordner sind im Editor gesperrt.

## KI-Änderungen
Eine Datei auswählen, Auftrag formulieren, Diff prüfen und ausdrücklich übernehmen. Abgeschnittene Antworten werden abgelehnt; zwischenzeitliche Änderungen führen zum Speicherkonflikt. Anschließend passende Tests ausführen.

## Ausführen & Prüfen
Projektumgebung anlegen; Python-Datei wählen und Argumente als JSON-Liste angeben. Der Klick auf pytest, Ruff & mypy installieren erlaubt genau diese Installation einmalig in der Projektumgebung. Die allgemeine automatische pip-Freigabe bleibt unverändert. Tests, Linting und Typprüfung sind getrennte Aufträge. Live-Ausgabe und Abbruch stehen darunter.

## Git und Workflows
Git-Repository im Projekt initialisieren, Diff und Historie prüfen. Committen erfordert eine explizite Dateiauswahl. Unabhängig vorgemerkte Dateien werden nicht mitcommittet. In Workflows Knoten auswählen, Konfiguration und Eingänge ändern, speichern und ausführen. Die CSV→Excel-Abnahme prüft Einlesen, Validierung, Duplikate und Excel-Export. Python-Knoten erhalten --input und --output mit JSON-Pfaden.
