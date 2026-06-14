---
description: Write and run tests for a completed Spendly feature
argument-hint: "<spec-name>"
allowed-tools: Read, Bash, Write, Glob, Grep, Agent
---

A spec name is required. Usage: `/test-feature <spec-name>`
Example: `/test-feature 05-backend-routes-for-profile-page`

If $ARGUMENTS is empty, stop here.

## Pre-flight check

Verify `.claude/specs/$ARGUMENTS.md` exists.
If not, stop and say:
"Spec file not found: .claude/specs/$ARGUMENTS.md"

## Stage 1 — Test Generation

Invoke the `spendly-test-writer` subagent with:
- The spec at `.claude/specs/$ARGUMENTS.md`
- The app structure (`app.py`, `database/` directory)
- Target output file: `tests/test_$ARGUMENTS.py`

The test writer must:
- Base all tests on the spec — not the implementation
- Cover happy path, auth guards, validation, DB side effects, HTTP semantics, and edge cases
- Deliver a complete, ready-to-run pytest file

**Do not proceed to Stage 2 until Stage 1 fully completes.**
If test writing fails, stop immediately.

## Stage 2 — Test Execution

Invoke the `spendly-test-runner` subagent with:
- The generated test file at `tests/test_$ARGUMENTS.py`
- The spec at `.claude/specs/$ARGUMENTS.md`
- Access to `app.py` and `database/` for failure diagnosis

The test runner must:
- Verify the test file exists before running
- Run only `pytest tests/test_$ARGUMENTS.py` — not the full suite
- Diagnose failures by cross-referencing the spec and source code
- Classify each failure as a bug or a missing feature

## Final report

Combine both stages into one summary:

```
Test Pipeline — [Feature Name]

📝 Tests written: N
📁 File: tests/test_<spec-name>.py

📊 Results
| Total | Passed | Failed |
|-------|--------|--------|
| N     | N      | N      |

[Failure details if any]

✅ Verdict: Ready for code review / Needs fixes
```

## Rules
- Stage 2 cannot begin until Stage 1 fully completes
- No code fixes — analysis only
- Run only the specific test file, never the full suite
