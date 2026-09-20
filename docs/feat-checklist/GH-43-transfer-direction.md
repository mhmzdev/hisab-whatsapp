---
type: Checklist
title: GH-43-transfer-direction
description: Acceptance checklist for a transfer receipt knowing which side the user is on: the holder name asked in setup, one direction ladder in the prompt, and a by-hand model check against four receipt fixtures.
tags: [checklist, setup, agent, i18n, privacy]
timestamp: 2026-09-20T00:00:00Z
---

# GH-43-transfer-direction — acceptance checklist   (11 proven · 3 manual · 0 failing)

Plan: [GH-43-transfer-direction](../exec-plans/completed/GH-43-transfer-direction.md) · Issue: [#43](https://github.com/mhmzdev/hisab-whatsapp/issues/43) · Decisions: the issue's first comment (grill, 2026-09-20). Amended after the plan, by the lead: the both-sides rung is dropped with no holder; party labels ("Transferred To: <name>") are not direction words; an own-app-view rung works without a name (fixtures r1–r4).

- [x] Setup asks the holder name as question 2 in both flows, in `en` and `ur`, stores it in `settings.json`; *skip* (`skip`, `none`, `نہیں`) stores `""`; a digit, one character or 61 characters is re-asked — `python3 tests/smoke.py` ("setup: holder is question 2 of 8…")
- [x] Every onboarding message is numbered `n/8`, Latin digits, `1/8` on the greeting to `8/8` on the last question, in both flows and both languages; a rejected mode, holder or currency repeats its own number — same test
- [x] `Ledger.holder` is the stored name, and `""` when missing, blank, not a string, or the settings file is malformed — same test
- [x] A setup begun before this change (a stored flow without `holder`) finishes without raising and without a holder, numbered out of its own length (`3/7`) — same test
- [x] `agent.system()` names the holder when set; without one it contains neither the name, the holder rung nor the both-sides rung, and keeps the own-app-view rung — `python3 tests/smoke.py` ("prompt: one direction ladder…")
- [x] Both renderings carry the party-label rule, the own-app-view rule, the direction-known rule and the transfer-reply rule; the ladder is numbered without a gap (5 steps with a name, 4 without) — same test
- [x] `hisab/agent.py` no longer claims to match masked account digits — `! grep -n "masked account digits" hisab/agent.py`; also asserted by smoke
- [x] `tests/check_receipts.py` exits 0 with SKIP when its fixtures directory is empty, touches only a temp ledger, and its judge decides direction from tool calls — `python3 tests/smoke.py` ("check_receipts: …"); `hisab/tools.py` untouched (`git diff main...HEAD -- hisab/tools.py` is empty)
- [x] AGENTS.md's Commands row exists, and the question-count wording in AGENTS.md, ARCHITECTURE.md (two places), README.md (two places) and the `setup.py` docstring matches the flow length — same test
- [x] The committed sample still passes `hledger -f sample-vault/hisab.md check --strict`; `python3 tests/make_sample.py` runs to completion (it was crashing on the new question until it got the `skip` answer). The sample was left as committed, never regenerated over its phone-posted #35 and #36
- [x] Repo check — `python3 tests/smoke.py` → `ALL OK` (Python 3.11)
- [?] The model follows the ladder on the real receipts — needs a key, post-merge, owner + lead: `python3 tests/check_receipts.py` (r1 out, r2 out with a receivable candidate if it asks, r3 out with no income and no name match on "Waleed Hamza Flutter", r4 in, r1 with holder "Ayesha Khan" asks about direction and posts nothing). Paste the output in the PR
- [?] Phone, post-merge, owner + lead, on the demo agent: `/setup`, answer `personal`, expect `2/8 · …full name on your accounts…`, answer a name with digits and expect `2/8 · Just the name, no numbers…`; then send r1, r3 and r4 as photos and expect out, out and in; send r1 to a ledger whose holder is someone else and expect one direction question
- [?] Self-transfer: with the holder on both sides of a receipt and both institutions declared, expect the three-posting `equity:transfer` entry and both accounts named in the reply; with an undeclared institution, expect the one question "your own account, or another person?" (no fixture exists for this yet)

## Conventions
- Six tools unchanged; `hisab/tools.py` untouched (the script wraps `Tools.call` itself). Ledger writes, entry numbers, undo, transport, chunking: unchanged.
- New strings `holder` and `holder_again` exist in `en` and `ur` (Urdu script); the reply stays one line and the `MODEL_LANG` shapes are unchanged (pinned by smoke).
- No new failure code, so `errors.py` is untouched. The holder name lives in the user's own `settings.json`, nothing new leaves the machine.
- `config.example.yaml` needs no key.

## Findings
FINDING-01 · Important (fixed in this review) · tests/smoke.py — the test names were `Hamza Shakeel` and `حمزہ شکیل`, invented from the owner's email address: a real person's name in a public repo. Replaced with `Ayesha Khan` / `عائشہ خان`.
FINDING-02 · Important (owner decision before push) · tests/fixtures/receipts/r1–r4.jpg, tests/fixtures/receipts/README.md, tests/check_receipts.py — the four screenshots and the default holder carry the owner's real name (`MUHAMMAD HAMZA`), and the receipts name three private third parties (`Mian Inam Ullah`, `Waleed Hamza Flutter`, `ALI SHAKEEL`), one with the last digits of a phone number (r2) and masked IBAN/account tails (r1, r4). AGENTS.md's privacy rule and the plan's "blurred except the holder name and the amount" both point the other way. The images were placed by the owner and the lead approved the mapping; the owner should confirm, or blur the third parties, before this is pushed.
FINDING-03 · Minor · the owner's own copies of r1–r4 are still untracked in the main checkout's `tests/fixtures/receipts/`; a merge of this branch there will refuse to overwrite them. Delete them after merge (they are byte-identical to the committed ones).
FINDING-04 · Minor · with no holder, receipts that name both parties (r1, r2, r4) fall through to the direction question by design; only a lone recipient (r3) posts. That is the agreed behaviour for a skipped name and the reason the no-holder case is in the checklist above rather than a fixture.
