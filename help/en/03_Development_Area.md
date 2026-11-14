# Development Area

## Introduction

The first time the development area is opened, its own tutorial starts. It explains the six tabs in their working order, the live output and cancellation. It can be restarted from the help page or the tutorial button next to the tabs.

## Improvements

Textual extensions can be submitted even during development. They are planned at the next task boundary; if another assistance function is currently running, at the latest on the next start. Existing tasks are not deleted. Each extension receives new IDs and file conflicts are linked via dependencies. Invalid plans do not replace the existing plan.

For AI suggestions, choose the areas architecture, code quality, features, appearance, speed, tests and security. A general model can be suggested or chosen manually. This preselection is not an objective ranking. The analysis scope names read excerpts and omitted files. Mark suggestions individually and confirm them. If the project has changed meanwhile, renew the analysis. On errors in an extension request, enter the corrected request again.

## Files & editor

Choose a file, edit and save it, also with Ctrl+S. Previous content is backed up. On external changes, a revision comparison prevents overwriting. Unsaved drafts are cached in the browser. Binary files, secret files and internal control folders are locked in the editor.

## AI changes

Choose a file, formulate the request, review the diff and apply it explicitly. Truncated responses are rejected; concurrent changes lead to a save conflict. Run suitable tests afterwards.

## Run & check

Create the project environment; choose a Python file and enter arguments as a JSON list. Clicking Install pytest, Ruff & mypy grants exactly this installation once in the project environment. The general automatic pip permission remains unchanged. Tests, linting and type checking are separate jobs. Live output and cancellation are shown below.

## Git and workflows

Initialize a Git repository in the project, review diff and history. Committing requires an explicit file selection. Independently staged files are not committed. In workflows, select nodes, change configuration and inputs, save and run. The CSV→Excel acceptance checks reading, validation, duplicates and Excel export. Python nodes receive `--input` and `--output` with JSON paths.
