---
name: codex-harness-review
description: Review Codex Harness project changes against project docs, architecture, ADRs, tests, critical rules, and buildability. Use when the user asks to review a diff, commit, pull request, uncommitted changes, or harness-generated step output, especially as the Codex replacement for the old .claude/commands/review.md workflow.
---

# Codex Harness Review

## Review Setup

Read these files before judging the change:

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/PRD.md` when product behavior is relevant
- `docs/UI_GUIDE.md` when UI behavior or presentation is relevant

Inspect the target diff using the appropriate Git command:

- uncommitted changes: `git diff --stat` and `git diff`
- staged changes: `git diff --cached --stat` and `git diff --cached`
- commit: `git show --stat <commit>` and `git show <commit>`
- branch or PR base: `git diff --stat <base>...HEAD` and `git diff <base>...HEAD`

## Checklist

Prioritize concrete defects over style. Check:

1. Architecture compliance: changed files follow `docs/ARCHITECTURE.md`.
2. Stack compliance: implementation does not violate `docs/ADR.md`.
3. Test coverage: new behavior has focused tests or a defensible reason why not.
4. Critical rules: no `CRITICAL` rule in `AGENTS.md` is violated.
5. Buildability: the relevant build, lint, typecheck, and test commands pass or the reason they were not run is explicit.
6. Harness metadata integrity: phase and step status files use valid statuses and include required summaries, error messages, or blocked reasons when applicable.
7. Scope control: the change does not include unrelated refactors, generated noise, or broad rewrites outside the requested step.

## Output

Lead with findings ordered by severity. Include file and line references when possible.

Use this table only after findings or when the user specifically asks for checklist output:

| Item | Result | Notes |
| --- | --- | --- |
| Architecture | pass/fail | <details> |
| Stack | pass/fail | <details> |
| Tests | pass/fail | <details> |
| CRITICAL rules | pass/fail | <details> |
| Buildability | pass/fail | <details> |

If there are no defects, state that clearly and list any verification commands that could not be run.

## Fix Guidance

When reporting a violation, give the smallest concrete fix. Prefer targeted changes over broad rewrites. If a failure is caused by missing project context, ask for that context instead of guessing.
