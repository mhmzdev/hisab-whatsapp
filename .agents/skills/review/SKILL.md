---
name: review
description: Close a feature's inner loop — derive the acceptance checklist from intent plus diff, verify every criterion at the cheapest honest layer (smoke test, terminal mode, phone), check Hisab's own conventions, and persist docs/feat-checklist/<slug>.md that /open-pr seeds the Test Plan from. Use when the user says "review this", "check before merging", "is this done".
argument-hint: optional plan path, issue number, or diff scope — defaults to the current branch diff
---

# Review

Honour `.agents/skills/README.md`. Position: `/implement` → **`/review`** → `/open-pr`. Two jobs: **is it done** (every criterion verified, honestly) and **is it right** (Hisab's conventions). Advisory: report first, fix only when asked.

## Step 1 — Scope and intent
- Paths given → those. Else `git merge-base HEAD main` → `git diff <base>...HEAD --name-only`. Announce the file count and areas.
- Find the intent: the plan for this slug in `docs/exec-plans/{active,completed}/`, its issue (`gh issue view`), the spec. The plan's success criteria and the issue's `Done when` boxes are the checklist's seed; add what the diff shows the intent implies.

## Step 2 — Verify each criterion at the cheapest honest layer
For each item, one verdict:
- `[x]` — proven by a named command or test you ran this run (`python3 tests/smoke.py`, a `hledger … check --strict`, `docker build`).
- `[?]` — needs a human: a terminal run (`tests/demo_terminal.sh`, lines to type, expected reply) or the phone. Write the exact steps.
- `[!]` — not done or broken. Say why with `file:line`.
Never tick on the user's behalf. Never mark `[x]` from reading code alone.

## Step 3 — Conventions checklist
- **Surface.** Still six tools? No shell, no free file access, no new network call outside the model, transcription and WhatsApp?
- **Writes.** Every ledger write through `Ledger.append` under the strict check with rollback? Entry numbers from `next_entry_number` only? Undo still by number?
- **Transport.** Dedup by message id kept; offset advanced only after the batch; replies chunked under 3,500; typing indicator sent?
- **Language.** Every new user-facing string in `i18n.py` in `en`, `ur`, `roman`? Model reply shapes still one line? Setup questions still in the chosen language?
- **Conventions the dashboard reads.** Alphabetic commodities, `equity:transfer` three-posting transfers, `~ monthly` rules, `P` lines.
- **Privacy.** Nothing personal, no token, no path from the author's machine, in code, tests, docs or the sample. `.env`, `config.yaml`, `vault/`, `scratch-*` untouched and ignored.
- **Tests.** Every new unit exercised in `tests/smoke.py`? Sample regenerated if `setup.py` changed?
- **Docs.** README still true? `config.example.yaml` updated for any new key?

## Step 4 — Persist and report
Write `docs/feat-checklist/<slug>.md`:

```markdown
# <slug> — acceptance checklist   (<n> proven · <n> manual · <n> failing)

- [x] <criterion> — `python3 tests/smoke.py` passes (test: <name>)
- [?] <criterion> — terminal: run `bash tests/demo_terminal.sh`, type `…`, expect `…`
- [!] <criterion> — <why>, hisab/ledger.py:123

## Findings
FINDING-01 · Important · hisab/loop.py:88 — <what, and the rule it breaks>
```

Chat summary: path, counts, every `[!]` and Critical/Important finding verbatim. A clean review says so in one line.

## Step 5 — Act only when asked
Offer: fix the failing items · fix specific findings · hand off to `/open-pr` · stop. After a fix, re-run the check and report which ids changed. The board card stays where it is (no in-review column).

## What NOT to do
- Fix before being asked. Tick manual items. Flag style you merely dislike (every finding maps to `AGENTS.md`). Expand past the scope.
