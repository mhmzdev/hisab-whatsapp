---
type: Checklist
title: GH-38-quota-refund-model-failures
description: Acceptance checklist for model-side failures no longer using a tenant's monthly model-call allowance.
tags: [checklist, quota, hosted, errors]
timestamp: 2026-09-14T00:00:00Z
---

# GH-38-quota-refund-model-failures — acceptance checklist   (5 proven · 0 manual · 0 failing)

Plan: [GH-38-quota-refund-model-failures](../exec-plans/completed/GH-38-quota-refund-model-failures.md) · Issue: [#38](https://github.com/mhmzdev/hisab-whatsapp/issues/38) · Owner chose option B on 2026-09-14.

- [x] With a quota set, `model_auth`, `model_unavailable` and `model_rejected` leave the counter unchanged; a bare `KeyError` (`internal`) and a `LedgerError` (`ledger_rejected`) add one; a successful turn adds one — `python3 tests/smoke.py` ("quota: model_* failures refunded…"); mutation: with the refund removed, smoke fails with `('HisabError', 'model_auth', 0, 1)`
- [x] `refund_model_call` stays at 0 and leaves a previous month's `usage.json` count untouched — same test
- [x] The existing quota block (80% warning, hard stop, free commands, persistence) still passes — `python3 tests/smoke.py`
- [x] Live in the runner image (Gemini, `monthly_limit: 1000`): a real turn → `usage.json` `calls: 1`; the same store with a bogus `GEMINI_API_KEY` → `error model_auth`, still `calls: 1`
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`

## Conventions
- No new strings or config; self-host (no quota) never records or refunds. `runner/activity.py` publishes the refunded count unchanged.
- `runner/README.md` states the rule next to the allowance.

## Findings
_None._ An accepted risk from the plan: a `model_*` failure after a tool round already posted an entry is refunded too.
