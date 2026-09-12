---
name: create-plan
description: Turn a GitHub issue, spec, brainstorm or task description into a file:line-grounded implementation plan with phases and machine-checkable success criteria, written to docs/exec-plans/backlog/<slug>.md and registered in the INDEX. Use when the user says "create a plan", "plan this", "how should we build X". A plan carries no open question.
argument-hint: "<#N | issue URL | spec path | brainstorm path | task description>"
---

# Create Plan

Honour `.agents/skills/README.md`. You turn a WHAT into a HOW. Output is a **plan document**, precise enough that `/implement` executes it without re-deciding scope: exact paths, `file:line` anchors, the code shape where it is the decision, and criteria a command settles.

Position: `/file-an-issue` (or a picked issue) → **`/create-plan`** → `/implement` → `/review` → `/open-pr`. Input is normally one GitHub issue (one plan per issue); also a spec, brainstorm or bare description.

## Step 0 — Facts and naming
Repo facts from `AGENTS.md`: `check`, `docs/exec-plans/{backlog,active,completed,superseded}`, `issues_repo`, board. `ls docs/exec-plans/*/` for the naming convention (bare slug per Contract 2; no date prefix). No argument → ask for the issue, spec or task, then wait.

## Step 1 — Context
1. Read every mentioned file **fully**. Derive the slug (`GH-<N>-<topic>` when an issue exists) and read any `docs/brainstorm/` or `docs/specs/` file for it first.
2. Issue given: `gh issue view <N> --repo mhmzdev/hisab-whatsapp --json title,body,url,labels,state,assignees`. It **is** the ticket: settled decisions from its body, its `Done when` boxes seed the criteria. Check blockers (`blockedBy` via `gh api graphql`); an open blocker → say so and stop unless told to plan ahead.
3. If the WHAT is still fuzzy or the approach was never grilled and touches a risk area (the strict-check path, entry numbering, the store and offset, language strings, anything privacy-adjacent), **recommend `/grill-me` first**. Do not plan a moving target.

## Step 2 — Targeted research
Grep/read **only** the areas the plan touches. For a new tool: `tools.py` schema + `Tools` method, the `ledger.py` function, the prompt line in `agent.py`, and the smoke test that covers the sibling. For a transport change: `wa.py` and `loop.py` around the offset and the store. For setup or language: `setup.py` and the three-language dicts in `i18n.py`. Note exact `file:line` anchors. Read `tests/smoke.py` to see how the sibling is tested.

## Step 3 — Criteria (the contract)
Each criterion carries exactly one:
- `verify: python3 tests/smoke.py` — the repo check; every plan includes it.
- `verify: <command>` — another command whose exit 0 proves it (`docker build -q -t hisab-whatsapp .`, `hledger -f sample-vault/hisab.md check --strict`, `python3 tests/make_sample.py`).
- `verify: manual <numbered steps>` — terminal mode via `tests/demo_terminal.sh`, or the phone against the demo agent; name the exact lines to type and the expected reply shape.
Rewrite anything vacuous into something provable.

## Step 4 — Write `docs/exec-plans/backlog/<slug>.md`

```markdown
---
slug: <slug>
issue: <N or none>
status: backlog
open_questions: none
---

# <type>: <title>          ⬜ BACKLOG

## Problem
Why this exists. Link the issue / spec.

## Approach
The design in prose. Which existing pattern it reuses; which invariants it keeps (six tools, strict check, entry numbers, offset-after-batch, three languages, privacy).

## Success criteria
- [ ] <criterion> — `verify: …`
- [ ] Repo check passes — `verify: python3 tests/smoke.py`

## Phases
### Phase 1 — <name>
**Status:** Not started
- Files: `hisab/…` (`file:line` anchors), `tests/smoke.py`
- Change: what, in enough detail that no decision remains
- Test: the assertion to add

### Phase 2 — …

## Risks
- ...

## Out of scope
- ...
```

Sizing: one phase ≈ one context window. Tool + prompt + test is one phase; the phone path is its own. Any new user-facing string appears in all three languages in `i18n.py` in the same phase.

## Step 5 — Register and hand off
Add a row to `docs/exec-plans/INDEX.md` (Backlog table: file, problem, depends on). Then offer via one question: **Implement now** (`/implement`) · **Refine** (`/refine-approach`) · **Grill first** (`/grill-me`) · **Leave in backlog**.

## The no-open-questions contract
`open_questions: none` is a claim you make only when true. A fork the user has not decided goes back to `/grill-me`; it never ships inside a plan as "TBD".

## What NOT to do
- Write code. Put the plan anywhere but `backlog/`. Skip the INDEX row. Invent a criterion you cannot verify. Re-run a full audit when the brainstorm did recon. Leave a question open.
