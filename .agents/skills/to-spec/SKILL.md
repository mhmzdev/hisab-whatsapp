---
name: to-spec
description: Turn a hardened discussion into a numbered written spec — a WHAT/WHY contract with problem, solution, user stories, decisions and testing seams — saved to docs/specs/<NNN>-<slug>.md and registered in its INDEX. Use when the user says "spec this out", "write this up as a spec", "make a spec". Synthesises the conversation; does not re-interview.
argument-hint: optional spec slug or brainstorm doc path
---

# To-Spec

Honour `.agents/skills/README.md`. Crystallise a discussion that already happened into a durable **spec**: the WHAT/WHY contract the rest of the lifecycle draws from. The HOW comes later.

```
/brainstorm → /grill-me → **/to-spec** → /file-an-issue → /create-plan → …
```

The next step is `/file-an-issue`, which slices the spec into GitHub issues — behind a **human gate**: present the spec, wait for approval.

**A spec is temporary; GitHub is the durable contract.** Once `/file-an-issue` runs, it copies Problem + Solution + Out of scope into the parent issue and links the children; from then on the issue is the source of truth and the file is disposable (`status: ticketed`, frontmatter carries `parent:`). Never link into a spec from other docs; link to the issue.

## Step 0 — Do you have material?
If the conversation has not settled the WHAT (approaches still open, scope undefined), **stop and recommend `/brainstorm` then `/grill-me`.** A spec around an unresolved question gives the ambiguity a filename.

## Step 1 — Gather
The conversation above is the primary source. Read `docs/brainstorm/<slug>.md` if it exists. Only if the discussion never touched the code: a light grounding pass (describe what exists, `file:line`). Use the repo's vocabulary from `AGENTS.md`: entry, posting, ledger, quarter file, tool, store, setup, template, language.

## Step 2 — Testing seam (the one question you may ask)
Confirm with the user where this is verified: `tests/smoke.py` (no network — the default), `tests/demo_terminal.sh` (needs a model key), or the phone against the demo agent. Prefer the highest seam that gives honest confidence; prefer existing seams over new ones.

## Step 3 — Number and write
`ls docs/specs/` → highest `NNN-` prefix + 1, zero-padded (`001` if empty). Write `docs/specs/<NNN>-<slug>.md`:

```markdown
---
slug: <slug>
status: draft
last_verified: <YYYY-MM-DD>
---

# <NNN> — <Feature> — Spec

## Problem
Who feels it, when, what it costs. No implementation.

## Solution
In plain terms. Still no implementation.

## User stories
1. As a <person texting the agent / shop owner / self-hoster / judge in a terminal>, I can <X> so that <benefit>.

## Decisions
Tool shape, prompt rule, ledger convention, store field, language strings — the clarifications the grilling produced. Which existing patterns it reuses; which invariants it respects (six tools, strict check, entry numbers, offset-after-batch, three languages).

## Testing decisions
The seam(s) from Step 2 and the closest prior-art test to mirror in tests/smoke.py.

## Out of scope
- <explicitly excluded>

## Further notes
- Open questions, links to the brainstorm doc.
```

## Step 4 — Register
Add a row to `docs/specs/INDEX.md` (`| [NNN](NNN-slug.md) | title | draft | date |`); create the file with a one-line header if absent.

## Step 5 — Hand off (human gate)
Present the spec and wait. Offer: **Slice into issues** (`/file-an-issue`, expected) · **Plan it directly** (`/create-plan`, single-slice) · **Stop**.

## What NOT to do
- Interview the user (only the seam question). Bake in file paths or code that will go stale (a schema or reply shape that *is* the decision is fine). Write the HOW. Invent a fact the discussion did not settle — flag it under Further notes.
