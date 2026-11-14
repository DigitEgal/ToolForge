<p align="center">
  <img src="frontend/logos/LogoV7_OnlyLOGO.png" alt="ToolForge – Local Workbench" width="96">
</p>

<p align="center">
  <strong>Local vibe-coding workbench for Python tools:</strong><br>
  plan, verify, develop, test, version and connect – on your own machine.
</p>

<p align="center">
  <strong>English</strong> · <a href="README.md">Deutsch</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-V1.4-b8a3ff" alt="Version V1.4">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-2f3640" alt="Windows and Linux">
  <img src="https://img.shields.io/badge/tests-185%20passed-2ea44f" alt="185 tests passed">
  <img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="MIT license">
</p>

---

## What is ToolForge?

ToolForge combines project management with a controlled AI development workflow. You describe a goal, optionally compare local models in a preflight and have a reviewable task plan generated from it. Aider then works through the tasks step by step; passed check commands – not mere agent prose – provide the proof of success.

Everything runs locally. By default the workbench is reachable only at `http://127.0.0.1:8000`. Cloud services and an AI provider are not required for the core features.

> **OpenCode Free:** Optionally, free models can be used without an additional account through the locally installed OpenCode service. In that case model prompts leave your machine for the free OpenCode inference service; code, plans and checks remain local. Details under [OpenCode Free](#opencode-free-free-models-without-an-account).

> **Who is it for?** Technically experienced individuals who want to use local models (e.g. LM Studio) and Aider while keeping plans, file changes, tests and approvals in view.

## Feature overview

| Area | Features |
|---|---|
| **Projects** | Create, open, search, archive, delete with cleanup preview; tile and list view; project groups; ZIP export/import with manifest; recoverable folder deletion; separate pip/Chocolatey/npm permissions |
| **Pilot** | Incremental project analysis with symbols and dependencies, goal description, optional model preflight, reviewable task plan with diff preview, task graph, Aider batch execution, questions, pause/resume, repair strategies, extensions without restart, progress preservation, project logs |
| **Handoff & review** | Ordered handoff list for stuck tasks, independent result review by other models, creator exclusion, configurable minimum approvals, strict repair after rejection, changes even during a run |
| **Model comparison** | Three to six candidates, identical work samples, one or two temperatures, anonymized evaluation, recommendation with explicit acceptance, context verification including small LM Studio rounding deviations; empirical benchmarks with repetitions, tokens/s, VRAM peaks and quality spread per hardware, quantization and task type |
| **Development** | File tree and CodeMirror editor, conflict-checked saving with backups, Python execution with live output and cancellation, pytest/Ruff/mypy, Git status/diff/selected commits/history |
| **AI assistance** | Single-file proposals with diff and explicit acceptance; extension suggestions by category; document-grounded help chat |
| **Workflows** | Visual node graph, validation, CSV checks, duplicate removal, Excel export, Python nodes |
| **Acceptance** | Declared CLI, local HTTP and headless browser scenarios as real application acceptance; separate review of test changes with baseline and review step |
| **Research & diagnostics** | Research with domain filter, opened sources, text evidence and cache; journal; detailed error logs with secret redaction |
| **Sandbox** | Optional Docker execution for project commands and Python workflow nodes; images, internal networks, memory/CPU/process limits, loopback ports and package installation in the container |
| **Usability** | Unified V7/V6 branding, dark/light theme, notification sound with volume, EN/DE language switch for the interface and help, guided tutorials for UI, cockpit, handoff & review and the development area, SSE updates with polling fallback, global questions, help inside the app; large areas and the editor load only on demand |
| **Operations** | Hidden start, dedicated Chrome/Edge app window with automatic closing, stop script, debug start, log rotation, plan backups, uninstall script, optional tray icon and prepared Windows installer |

## New in V1.4

- **Multi-model handoff for stuck tasks:** An ordered list of `source::model` entries is tried in sequence when the primary model repeatedly fails, stalls, reaches a context limit or leaves a task blocked. The order survives a later change of the source preset.
- **Independent result review:** One or more other models assess passed tasks and the project completion. A task’s creator and the active primary model are excluded from reviewing it; minimum approvals and strict repair behaviour are configurable.
- **Configurable in preflight and during a run:** Handoff and reviewer lists can be accepted together with the preflight recommendation and changed at any time under “Handoff & review”, even while a job is running. The selection is validated against the current model inventory.
- **Optional preflight:** “Skip preflight” allows planning and starting without a confirmed model comparison. A later preflight remains possible; recommendations still become active only after explicit acceptance.
- **Bilingual throughout:** `EN | DE` next to sound and theme translates the entire interface, the help documents, all tutorials as well as README and quickstart. The choice is stored in the browser; the help page loads its documents in the selected language.
- **Free quota remains respected:** Every reviewer receives exactly the configured model without silent substitution. Handing off to another free model does not create new daily quota; when exhausted, the run stops with an explained note.
- **Docker build starts reliably:** Docker CLI and Linux daemon are checked before build, network and package jobs. Missing or stopped daemons produce an immediate, actionable message instead of a hanging “Job: failed”; the interface keeps refreshing the status until completion.
- **V1.4 throughout:** API and FastAPI metadata report `1.4.0`, the workbench stage is `14`; frontend package, installer, start banner, setup output, help and documentation all say V1.4 or fourteen stages.

## Feature basis V1.3

- **OpenCode Free without an extra account:** The locally installed OpenCode service provides free coding models. ToolForge connects through the local, password-protected OpenCode API and uses it for preflight, planning, help and as an OpenAI-compatible bridge for Aider. No API key is required.
- **Source presets instead of model-name tricks:** Six presets – Local only, Free only, API only, Free & local, Local & API, Free & API – combine with MAX quality, Price/performance or Cost saving into a clear source order. Each source has its own model field. The active source stays first while a job is running.
- **Shared free quota respected:** All OpenCode free models share one daily limit. Switching the model is not additional quota. When exhausted, ToolForge falls back only to local or a paid API if the preset allows that source; Free only stops with an explained note. OpenCode status and a separate console open only on click.
- **More reliability for small models:** Small models under about 16 GB receive a more compact project overview, whole files instead of risky diffs, stricter format checking and syntax errors with concrete line excerpts. Task splitting and fresh context windows remain available.
- **Pilot button fixed:** “Open Pilot” now really starts the bundled desktop window through the local Python environment; failed starts are reported with the log path. “Open cockpit” remains a separate path into the browser workbench.
- **Repeatable preflight:** After errors or plan changes, the preflight can be restarted directly with the saved candidates and evaluation model. The last report stays visible, marks an outdated task or source preset and shows skipped candidates and measured alternative sources.
- **V1.3 throughout:** API and FastAPI metadata reported `1.3.0`, the workbench stage `13`; frontend package, installer, start banner, setup output, help and documentation said V1.3 or thirteen stages.

## Feature basis V1.2

- **Unified branding:** The V7 logo from `frontend/logos` appears in the sidebar, completion screen and welcome dialog. Bottom left remains exactly one linked “by DigitEgal”, whose wordmark now uses the V6 mark as an image; size and contrast are tuned to the sidebar.
- **Faster start:** Cockpit, help, project management, analysis, development area and code editor are loaded via `React.lazy`/`Suspense` only when opened. The initial JavaScript bundle drops from about 955 kB to about 261 kB; the editor remains a separate CodeMirror bundle loaded on demand.
- **Permanently cacheable assets:** Hashed files under `/assets/` receive `public, max-age=31536000, immutable`; `index.html` stays `no-cache` so an update is detected immediately.
- **Tidied documentation:** All test reports and environment data live in a current [TESTBERICHT.md](TESTBERICHT.md). Historical requirement comparisons are archived; version-specific individual reports, old environment files and unused SVG logo duplicates were removed.

## Feature basis V1.1

- **Full incremental project analysis:** The index stores file signatures, symbols, imports and dependencies; only changed files are re-read. Large projects are analysed in documented, size-limited chunks including manifest and coverage display.
- **Empirical benchmarks instead of family preselection:** Repeated work samples across multiple context sizes, tokens/s, VRAM peaks and quality spread; results are cached per hardware, quantization and task type.
- **Plan diff with risk preview:** Dependencies, effort, new checks and already verified parts are compared before acceptance. Changes to verified tasks require explicit confirmation; a plan backup is created beforehand.
- **Application acceptance:** Declared CLI, HTTP and browser scenarios verify the finished tool as an application. Test changes are shown as a diff against a baseline and approved separately.
- **Reproducible environments:** `aider-chat==0.86.2` and the tested controller state are pinned; environment locks contain package versions, file hashes and Docker digests. Presets can be exported and imported without API keys.
- **Task graph:** Nodes, edges, critical path, ready tasks and file conflicts; priorities are applied before task selection. Parallel use of the same file requires explicit approval.
- **SSE and global questions:** Session and global event channels update the UI without constant polling; slow polling remains a fallback. Open questions appear across projects.
- **Evidence-based research:** Domain filter, rejection of local/IP-literal targets, actually opened sources, text evidence, seven-day cache and assignment to a task or error.
- **Operations and recovery:** Project export/import as ZIP, log rotation, plan backups, installer definition, build/sign script and optional tray icon.
- **Sandbox convenience:** Resource controls, image and network management, loopback ports and pip/npm package installation in derived project images.

The full mapping is in [ABNAHME.md](ABNAHME.md). Test scope and limits are documented in [TESTBERICHT.md](TESTBERICHT.md).

## Installation on Windows

**Prerequisites**

- Windows 10/11
- Python 3.11 or newer
- Internet connection for setup and packages
- Optional: [LM Studio](https://lmstudio.ai/) with the Native REST API v1 enabled
- Optional: [OpenCode](https://opencode.ai) and Node.js/npm for free models without an additional account
- Optional: Docker Desktop for the sandbox

**Steps**

1. Unpack the ZIP into a new program folder. Stop any running old ToolForge server first.
2. Run `Setup_ToolForge.cmd`. Setup creates `.venv` for the workbench and `.aider-venv` for Aider and actually verifies Aider’s version and required options. If npm is available, it additionally installs `@opencode/cli` and starts the local OpenCode service; without npm, OpenCode simply stays disabled.
3. Open `Start_ToolForge.cmd`. The UI starts at `http://127.0.0.1:8000`; under Chrome/Edge a dedicated app window opens.
4. On first start a welcome dialog introduces the UI tutorial.
5. Under **Settings → Model sources** choose a preset, for example **Free & local**, pick the desired order and load a model per source. For API only, enter the base URL and session key.

```text
Setup_ToolForge.cmd        one-time setup
Start_ToolForge.cmd        start the workbench
Start_ToolForge_Debug.cmd  for startup problems; log at runtime/startup.log
Stop_ToolForge.cmd         emergency stop for a hanging UI
```

Node.js is not required for normal use – the built frontend is included.

### OpenCode Free: free models without an account

OpenCode is a separately installed coding agent with a local background service. ToolForge uses its local API to employ free models such as `deepseek-v4.1-flash-free`, `glm-5.3-flash-free` or `minimax-m3.1-flash-free` for preflight, planning, help and Aider. No OpenCode account and no API key are stored in ToolForge.

1. Run `Setup_ToolForge.cmd` if npm is available. Alternatively install manually with `npm install -g @opencode/cli` and start with `opencode service start`.
2. Under **Settings → Model sources → OpenCode Free**, check the status, start the service or open the console. These actions run only on click.
3. Select a free model and save the source preset. Optionally, a preferred free-model order for temporary model errors can be configured; it is not a quota reset.
4. All free models share one daily limit. When exhausted, ToolForge only tries local or a paid API if the selected preset allows that source. With Free only the run stops with a note; local models remain independently usable.

The free models run through the OpenCode inference service. Prompts and the file excerpts belonging to the task are sent to that service. For fully local processing, use LM Studio.

**Optional installer and tray:** Under [installer/](installer/README.md) there is an Inno Setup 6 definition with build and sign script. The installer installs to `%LOCALAPPDATA%\Programs\ToolForge`; Python 3.11 or newer remains a prerequisite. Without a code-signing certificate (`TOOLFORGE_SIGN_CERT`) it is built unsigned. The tray icon is optional and requires `pip install -r requirements-tray.txt`; without these packages ToolForge still starts normally.

### Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python start_toolforge.py
```

Aider uses the same separate approach as on Windows; details are in the help.

## First workflow

1. **Create a project** and connect a working folder outside the ToolForge program folder.
2. **Describe the goal** and have three to six models suggested in the preflight – local from LM Studio or free via OpenCode Free.
3. **Start the preflight** or directly choose **“Automatic: preflight → recommendation → plan → start”**.
4. Review the recommendation, inspect the plan and start execution. Open questions appear in the cockpit.
5. Extend existing tools via **Development area → Improvements** instead of starting over.
6. Continue with **Files & editor**, **Run & check**, **Git** and **Workflows**.

The development tabs follow the workflow: **Improvements · Files & editor · AI changes · Run & check · Git · Workflows**.

## Uninstallation

```text
Deinstallieren_ToolForge.cmd
```

Removes `.venv`, `.aider-venv`, `frontend/node_modules`, `frontend/dist`, `runtime`, `.pytest_cache` and Python caches. On request `%APPDATA%\ToolForgePilot` is deleted as well. **Your own project folders are never modified.** Afterwards delete the program folder manually.

Without prompts:

```powershell
python uninstall_toolforge.py --yes
python uninstall_toolforge.py --yes --keep-data
```

## Security and privacy

- **Local:** Server bound to `127.0.0.1`, CORS limited to local addresses, access logs off by default. OpenCode Free is optional and uses a local service that forwards model prompts to the free OpenCode inference service.
- **No silent cloud calls:** Web search is opt-in and uses DuckDuckGo exclusively. Every attempt – including errors and zero results – is recorded in the project journal.
- **No blanket permissions:** pip, Chocolatey and npm installations can be permitted separately; checking tools have their own one-time permission.
- **Secrets:** API keys are redacted in logs; detailed diagnostics are opt-in.
- **Project folders remain untouched:** Deletions are limited to ToolForge-owned data and confirmed project folders.
- **Docker is optional:** Without Docker, commands run on the host. The container option is not full virtualization of the workbench.

## Documentation

- [Acceptance and requirement comparison V1.4 (German)](ABNAHME.md)
- [Consolidated test report V1.4 with archive (German)](TESTBERICHT.md)
- [Development path (German)](TOOLFORGE_ROADMAP.md)
- [LM Studio and model preflight (German)](LM_STUDIO_PRESETS.md)
- [Start and Projects](help/en/01_Start_and_Projects.md)
- [Models and Tasks](help/en/02_Models_and_Tasks.md)
- [Development Area](help/en/03_Development_Area.md)
- [Research, Diagnostics and Sandbox](help/en/04_Research_Diagnostics_Sandbox.md)
- [German help](help/01_Start_und_Projekte.md) · [Quickstart EN](SCHNELLSTART.en.txt) · [Schnellstart DE](SCHNELLSTART.txt)
- [Windows installer](installer/README.md)
- [Next optimisations (German)](NAECHSTE_SCHRITTE.md)

The help is also available directly in the app under **Help**.

## Development and tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests backend/tests
npm --prefix frontend run build
```

The frontend build runs `tsc --noEmit` and the Vite production build. Tests use isolated projects and simulated model/Docker responses. Real model quality, GPU/VRAM behaviour, Docker Desktop, actual Aider runs, signing and tray must additionally be verified on the target machine. Details and limits: [TESTBERICHT.md](TESTBERICHT.md).

### Project structure

```text
backend/            FastAPI, project API, Pilot bridge, workspace, workflows
toolforge_pilot/    Engine, Aider adapter, preflight, installations, recovery
frontend/src/       React/TypeScript interface including tutorials
frontend/logos/     V7 tool logo and V6 DigitEgal wordmark
tests/              Engine, Pilot and regression tests
backend/tests/      API, database and migration checks
help/               user documents for the app (English under help/en)
installer/          Inno Setup definition, build and sign script
docs/archiv/        Historical requirement comparisons and base specification
```

## Known limits

- LM Studio must be installed and provide the Native REST API v1. The benchmark recommends only a sample measured on this hardware, not a globally best model family.
- OpenCode Free requires a local OpenCode installation. The free models share one daily limit; when fully exhausted no free cloud model is available until the reset. Prompts are sent to the OpenCode inference service.
- The model preflight and benchmark do not replace professional review. Quantization, drivers and other running GPU applications influence tokens/s, VRAM peaks and quality spread.
- Docker, Aider, GPU measurements, tray and installer signing are not replaced by simulated tests. In the documented test environment no Docker daemon was running; Inno Setup and `signtool` were not installed.
- A fully frozen operating-system process must be ended in Task Manager. ToolForge never terminates other Python processes indiscriminately.
- A browser outside the ToolForge app window may not be closed by script; a completion screen appears there instead.

## Version history

| Version | Focus |
|---|---|
| 0.1 | Project management, local persistence, workbench skeleton |
| 0.2 | Project analysis/dashboard, separate package permissions, installation journal |
| 0.3 | Aider batch mode, plan JSON, model warnings, context/temperature, diagnostics, logs |
| 0.4 | Loop/token limits, fresh context, limited replanning, overall verification |
| 0.5 | Save/import plan, project lifecycle, independent tasks despite questions |
| 0.6 | Editor, Python execution, quality checks, Git, AI diffs, workflows, CSV/Excel acceptance |
| 0.7 | Model preflight, work samples, 15 presets, 20,000 starting context |
| 0.8 | Six problems and seven improvements: setup, questions, progress, repair, help, sound, web search, diagnostics |
| 0.9 | Project groups, list view, tutorials, branding – completed in V1.0 |
| **V1.0** | **Pillow self-repair, browser closing, one-click flow, context tolerance, 3–6 candidates, uninstallation** |
| **V1.1** | **Incremental project index, empirical benchmark, plan diff, application acceptance, pinned environments, task graph, SSE, evidence-based research, export/import, installer/tray, sandbox convenience** |
| **V1.2** | **V7/V6 branding, consolidated test report, cleaned-up legacy, code splitting with a much smaller start bundle, immutable asset cache and twelfth stage** |
| **V1.3** | **OpenCode Free without an extra account, deliberate source presets instead of free-model switching at daily limits, configurable order, more reliable small models, fixed desktop Pilot and repeatable preflight** |
| **V1.4** | **Multi-model handoff for stuck tasks, independent result review without creator bias, roles configurable in preflight and at runtime, optional preflight, complete EN/DE interface and help, four tutorials and diagnosed Docker build** |

## License and credits

MIT license – see [LICENSE](LICENSE). Copyright © 2026 **DigitEgal**.

ToolForge uses among others FastAPI, Uvicorn, SQLite, React, TypeScript, Vite, CodeMirror and Aider. LM Studio, OpenCode and Docker are optional, separately installed tools.
