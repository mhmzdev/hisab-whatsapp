---
name: brainstorm
description: Explore WHAT to build for Hisab and WHY through dialogue before any planning or code. Use when the user says "brainstorm", "let's explore", "think through this", or when a request is fuzzy enough that a plan would guess at scope. Produces docs/brainstorm/<slug>.md.
argument-hint: the feature or idea to explore
---

# Brainstorm

Honour `.agents/skills/README.md`. You are exploring an idea **before** it becomes a plan: nail down **WHAT** and **WHY**, not HOW. No code, no file lists, no phases.

```
/brainstorm → /grill-me → /to-spec → /file-an-issue → /create-plan → /implement → /review → /open-pr
  (what)       (harden)     (contract)   (slice)          (how)          (do)        (check)      (ship)
```

## Principles

1. **Ruthless YAGNI.** Hisab is a small product with a sharp claim: a ledger you text. Anything that turns it into an app with a chat window is out.
2. **The constraints are the product.** One agent, one creator, six tools, every write under `hledger check --strict`. A feature that needs a seventh tool or a shell is probably wrong; say so.
3. **One question at a time**, multiple choice, recommended default.
4. **Look before you ask.** `AGENTS.md`, `README.md`, `hisab/agent.py` (the prompt), `hisab/tools.py` (the surface) answer most questions.

## Flow

**Step 0 — Scope.** Which surface does the idea touch: the prompt (`agent.py`), a tool (`tools.py` + `ledger.py`), the transport (`wa.py`, `loop.py`), setup or language (`setup.py`, `i18n.py`), templates, Docker, docs. If it is a one-file fix, say so and recommend `/create-plan` or just doing it.

**Step 1 — Understand.** Light codebase pass over the area (read the 1–3 files that matter). Then surface the real requirement one question at a time: who hits this and when, on the phone or in the terminal; the smallest version; what a WhatsApp-native gesture could do instead of a command; what the strict check must reject. Explore 2–3 approaches, one line each with the trade-off, recommend one.

**Step 2 — Write** `docs/brainstorm/<slug>.md`:

```markdown
# <Topic> — Brainstorm

## Problem
Who feels it, when, in user terms.

## Goal
The smallest outcome that counts.

## Approaches considered
1. **<Name>** — <one line>. Reuses <X>. Trade-off: <Y>.
**Leaning toward:** <which, why>.

## Surfaces touched
prompt / tools / transport / setup / i18n / templates / docker / docs

## Open questions
- [ ] ...

## Out of scope (YAGNI)
- ...
```

**Step 3 — Hand off.** Offer: **Grill it** (`/grill-me`, the usual next step) · **Spec it** (`/to-spec`) · **Plan it** (`/create-plan`, small low-risk ideas) · **Refine** (`/refine-approach`) · **Pause**.

## What NOT to do
- No phases, file lists or code. No invented requirements. No 400-line doc: if it is that big, split the idea.
