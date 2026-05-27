---
name: codex-harness-planner
description: Generate Codex Harness phase plans and step files from project documents. Use when the user asks to create, design, split, or scaffold a harness task or phase under phases/, especially as the Codex replacement for the old .claude/commands/harness.md workflow.
---

# Codex Harness Planner

## Workflow

Read `AGENTS.md` and every relevant file under `docs/` first, especially `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`, and `docs/UI_GUIDE.md` when present. Use those files as the source of truth for project scope, architecture, stack, and constraints.

If the implementation goal is underspecified, discuss the missing decisions with the user before writing phase files. Do not invent product requirements, external services, auth flows, data models, or UI behavior when the docs are silent.

When the user asks for a plan, split the requested task into small sequential steps and create the harness files described below. Create planning files only; do not implement product code while using this skill unless the user explicitly changes the task.

## Step Design Rules

Use these rules for every step:

1. Keep scope small. One step should touch one layer or module where possible.
2. Make every step self-contained. A separate Codex session must be able to execute it without reading the prior chat.
3. Force context gathering. List the docs and previously created or modified files that the step must read first.
4. Give signature-level direction. Specify interfaces, file paths, responsibilities, invariants, and edge cases; leave routine implementation details to the executing agent.
5. Make Acceptance Criteria executable. Use real commands such as `npm run build && npm test`, `pytest`, or the project-specific equivalent.
6. Write concrete prohibitions in the form "Do not X. Reason: Y."
7. Name steps with kebab-case slugs.

## Files To Create

Create or update `phases/index.json`:

```json
{
  "phases": [
    {
      "dir": "0-mvp",
      "status": "pending"
    }
  ]
}
```

If the file already exists, append the new phase entry only if it is not already present. Do not add timestamps at creation time; `scripts/execute.py` records them.

Create `phases/{phase-name}/index.json`:

```json
{
  "project": "<project-name>",
  "phase": "<phase-name>",
  "steps": [
    { "step": 0, "name": "project-setup", "status": "pending" },
    { "step": 1, "name": "core-types", "status": "pending" },
    { "step": 2, "name": "api-layer", "status": "pending" }
  ]
}
```

Use `project` from `AGENTS.md` or ask the user if it is absent. Use 5 to 10 steps for a typical feature, fewer for very small tasks.

Create one `phases/{phase-name}/stepN.md` per step with this structure:

````markdown
# Step N: step-name

## Files To Read

Read these files first and align the implementation with their constraints:

- /AGENTS.md
- /docs/ARCHITECTURE.md
- /docs/ADR.md
- <relevant files from previous steps>

## Task

<Specific implementation instructions. Include target paths, expected interfaces,
state transitions, validation rules, and non-obvious design constraints.>

## Acceptance Criteria

```bash
<real verification command>
```

## Verification Procedure

1. Run the Acceptance Criteria commands.
2. Check architecture and stack alignment against `docs/ARCHITECTURE.md` and `docs/ADR.md`.
3. Update `phases/{phase-name}/index.json` for this step:
   - success: set `"status": "completed"` and add a one-line `"summary"`
   - repeated failure: set `"status": "error"` and add `"error_message"`
   - user intervention needed: set `"status": "blocked"` and add `"blocked_reason"`

## Prohibitions

- Do not change files outside this step's scope. Reason: later steps depend on narrow, reviewable changes.
- Do not skip tests or verification commands. Reason: the executor relies on step status reflecting real validation.
````

## Execution

After the user reviews and accepts the generated phase files, run:

```bash
python scripts/execute.py {phase-name}
python scripts/execute.py {phase-name} --push
```
