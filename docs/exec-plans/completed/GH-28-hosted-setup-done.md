---
slug: GH-28-hosted-setup-done
issue: 28
status: completed
open_questions: none
---

# fix: Hosted setup-done message doesn't name the ledger folder (the Firebase uid)          ✅ COMPLETED — 2026-09-14

## Problem

[#28](https://github.com/mhmzdev/hisab-whatsapp/issues/28): the last setup reply is `q("done", lang, dir=self.ledger.dir.name)` (`hisab/setup.py:84`, `hisab/i18n.py:111`). In hosted mode the ledger folder is `vault/<uid>`, so the user reads "Setup done. The ledger is at ZeMXFc4x4g9wGg4n5NMp79aXi7IN/." That's an internal identifier in a chat transcript, and it happened again on the owner's #27 phone run on 2026-09-14. Self-host keeps the folder name, because that's the folder the user opens in Obsidian.

The issue's decisions stand. The issue's "`en`, `ur`, `roman`" is now **`en` and `ur`**, because GH-22 removed `roman`.

## Approach

- `Setup.__init__(self, ledger, store, hosted=False)` stores `self.hosted`. `hisab/loop.py:42` passes `bool(cfg.get("hosted"))`, the same flag `_welcome_if_due` and `errors.reply` read. Other callers (`tests/make_sample.py`, smoke) keep the default and the self-host text.
- `setup.py:84`: `q("done_hosted", lang)` when `self.hosted`, else `q("done", lang, dir=...)`. `done_parked` is appended exactly as now.
- `hisab/i18n.py` `Q["done_hosted"]`:
  - en: "Setup done. Send an entry any time, e.g. *2500 coffee*, a voice note, or a receipt photo. *balance <account> <amount>* sets a starting balance."
  - ur: "سیٹ اپ مکمل۔ کبھی بھی اندراج بھیجیں، مثلاً *2500 chai*، وائس نوٹ، یا رسید کی تصویر۔ *balance <account> <amount>* سے ابتدائی بیلنس سیٹ ہوتا ہے۔"

Invariants: setup questions, order and language detection are unchanged; no ledger write changes.

## Success criteria

- [x] A hosted setup run to completion (en and ur) ends with a reply that contains neither the ledger folder name nor `{dir}`, and still carries `done_parked` when an entry was parked; a self-host run still names the folder — `verify: python3 tests/smoke.py`
- [x] `Q["done_hosted"]` exists in `en` and `ur` and has no `{dir}` placeholder — `verify: python3 tests/smoke.py`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Hosted flag, string, test
**Status:** Done — `Setup(..., hosted)` from `cfg["hosted"]` in the loop; `Q["done_hosted"]` en/ur; smoke "setup: hosted done message…" (en, ur, parked, self-host) + a loop wiring assertion
- Files: `hisab/setup.py:27-29,84`; `hisab/loop.py:42`; `hisab/i18n.py:111-113`; `tests/smoke.py` (after the setup loop, ~line 45)
- Change: as in Approach.
- Test: run the personal answers through `Setup(led, st, hosted=True)` with a uid-like ledger folder name (`tmp / "UidLike28chars..."`), in en, and with an Urdu first answer, and assert the final reply. Assert the self-host run's final reply contains `led.dir.name`. Assert `done_hosted` has both languages and no `{dir}`.

## Risks
- None beyond wording.

## Out of scope
- Any other place a path could leak. A grep of fixed strings shows `done` is the only `{dir}`.
