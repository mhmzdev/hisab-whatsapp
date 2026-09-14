---
type: Checklist
title: GH-40-local-clock
description: Acceptance checklist for every ledger date, report period, quota month and export time reading the configured timezone instead of the container's UTC clock.
tags: [checklist, clock, ledger, runner, export]
timestamp: 2026-09-14T00:00:00Z
---

# GH-40-local-clock — acceptance checklist   (6 proven · 0 manual · 0 failing)

Plan: [GH-40-local-clock](../exec-plans/completed/GH-40-local-clock.md) · Issue: [#40](https://github.com/mhmzdev/hisab-whatsapp/issues/40)

- [x] At `2026-09-30T20:30Z` (01:30 PKT, 1 Oct): the prompt says `Today is 2026-10-01`, a dateless `append_entry` writes `2026-10-01` into `2026-Q4.md` (so it passes the future guard), `month_summary` is October's, `Store.usage()` month is `2026-10` (and `2026-09` for a UTC store), and `runner.activity.snapshot` reads October's `usedThisMonth` — `python3 tests/smoke.py` ("clock: …")
- [x] hledger's own "this month" follows `--today`: `report("register")` at that clock lists only the 1 Oct entry — same test; also run in the rebuilt runner image on hledger 1.32.3
- [x] Export ZIP entries are stamped in the ledger's timezone: an mtime of `05:59Z` reads `10:59` — same test
- [x] No bare `date.today(`, `datetime.now(`, `time.localtime(` or `time.strftime("%Y` in `hisab/` or `runner/` outside `clock.py` — same test (grep guard)
- [x] Live, runner image with real Gemini: `500 chai` posted `2026-09-14 chai ; n:38` in `2026-Q3.md`, matching `TZ=Asia/Karachi date +%F`; at a fixed 20:30Z a tool append went to `2026-10-01` in `2026-Q4.md`
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`

## Conventions
- Six tools unchanged; strict check and rollback unchanged; entry numbering unchanged.
- No new user-facing strings. The `timezone` config key already existed from #36 and now has one source of truth, `clock.DEFAULT_TZ`.

## Findings
_None._ Operator log timestamps (`[HH:MM:SS]`) stay container time by design (plan: out of scope).
