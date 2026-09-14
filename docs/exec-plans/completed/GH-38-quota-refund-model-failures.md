---
slug: GH-38-quota-refund-model-failures
issue: 38
status: completed
open_questions: none
---

# fix: A model-side failure refunds the monthly allowance          ✅ COMPLETED — 2026-09-14

## Problem

[#38](https://github.com/mhmzdev/hisab-whatsapp/issues/38): `Hisab._agent` records the model call before dispatch (`hisab/loop.py:112`, `store.record_model_call()`) and never takes it back when `agent.run` raises. On the #27 live test, one normal entry plus one `model_auth` failure left `usedThisMonth=2`. So our outages (a revoked operator key, a provider down, a bad model id) use up the user's paid allowance. The owner chose **option B** on 2026-09-14; the decision is in the issue comment.

## Approach

- `Store.refund_model_call()` (`hisab/store.py`, next to `record_model_call`) decrements this month's `calls`, never below 0, and does nothing when the stored month isn't the current month. A turn that started before midnight on the 1st must not refund the new month. It returns the new count.
- In `Hisab._agent`'s `except` (`hisab/loop.py:121-125`): when `used is not None` (a quota is configured) and `code.startswith("model_")`, call `self.store.refund_model_call()` before replying. `internal` and `ledger_rejected` still count.
- Docstrings: `record_model_call` states the rule ("counted at dispatch; refunded by `refund_model_call` when the turn fails with a `model_*` code — nothing was served"). `runner/README.md:34` gets one clause: model-side failures don't count.

Invariants: the 80% warning and the hard stop read the same counter; `runner/activity.py` publishes `usedThisMonth` from the same `usage.json`, so the portal shows the refunded number. Self-host (no quota) never records or refunds.

## Success criteria

- [x] With `monthly_limit` set, a turn raising `HisabError` `model_auth`, `model_unavailable` or `model_rejected` leaves `store.usage()["calls"]` unchanged; `internal` (a bare `KeyError`) and `ledger_rejected` still add one; a successful turn adds exactly one — `verify: python3 tests/smoke.py`
- [x] `refund_model_call` never goes below 0 and doesn't touch a counter from a previous month — `verify: python3 tests/smoke.py`
- [x] The existing quota block (warn at 80%, hard stop, free commands exempt, persists across restart) still passes — `verify: python3 tests/smoke.py`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Refund and tests
**Status:** Done — `Store.refund_model_call`; `_agent` refunds on `model_*` when a quota is set; smoke "quota: model_* failures refunded…" (mutation: without the refund it fails on `model_auth`); live in the runner image: a real Gemini turn → `calls: 1`, then a bogus-key `model_auth` turn → still `calls: 1`
- Files: `hisab/store.py:77-83`; `hisab/loop.py:121-125`; `runner/README.md:34`; `tests/smoke.py` (after the quota block)
- Change: as in Approach.
- Test: a fresh `make_app` with `quota.monthly_limit = 10`, cycling `RaisingAgent` over each code, with stderr redirected, asserting the count after each; then `FakeAgent` +1. The store unit test uses `usage.json` with `{"month": <last month>, "calls": 3}`, so a refund leaves the file's previous-month count untouched and the current month reads 0; and a refund at 0 stays 0.

## Risks

- A `model_*` failure after a tool round already posted an entry refunds a turn that did some work. Accepted: the user got an error reply and no confirmation, and the operator-side failure is ours.

## Out of scope

- Per-token accounting; changing what the portal shows beyond the corrected number.
