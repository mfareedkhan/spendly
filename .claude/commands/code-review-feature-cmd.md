---
description: Run parallel security and quality review on a completed feature
argument-hint: "<spec-name>"
allowed-tools: Read, Bash(git:*), Agent
---

A spec name is required. Usage: `/code-review-feature <spec-name>`
Example: `/code-review-feature 03-login`

If $ARGUMENTS is empty, stop here.

## Step 1 — Collect changes

Run both of these and combine the output into a single diff:
```bash
git diff
git diff --staged
```

If both return empty output, stop and say:
"No changes detected. Stage or make changes before running a review."

## Step 2 — Verify spec exists

Check that `.claude/specs/$ARGUMENTS.md` exists.
If not, stop and say:
"Spec file not found: .claude/specs/$ARGUMENTS.md"

## Step 3 — Launch parallel reviews

Spawn BOTH subagents simultaneously — not sequentially:

**spendly-security-reviewer**: Review the diff against `.claude/specs/$ARGUMENTS.md` and the relevant source files. Focus exclusively on security vulnerabilities.

**spendly-quality-reviewer**: Review the same diff for Flask best practices, code organization, naming, and maintainability. Do not comment on security.

Both agents receive:
- The combined diff from Step 1
- The spec file at `.claude/specs/$ARGUMENTS.md`
- Access to `app.py`, `database/db.py`, and relevant templates

## Step 4 — Unified report

After both reviews complete, consolidate findings into one report:

```
Code Review — [Feature Name]

🚨 Critical / High (Security)
[Critical security findings first]

🔧 Change Requests (Quality)
[Quality issues that should be fixed]

⚠️ Medium / Low (Security)
[Lower-priority security notes]

💡 Suggestions
[Optional improvements from both reviewers]

✅ Approved patterns
[What both reviewers found clean and correct]
```

Merge duplicate findings when both agents flagged the same code for different reasons.

## Step 5 — User approval gate

Present the full report and ask:
"Do you want me to implement these fixes? (yes/no)"

**Do NOT edit any files before receiving explicit approval.**

## Rules
- Both reviewers must launch simultaneously — never sequentially
- Partial results from a failed subagent cannot be presented as a complete review
- No file modifications until the user explicitly approves
