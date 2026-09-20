---
slug: GH-43-transfer-direction
issue: 43
status: backlog
open_questions: none
---

# feat: a transfer receipt knows which side the user is on          ⬜ BACKLOG

## Problem

[#43](https://github.com/mhmzdev/hisab-whatsapp/issues/43): a bank or wallet receipt names both parties, but Hisab never knew which one was the user, so the model asked a question that mixed directions — *"expenses:family, income:other, or equity:transfer?"* — where the first is money out, the second money in and the third neither. The user does the model's job, and a wrong pick silently flips the sign of an entry.

Every decision below was settled in the grill of 2026-09-20 ([the issue's first comment](https://github.com/mhmzdev/hisab-whatsapp/issues/43#issuecomment-5748020716)). This plan implements them and decides nothing new.

Three facts the grill established, which shape the work:
- Setup stores only `language`, `mode` and `currency` (`hisab/setup.py:141`). It never asked who the user is.
- The model cannot save a fact: the six tools write entries, accounts and category rules, and identity is none of those. So the name has to be asked in setup, where the loop writes it, not learned by the model.
- `hisab/agent.py:26` claims the SMS path matches "the masked account digits" to a money account. Nothing stores digits — `money_account()` slugs "Alfalah bank" into `assets:bank:alfalah` — so that clause only ever worked by luck.

## Approach

Three seams, in this order: **setup learns the name**, **the prompt carries one direction ladder**, **a by-hand model check proves the model follows it**.

### 1. Setup: one more question, and numbered questions

`holder` joins both flows as the **second** key, right after `mode` (`hisab/setup.py:9-10`):

```python
PERSONAL = ["mode", "holder", "currency", "money", "cards", "income", "investments", "donations"]
SHOP     = ["mode", "holder", "currency", "money", "suppliers", "staff", "income_shop", "fixed"]
```

It is second, not first, because **language detection lives on the `mode` answer** (`setup.py:58-71`): "dukaan" means Urdu, "personal" means English. A name carries no such signal, so a name-first flow would set every Roman-Urdu user to English. Nothing about detection changes.

`answer()` gains a branch beside `mode` and `currency` (`setup.py:61-78`):

```python
elif key == "holder":
    name = " ".join(t.split())
    if _none(name):
        st["answers"]["holder"] = ""          # skipped: the ladder falls through to asking
    elif not (2 <= len(name) <= 60) or re.search(r"\d", name):
        return q("holder_again", lang), False, None
    else:
        st["answers"]["holder"] = name
```

A digit in the answer is the one rejection worth having: it catches an account number pasted where a name was asked. `write()` stores it beside the rest (`setup.py:141`): `{"language": …, "mode": mode, "currency": cur, "holder": a.get("holder", "")}`.

`Ledger.holder` is a read-only property next to `currency` (`hisab/ledger.py:70-73`), the shape #65 established: `settings().get("holder")` when it is a non-empty string, else `""`. Every construction path — self-host, hosted tenant, `--stdin` — gets it for free.

**Numbering.** Every onboarding message carries `n/8`, Latin digits in both languages, because both flows are exactly 8 questions once `holder` is in. The greeting is `1/8`. A rejected answer repeats its own number, since the step has not moved. One helper in `setup.py` does it, so no `Q` string in `i18n.py` carries a number:

```python
def _numbered(text, step, total):
    return f"{step + 1}/{total} · {text}"
```

`start()` numbers the greeting; `answer()` numbers the next question and every `*_again` reply with the current step.

### 2. The prompt: one direction ladder for all three inputs

`SYSTEM` (`hisab/agent.py:16-33`) gains the holder line and one ladder, replacing the direction rules scattered across the typed-words line (`:19`), the receipt line (`:20`) and the SMS line (`:26`). `system()` (`agent.py:49-52`) passes `holder=self.ledger.holder`, and renders the account-holder line only when it is set.

The ladder, in the prompt's own voice:

```
- Direction — for a typed message, a forwarded SMS and a receipt photo alike, in this order:
  1. What the user said wins: "Uzair ko 35000 diye" is money out whatever the image shows. A photo's caption counts as what the user said.
  2. The document's own words: debited/paid/sent/transferred to = out; credited/received/deposit from = in.
  3. The account holder name{holder_clause}: whichever side of the receipt it names is the user's side.
  4. If none of those settles it, ask ONE question about direction alone — "did this money leave you or arrive?" — and never mix money-in and money-out accounts in one question.
- Both sides name the account holder: the user moved their own money. When both institutions match declared money accounts, post the three-posting transfer (destination +amount, source -amount, bare equity:transfer) with no question, and name both accounts in the reply. When the other institution is not a declared account — a different person with the same name, or an account Hisab does not know — ask ONE question: your own account, or another person?
- Direction known, category not: ask ONE question whose three candidates are all on that side. A transfer to a named person offers assets:receivable:<name> among the three; it is never the silent default.
- A transfer entry's reply names the account used: "posted #4 — lent to Uzair 35,000 → assets:receivable:uzair — month out 3,000". Ordinary entries do not name the account.
```

`{holder_clause}` is ` (the user is {holder})` when set, and the rung is dropped entirely when the name was skipped. The masked-digits clause at `:26` is deleted.

Everything else about the reply is untouched: one line, no advice, the same shapes per language in `MODEL_LANG`.

### 3. `tests/check_receipts.py`: a by-hand model check

A new script beside `tests/check_endpoint.py`, run with a key, **never part of the repo check**, because a model can fail it without anything having regressed. It gates nothing; it is run before a release or after a prompt change, and its result is pasted into the PR.

It builds a temp ledger (never `vault/`), runs setup with a fixed holder name, and drives `Agent.run` against three fixtures in `tests/fixtures/receipts/`. It asserts **tool calls, not wording** — `Agent.run` returns `(reply, tools)`, and `Tools` records what it was asked to do:

| Fixture | The holder is | Passes when |
|---|---|---|
| `sender.jpg` | the sender | an `append_entry` moving money **out** of a declared account, or a question whose candidate accounts are all money-out |
| `receiver.jpg` | the receiver | the mirror: money **in**, or an all-money-in question |
| `stranger.jpg` | neither party | a question about direction, and **no** `append_entry` |

`Tools` does not record calls today; the script takes the cheapest seam that does not change behaviour — wrapping `Tools.call` in the script itself — so `hisab/tools.py` is untouched.

Missing fixtures are a clean skip with a message naming the directory, so the script can land before the images do. The fixtures are the owner's, blurred except the holder name and the amount, and reviewed before they are committed.

### Invariants kept

Six tools — no new tool; the name is written by setup, which is the loop, not the model. The strict check, entry numbers, `next_entry_number` and undo-by-reply are untouched. Transport is untouched. Every new user-facing string (`holder`, `holder_again`) exists in `en` and `ur`. The reply stays one line. Transfers keep the three-posting `equity:transfer` shape the Obsidian dashboard reads. Privacy: the holder name lives in the user's own `settings.json` (already inside `export-ledger`'s ZIP); nothing new leaves the machine, and hosted tenants' names stay in their own vault, never in Firestore.

## Success criteria

- [ ] Setup asks the holder name as question 2 in both flows, in `en` and `ur`, and stores it in `settings.json`; *skip* stores `""`; an answer containing a digit is re-asked — `verify: python3 tests/smoke.py`
- [ ] Every onboarding message is numbered `n/8` with Latin digits in both languages, the greeting is `1/8`, the last question is `8/8`, and a rejected answer repeats its own number — `verify: python3 tests/smoke.py`
- [ ] `Ledger.holder` returns the stored name, and `""` when it is missing, blank, not a string or the settings file is malformed — `verify: python3 tests/smoke.py`
- [ ] `agent.system()` names the holder when set and contains no holder rung when it was skipped; both renderings carry the four-step ladder, the both-sides-match rung and the transfer-reply rule — `verify: python3 tests/smoke.py`
- [ ] `hisab/agent.py` no longer claims to match masked account digits — `verify: ! grep -n "masked account digits" hisab/agent.py`
- [ ] A setup begun before this change (a stored flow without `holder`) finishes without raising and without a holder — `verify: python3 tests/smoke.py`
- [ ] `tests/check_receipts.py` exits 0 with a clear skip message when `tests/fixtures/receipts/` is empty, and never touches `vault/` — `verify: python3 tests/check_receipts.py` (exit 0, prints SKIP)
- [ ] AGENTS.md's Commands table has a row for it, and the question-count wording in `AGENTS.md:24`, `ARCHITECTURE.md:30`, `README.md:107` and `hisab/setup.py:1` still matches the code — `verify: python3 tests/smoke.py` (a docs assertion: the flow length equals the number in those files)
- [ ] The sample ledger still checks, and a regenerated sample is byte-identical — `verify: hledger -f sample-vault/hisab.md check --strict`
- [ ] **Post-merge, owner + lead, left unticked:** the three blurred fixtures pass `python3 tests/check_receipts.py` with a real key; then on the demo agent, a receipt where the owner is the sender, one where they are the receiver, and one naming neither — the first two post the right direction, the third asks about direction — `verify: manual`
- [ ] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Setup learns the name, and counts its questions
**Status:** Not started
- Files: `hisab/setup.py:1, 9-10, 49-89, 141`, `hisab/i18n.py` (`Q`, near `:88`), `hisab/ledger.py:70-73`, `tests/smoke.py:65-66, 87, 108-110, 389-393, 1044`
- Change:
  - `PERSONAL`/`SHOP` gain `holder` as the second key; the module docstring says nine questions counting the greeting, or keeps "at most eight" if that stays true — whichever the docs assertion below checks.
  - `answer()`: the `holder` branch above. `_numbered()` and its use in `start()`, in the next-question return and in every `*_again` return.
  - `write()`: `holder` into `set_settings`.
  - `Ledger.holder` property.
  - `i18n.Q`: `holder` (en: "What is the full name on your accounts, as your receipts show it? Not a nickname. Or *skip*." / ur equivalent) and `holder_again` (en: "Just the name, no numbers. Or *skip*." / ur equivalent).
- Test: every existing smoke scenario that drives setup gains the holder answer in its list — this is the breaking edit to watch. New assertions: the name is stored and read back through `Ledger.holder`; *skip* and a digit-bearing answer; `1/8` on the greeting through `8/8` on the last question in both flows and both languages; a rejected mode answer and a rejected currency answer repeat their number; the pre-`holder` stored flow at `:389` still completes.
- Verify: `python3 tests/smoke.py`

### Phase 2 — The prompt carries the ladder
**Status:** Not started
- Files: `hisab/agent.py:16-33, 49-52`, `tests/smoke.py` (the prompt section)
- Change: the holder line and the ladder as written above; delete the masked-digits clause; `system()` renders the holder rung only when the name is set.
- Test: `agent.system()` on a ledger with a holder contains the name and the ladder's four steps; on one without, contains neither the name nor the holder rung, and still contains the other three steps; the string "masked account digits" appears nowhere in `hisab/`; the reply-shape lines in `MODEL_LANG` are unchanged.
- Verify: `python3 tests/smoke.py`

### Phase 3 — The by-hand model check, and the docs
**Status:** Not started
- Files: `tests/check_receipts.py` (new), `tests/fixtures/receipts/README.md` (new: what each fixture must show, and the blurring rule), `AGENTS.md:24` and its Commands table, `ARCHITECTURE.md:30`, `README.md:107`
- Change:
  - The script: `--config` like `check_endpoint.py`, a temp ledger, a fixed holder name matching the fixtures, the three cases, PASS/FAIL per case, exit 1 on any failure, exit 0 with SKIP when the fixtures are absent. It wraps `Tools.call` to record calls rather than touching `hisab/tools.py`.
  - Docs: the Commands row; the question-count wording in the three files and the `setup.py` docstring.
- Test: smoke's docs assertion ties the flow length to the number in those files, so the next question that is added cannot leave them stale.
- Verify: `python3 tests/check_receipts.py` (exit 0, SKIP) and `python3 tests/smoke.py`

## Risks

- **The model is the thing being changed, and the repo check cannot judge it.** Smoke proves the prompt and setup carry the rule; only `check_receipts.py` and the phone prove the model follows it. Accepted in the grill.
- **`check_receipts.py` can fail for reasons that are not a regression** (a model's bad day, a provider outage). That is why it gates nothing and is never part of the repo check.
- **Adding a setup question touches every setup scenario in smoke.** Phase 1 is where this plan is most likely to go long; the answer lists are the first thing to fix.
- **Two people sharing one name** defeats the name match. The both-sides rung's institution guard catches the common case; `undo` catches the rest.
- **Existing ledgers have no holder.** They fall through to the direction question until their owner runs `/setup` again. No migration prompt, by decision.
- **A longer system prompt costs tokens on every turn.** The ladder replaces three scattered direction rules, so the net growth is small, but it is growth.

## Out of scope

- Storing masked account digits, or matching them to money accounts — the false claim is deleted, and making it real is its own ticket.
- A seventh tool, or teaching `learn_rule` to store identity.
- Asking existing users for their name, or any migration prompt.
- Changing what `undo` does, or adding a second reply line.
- The landing page and the portal.
- Any live run before merge: no phone, no real model call from the lane. The fixtures are the owner's to place.
