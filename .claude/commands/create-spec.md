---
description: Create a feature branch and spec document for the next Spendly step
argument-hint: "<step_number> <feature_name>"
allowed-tools: Read, Bash, Write, Glob
---

A step number and feature name are required.
Usage: `/create-spec <step_number> <feature_name>`
Example: `/create-spec 2 registration`

If $ARGUMENTS is empty or incomplete, stop and ask for the step number and feature name.

## Step 1 — Verify clean working directory

```bash
git status --short
```

If there are uncommitted changes, stop and say:
"Working directory is not clean. Commit or stash changes before creating a new spec."

## Step 2 — Parse arguments

Extract from $ARGUMENTS:
- step_number — the step number (e.g. "2")
- feature_name — the feature title in plain English (e.g. "registration")

Derive branch name: `step-<step_number>-<feature_name_kebab_case>`
Example: `step-2-registration`

## Step 3 — Check branch doesn't already exist

```bash
git branch --list step-<N>-<name>
```

If it exists, stop and say:
"Branch already exists: <branch-name>. Delete it first or choose a different name."

## Step 4 — Pull latest main and create branch

```bash
git checkout main
git pull origin main
git checkout -b <branch-name>
```

## Step 5 — Research the codebase

Read these files to understand current state:
- `CLAUDE.md`
- `app.py`
- `database/db.py`
- Any existing specs in `.claude/specs/`

## Step 6 — Generate spec document

Write a spec to `.claude/specs/<step_number>-<feature_name_kebab>.md` following this structure:

```markdown
# Spec: <Feature Name>

## Overview
[What this step accomplishes and why it matters]

## Depends on
[Prior steps this feature builds on]

## Routes
[List of GET/POST routes with auth requirement]

## Database changes
[New tables, columns, or helper functions needed]

## Templates
[Templates to create or modify]

## Files to change
[Existing files that need modification]

## Files to create
[New files to add]

## New dependencies
[Any new pip packages — flag if any]

## Rules for implementation
[Constraints specific to this feature]

## Definition of done
- [ ] [Verifiable checklist items]
```

Follow all constraints from `CLAUDE.md`:
- No ORMs — raw parameterized SQLite queries only
- Werkzeug for password hashing
- CSS variables — never hardcoded hex values
- All templates extend `base.html`
- `url_for()` for every internal link

## Step 7 — Report summary

Print:
```
✓ Branch created — <branch-name>
✓ Spec written — .claude/specs/<filename>

Next steps:
1. Review the spec
2. Implement the feature
3. Run /test-feature <spec-name> to validate
4. Run /code-review-feature <spec-name> before shipping
5. Run /ship-feature when ready
```
