# Start and Projects

## Setup and start (V1.4)

Run `Setup_ToolForge.cmd` once after unpacking. It installs the workbench in `.venv` and Aider separately in `.aider-venv` with Python 3.12 via uv. Internet access is required for packages and, if necessary, Python. Aider is installed from the pinned `requirements-aider.txt` and then actually checked for being callable. If npm is available, setup additionally installs `@opencode/cli` and starts the local OpenCode service for free models; without npm this model source simply remains disabled. On an error, setup does not report success. The optional tray icon additionally requires `requirements-tray.txt`; without these packages ToolForge still starts normally.

`Start_ToolForge.cmd` or `Start_ToolForge_Pilot.cmd` opens the browser; the server runs without a permanent CMD window. The short windows of the CMD launcher may be visible briefly. Use `Start_ToolForge_Debug.cmd` for troubleshooting. Startup errors are also written to `runtime/startup.log`. The project overview loads first; development cockpit, help, analysis and code editor are loaded only when opened. Hashed program files may stay in the browser cache long-term, while the start page is checked on every request.

Quit ToolForge in the top bar stops jobs and the server. If the UI was opened in a Chrome/Edge app window started by ToolForge, ToolForge closes that window as well. Other browsers may not allow a script to close a window; there a completion screen with a note appears. `Stop_ToolForge.cmd` is the fallback for a hanging UI: it sends a stop request and uses an instance-specific stop file if the API is unreachable. A completely frozen Python process must be ended in the Windows Task Manager; ToolForge never terminates other Python processes indiscriminately.

## Projects, views and groups

Create a project, open it and connect a working folder outside the ToolForge program folder. Existing files, plan versions and state are read in. Renaming and archiving do not change the code. The deletion preview shows local package cleanup and shared environments; folders are moved in a recoverable way. Global Chocolatey packages require separate confirmation.

Use **Tiles / List** to switch the project overview. The list view is intended for many projects and shows the project group on each row. Use **Groups** to create, rename or delete project groups. Move projects in the list view or in the project details; when a group is deleted, all projects remain and move to “No group”.

Under **Analysis & operations** you can export a project as a ZIP with a manifest and import it into another working folder. The export contains no `.toolforge` state data and no secrets; during import, paths are checked and existing files are overwritten only after explicit confirmation.

## Analysis and operations (since V1.1)

The incremental project index reads symbols, imports and dependencies and re-parses only changed files. The analysis shows manifest, file count and coverage; large projects are processed in documented, size-limited chunks.

The task graph shows dependencies, critical path, ready tasks and file conflicts. Priorities are applied before task selection. Parallel use of the same file is allowed only after explicit approval; with a dependency order, the same file can safely be used one after another.

Before a plan is applied, the preview shows changes to tasks, files, dependencies, checks and effort as well as affected already-verified parts. For high risk or changed checks, explicit confirmation is required; a plan backup is created automatically beforehand.

The empirical benchmark tests multiple context sizes and repetitions, tokens/s, VRAM peaks and quality spread. Results apply to the measured hardware, quantization and task. Application acceptance runs declared CLI, HTTP and browser scenarios; changed test files are shown as a diff and approved separately.

**Project memory** shows model-independent insights from earlier runs, allows your own notes and clearing; details are under Models and Tasks. **Operations** rotates diagnostic journals, lists plan backups, shows installer/tray status and supports restoration. The Windows installer is built under `installer/` and optionally signed; without a certificate it remains unsigned. Docker resources, images, networks, loopback ports and package installation are managed in the sandbox area.

## Tutorials and help

On first start a welcome window with the ToolForge logo appears. The UI tutorial guides you through projects, views, groups, the Pilot, the development path, help, sound and shutdown with a dimmed interface and highlighted areas. Further tutorials explain the cockpit, handoff & independent review and the development area. The developer tutorial starts on the first visit to the development area; all tutorials can be restarted from the help page at any time. The help page also contains the user documents and a document-based help chat. The `EN | DE` language switch next to sound and theme translates the interface and the help documents; the choice is stored in the browser.

After a version change, stop the previous server. To adopt the project list, copy the old `backend/data` folder into the new version before starting. Continue using the existing project working folder unchanged. State data is additionally stored under `AppData/ToolForgePilot`; task plans and diagnostic logs are stored in the project under `.toolforge`.
