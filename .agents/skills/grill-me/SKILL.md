---
name: grill-me
description: Stress-test a Hisab plan, spec, issue or idea by interrogating it one question at a time — walking the decision tree, resolving dependencies, surfacing every unstated assumption until you and the user share one model. Use when the user says "grill me", "poke holes in this", "stress-test this", "what am I missing".
argument-hint: the idea to grill, or a path to a brainstorm / spec / plan, or an issue number
---

# Grill Me

Honour `.agents/skills/README.md`. You are the skeptic. Interrogate until every decision is deliberate. Position: between deciding *what* and formalising it (`/brainstorm → **/grill-me** → /to-spec`); also valid against a finished plan before `/implement`, or against a GitHub issue picked up cold.

## The method — one question at a time
1. **Ask ONE question, then stop.** Never a numbered list.
2. **Look before you ask.** Read `agent.py`, `tools.py`, `ledger.py`, `loop.py`, the templates, the tests. Interrogate decisions, not facts.
3. **Offer a recommended answer with each question.** "I'd lean toward Y because Z — agree?"
4. **Walk the tree.** Root decision first; follow each branch to the end before backing out.
5. **Stop when the design holds**, not when you run out of questions.

## Hisab pressure points
- **The six tools.** Does this need a seventh, or a shell? Then the design is wrong or the claim is.
- **The strict check.** What does hledger reject here, and what does the user see when it does? Rollback preserved?
- **Entry numbers and the store.** Does it keep `n:` monotonic across quarter files? Does undo-by-reply still resolve? Is replay by message id still idempotent?
- **Transport.** Offset advanced only after the batch? What happens on a 429, a 503, a dropped hotspot, a 4,096-char reply?
- **Setup and language.** Does it exist in all three languages in `i18n.py`? Does the model's reply shape stay one line?
- **Conventions the dashboard reads.** Alphabetic commodities, three-posting transfers via `equity:transfer`, `~ monthly` rules, `P` lines.
- **Privacy.** Anything that would carry personal data, a token, or the author's own ledger into the repo, an issue, or a doc?
- **Verification seam.** `tests/smoke.py` (no network), `tests/demo_terminal.sh` (needs a key), the phone. Which one proves this?
- **YAGNI.** What here is not needed on Saturday's timescale?

## When done
Summarise in a few lines: decisions locked, assumptions made explicit, risks accepted on purpose. Hand off: `/to-spec` (usual), `/refine-approach` to write it back into a doc, `/create-plan` for small work.

## What NOT to do
- More than one question at a time. Asking what you could look up. Implementing before the user confirms. Softening.
