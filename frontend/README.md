# ToolForge Frontend V1.2

React / TypeScript / Vite. Die gebaute Oberfläche unter `dist` wird vom Backend ausgeliefert.

Neu in V1.2: einheitliches Tool- und DigitEgal-Branding aus `logos/`, kleinere Startlast durch verzögertes Laden von Cockpit, Hilfe und Editor sowie langfristig cachebare, gehashte Vite-Assets. Der Funktionsumfang aus V1.1 bleibt vollständig erhalten.

Entwicklung: `npm ci`, `npm run dev` (Port 5173, API-Proxy auf Port 8000).
Prüfen und bauen: `npm run build` (TypeScript-Prüfung eingeschlossen).
Für normalen Windows-Start ist Node.js nicht erforderlich. Siehe README im Projektstamm.
