# Models and Tasks

## Preflight

In the task plan, describe the goal, choose a test profile and load installed models. Compare three to six candidates on identical work samples. Optionally, two temperatures are tested. A general model evaluates the anonymized samples; a valid recommendation becomes active only after you apply it. Small context deviations rounded by LM Studio are adopted and the actually loaded value is stored as the verified budget. Before every model switch, existing instances are unloaded and the loaded context is checked. The button “Automatic: preflight → recommendation → plan → start” runs the entire sequence after candidate selection in one click. Details and all 15 model variants: `LM_STUDIO_PRESETS.md` in the program folder.

20,000 context tokens are a starting value, not a quality optimum. Temperature is set per model/request. Large models or contexts may require more memory. On load errors, do not load additional models. Assistance requests for help/improvements restore the previous working model.

The preflight is optional. Use “Skip preflight” in the preflight settings or under Settings → Execution & context to let ToolForge start without a confirmed model comparison. A later preflight remains possible; the recommendation still becomes active only after explicit acceptance.

## Model sources, presets and the free quota

Under Settings → Model sources, first choose the allowed selection: Local only, Free only, API only, Free & local, Local & API or Free & API. Each source has its own model field; changing the preset does not overwrite the models of other sources. The order MAX Quality (API → local → free), Price/performance (free → local → API) or Cost saving (local → free → API) determines which allowed source works first and where ToolForge falls back. The active source stays first while a task is running.

OpenCode Free uses the locally installed OpenCode service; no account or API key is required. All free models share one daily quota. Switching from deepseek to glm or another free model is therefore not additional quota and is not reported as a way out after a limit error. When the free quota is exhausted, ToolForge only tries local or a paid API if those sources are allowed by the preset. With Free only, the run stops with a clear explanation. “Check status”, “Start OpenCode” and “Open console” run only on click and do not slow down normal ToolForge startup. The console opens a separate terminal in the project folder. With OpenCode Free, prompts are sent to the OpenCode inference service.

For a paid API, base URL, session key and model are stored separately. The key exists only in the running session and is not written to project files or logs. The API is used only if it is allowed by the preset.

## Running the preflight again

The last preflight remains visible after an error. “Run preflight again” restarts it with the saved candidates and evaluation model. If the task, source preset or order changed, the report marks this visibly and requires a new run; with a changed preset, candidates are loaded fresh. Skipped, temporarily blocked candidates and already measured alternative sources are listed in the report. An exhausted free limit is explained as such; changing only the free model name does not help. The report is retained under `.toolforge/preflight-history`.

## Handoff and independent review (V1.4)

In the preflight and under “Handoff & review” you can define two ordered model lists. The handoff list is tried in order when the primary model repeatedly fails, stalls, reaches a context limit or leaves a task blocked. The reviewer list independently assesses passed tasks; a task’s creator and the active primary model are excluded from reviewing it. With the option enabled, a clear rejection triggers a repair; otherwise it is logged as a finding.

The order is stored as `source::model` and survives a later change of the source preset. Changes to either list apply from the next task and can also be made during a run. Every reviewer receives exactly the configured model without silent substitution. All free models still share one daily quota: handing off to another free model does not create new quota. When the limit is exhausted, handoff stops with an explained note. Creator, review verdict, approvals and handoff attempts are recorded in the task log and shown in the overview.

## Project memory

ToolForge stores distilled insights from completed and interrupted runs in the project state database: failures with a short cause, successful repair strategies, model handoffs, review rejections with findings, answers to questions and verified installation resolutions. Full transcripts and secrets are not retained; entries are redacted, deduplicated and capped at 500 records.

Later planning and tasks receive a compact excerpt with a fixed character limit. This happens independently of the active model and source preset, so a model change does not lose earlier lessons. The memory is data, not an instruction, and is checked against the current project state before use.

Under Analysis & operations → Project memory, entries are shown with provenance, model and file references. You can add your own note, refresh the memory or clear it completely. The option “Use project memory for planning and tasks” disables only future use; existing entries remain until deleted. Exporting the project folder does not include the state database.

## Supporting small models

For models under about 16 GB, ToolForge detects a small model and enables additional help: a more compact project overview, whole files instead of risky diffs, stricter format checking and syntax errors with concrete line excerpts. The “Support small models” option remains visible under Execution & context. Task splitting and fresh context windows remain independent; a larger model or more context does not replace quality verification.

## Planning and execution

Create plan stores versioned JSON in the project. Start / Resume executes the tasks in the dependency graph. JSON import remains possible. Unchanged tasks keep their verification evidence; changed requirements are checked again. Output limits and loops are bounded. A repair decision first checks environment, connection, format and scope problems. Splitting is intended for real context/output limits, not for every error.

## Questions, pause and progress

If information is missing, only the affected task is deferred. Independent tasks without shared affected files continue. If all remaining tasks depend on it, “Why tasks are waiting” shows the blockers. Answers are applied before the next run. All open questions are visible in the cockpit. Use the speaker icon/volume to set the sound; browsers allow sound only after user interaction.

Pause after run stops at a run boundary. Resume run cancels a still pending pause. After a pause has already happened, use Start / Resume. Stop now requests cancellation; running model HTTP requests may last until timeout.

“Currently verified” means valid verification evidence. “Already implemented” counts tasks that succeeded at least once. “To recheck” means changed inputs or dependencies. A new extension increases the total scope; the percentage may therefore legitimately decrease. Completed, unaffected tasks are not processed again. Unknown older verification evidence is checked once during migration, not adopted unchecked.
