---
type: Checklist
title: GH-36-export-ledger-delivery
description: Acceptance checklist for export-ledger actually delivering the ledger ZIP, named and captioned in Pakistan time.
tags: [checklist, export, transport, i18n, config]
timestamp: 2026-09-14T00:00:00Z
---

# GH-36-export-ledger-delivery — acceptance checklist   (6 proven · 0 manual · 0 failing)

Plan: [GH-36-export-ledger-delivery](../exec-plans/completed/GH-36-export-ledger-delivery.md) · Issue: [#36](https://github.com/mhmzdev/hisab-whatsapp/issues/36)

- [x] `send_document` declares `application/octet-stream` in the `type` field and on the file part — `python3 tests/smoke.py` ("export: octet-stream upload…")
- [x] A 400/131053 upload refusal raises `export_rejected` and its reply doesn't suggest a retry; a 500 stays `export_failed` — same test
- [x] At a fixed `2026-09-14T06:10Z` the file is `hisab-2026-09-14-1110.zip`, the caption is `Ledger backup · 14 Sep 2026, 11:10` (en) / `کھاتے کا بیک اپ · 14 Sep 2026، 11:10` (ur) — same test
- [x] `timezone` defaults to `Asia/Karachi`, overrides load, `Mars/Olympus` fails at load — same test
- [x] Phone (owner, 2026-09-14, hosted `make up` stack after `make runner-down && make runner-up`): `export-ledger` delivered `hisab-2026-09-14-1119.zip` with caption `Ledger backup · 14 Sep 2026, 11:19`; it unzipped to `2026-Q3.md`, `accounts.md`, `hisab.md`, `rules.md`, `settings.json`; the runner log has no `export_failed`/`export_rejected`
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`

## Conventions
- Six tools unchanged; `export-ledger` stays a runner-level command. ZIP contents unchanged (`hisab/archive.py`).
- New strings (`err_export_rejected[_selfhost]`, the new `export_ready`) are in en and ur; the registry guards pass.
- New config key `timezone` is documented in `config.example.yaml` and validated at load.

## Findings
FINDING-01 · Minor · not in this PR · hisab/archive.py — the files inside the ZIP carry container-clock (UTC) modification times: the phone showed 5:59 AM for files written at 10:59 PKT. Harmless, but it's the same UTC-clock root cause as the entry-date issue; fold it in there.
