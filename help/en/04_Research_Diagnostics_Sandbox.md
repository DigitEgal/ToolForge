# Research, Diagnostics and Sandbox

## DuckDuckGo

Enable and save web search in the project settings. It is off by default. For suitable technical errors, the Pilot may research once per affected task before repairing again or asking. It searches for a detected error class or module name, not complete logs or source code. Module names can also contain internal identifiers: enable this only if it is allowed for the project. Results are external, untrusted data; they are not executed as commands. Missing packages must still go through approved installation paths.

Every search attempt, including errors or zero results, is recorded in the project under `.toolforge/websearch.jsonl` with timestamp, query, hits and error. DuckDuckGo may rate-limit or block requests; search is not an availability guarantee. No other search provider is used as a substitute and no API key is required.

## Detailed error logs

Enable and save in settings, or toggle for the next run in the overview under Research & diagnostics. From the next run, additional run details, context profiles and error tracebacks are written to `.toolforge/diagnostics/errors.jsonl`. API keys and common secret patterns are redacted; nevertheless review before sharing, because project content may appear in diagnostic output. Normal run logs remain active independently.

## Package installation and build errors

If a source build fails during an approved pip installation (typically Pillow on Python 3.11 without zlib), ToolForge searches PyPI metadata for the newest version with a matching wheel for the interpreter and operating system. If web search is enabled, it may additionally research the error once. The installation is retried with the verified version; the plan is re-versioned and the task receives the finding as a note. The failed version marker is discarded so the correction is not blocked. Without a matching wheel version, the original error remains visible.

## Docker sandbox and networking

Install/start Docker Desktop with Linux containers. The build starts only when the Docker CLI and the Linux daemon are reachable; ToolForge checks both before every build, network and package job and immediately reports missing or stopped daemons with an actionable hint. Enable and save the sandbox under Settings, then build the Docker check environment under Development area → Run & check. The initial image contains Python, pytest, Ruff and mypy. Add further project dependencies under `.toolforge/docker/Dockerfile` in the project and rebuild; existing Dockerfiles are not overwritten. The build needs internet; installed packages remain in the image.

With the sandbox enabled, Python execution, Pilot check commands and Python workflow nodes run in the container. Editor, Git, AI file changes, CSV/Excel processing and installation of the local `.venv` run on the host. This is an execution boundary, not complete virtualization of the workbench. The project directory is mounted writable at `/workspace` in the container. No Docker socket or other project is mounted. Use Linux container paths; Windows programs and host paths outside the project are not available there.

No network by default. A shared freely chosen network name in several projects creates an internal Docker network `toolforge-NAME` on the next image build. Only containers selected this way are connected; internet access is blocked in the internal network. A running project container is reachable under the alias `tf-HASH` logged in the Docker command. No host ports are published. After a network change, rebuild the check environment for every participating project. Containers are removed after completion, error, timeout or cancellation; images and internal networks remain for later runs.
