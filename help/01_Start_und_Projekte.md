# Start und Projekte

## Einrichtung und Start
Setup_ToolForge.cmd einmal nach dem Entpacken ausführen. Es installiert die Workbench in .venv und Aider getrennt in .aider-venv mit Python 3.12 über uv. Ein Internetzugang wird für Pakete und gegebenenfalls Python benötigt. Aider wird anschließend tatsächlich aufrufbar geprüft. Bei einem Fehler meldet das Setup keinen Erfolg.
Start_ToolForge.cmd oder Start_ToolForge_Pilot.cmd öffnet den Browser; der Server läuft ohne dauerhaftes CMD-Fenster. Die kurzen Fenster der CMD-Startdatei können kurz sichtbar sein. Für Fehlersuche Start_ToolForge_Debug.cmd verwenden. Startfehler stehen auch in runtime/startup.log.
ToolForge beenden in der oberen Leiste stoppt Jobs und Server. Stop_ToolForge.cmd dient als Ersatz bei hängender UI: Es sendet eine Stoppanforderung und verwendet bei unerreichbarer API eine instanzbezogene Stoppdatei. Ein vollständig eingefrorener Python-Prozess muss im Windows-Taskmanager beendet werden; andere Python-Prozesse werden von ToolForge niemals pauschal beendet.

## Projekte
Projekt anlegen, öffnen und einen Arbeitsordner außerhalb des ToolForge-Programmordners verbinden. Vorhandene Dateien, Planversionen und Zustand werden eingelesen. Umbenennen und Archivieren ändern den Code nicht. Die Löschvorschau zeigt lokale Paketbereinigung und geteilte Umgebungen; Ordner werden wiederherstellbar verschoben. Globale Chocolatey-Pakete brauchen gesonderte Bestätigung.
Nach einem Versionswechsel den bisherigen Server beenden. Zum Übernehmen der Projektliste den alten Ordner backend/data vor dem Start in die neue Version kopieren. Den bisherigen Projekt-Arbeitsordner unverändert weiterverwenden. Zustandsdaten liegen zusätzlich unter AppData/ToolForgePilot; Aufgabenpläne und Diagnoseprotokolle im Projekt unter .toolforge.
