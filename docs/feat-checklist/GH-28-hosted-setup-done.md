---
type: Checklist
title: GH-28-hosted-setup-done
description: Acceptance checklist for the hosted setup-done message no longer naming the ledger folder (the Firebase uid).
tags: [checklist, setup, i18n, privacy]
timestamp: 2026-09-14T00:00:00Z
---

# GH-28-hosted-setup-done — acceptance checklist   (5 proven · 0 manual · 0 failing)

Plan: [GH-28-hosted-setup-done](../exec-plans/completed/GH-28-hosted-setup-done.md) · Issue: [#28](https://github.com/mhmzdev/hisab-whatsapp/issues/28) · The issue's `roman` string is dropped (GH-22).

- [x] A hosted setup run to completion ends without the ledger folder or `{dir}`, in English and with an Urdu first answer, and keeps `done_parked` for a parked entry; self-host still says `The ledger is at <folder>/` — `python3 tests/smoke.py` ("setup: hosted done message names no folder…")
- [x] `Q["done_hosted"]` has `en` and `ur` and no `{dir}` — same test
- [x] `Hisab` passes `cfg["hosted"]` to `Setup` (false by default, true for a hosted config) — `python3 tests/smoke.py` (wiring assertion in the export block)
- [x] End to end in the runner image (`hisab.loop --stdin`, hosted config, a uid-named empty vault): `hello` → setup → last reply `Setup done. Send an entry any time, e.g. *2500 coffee*, …` with no folder
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`; `hledger -f sample-vault/hisab.md check --strict` passes

## Conventions
- Six tools, ledger writes, transport unchanged. One new fixed string, in en and ur (no Roman Urdu).
- `tests/make_sample.py` still runs, and the setup change doesn't alter its output. Its only diff against the committed sample is two phone-added entries (`n:35`, `n:36`) that were kept deliberately, so the committed sample was restored untouched.

## Findings
_None._
