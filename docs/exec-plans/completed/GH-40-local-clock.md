---
slug: GH-40-local-clock
issue: 40
status: completed
open_questions: none
---

# fix: Every "today" reads the configured timezone, not the container's UTC clock          ✅ COMPLETED — 2026-09-14

## Problem

[#40](https://github.com/mhmzdev/hisab-whatsapp/issues/40): both images run in UTC, and every date decision reads the process clock. A Pakistani user (UTC+5) sending an entry between 00:00 and 04:59 gets yesterday's date, which near a month or quarter boundary lands in the wrong month or quarter file. Read this run:

- **The model's date:** `hisab/agent.py:51` (`Today is` in the prompt)
- **Default entry date:** `hisab/tools.py:64` (`append_entry` with no date)
- **Ledger:** `hisab/ledger.py` — `:62` quarter file, `:97` future-date guard, `:212` `afford`, `:246` `month_summary`
- **Setup:** `hisab/setup.py:136,142` (`~ monthly from`, the first quarter file)
- **Quota month:** `hisab/store.py:71` (`usage` month); its reader, `runner/activity.py:66-67`, must agree with it
- **Exported file times:** `hisab/archive.py`, where `zf.write` stamps each file with UTC-local times (#36 phone run)
- **hledger itself:** `this month` and `last month` in `Ledger.report` (`ledger.py:273-278`) use hledger's own clock

## Approach

**One clock module, `hisab/clock.py`, stdlib only:**

```python
DEFAULT_TZ = "Asia/Karachi"
def _utcnow():                      # the one real clock read; smoke patches this
    return datetime.now(timezone.utc)
def now(tz=DEFAULT_TZ): return _utcnow().astimezone(ZoneInfo(tz or DEFAULT_TZ))
def today(tz=DEFAULT_TZ): return now(tz).date()
```

`hisab/config.py` `DEFAULTS["timezone"]` becomes `clock.DEFAULT_TZ`, so there's one source.

**Threading the timezone through.**
- `Ledger(path, currency="PKR", timezone=clock.DEFAULT_TZ)` stores `self.tz` and gains `today()`. Every `date.today()` in `ledger.py` becomes `self.today()`.
- `Ledger.hledger` prepends `--today=<self.today()>` to every call, so hledger's relative periods agree. Verified this run: `--today` exists in 1.52.3 (Mac) and 1.32.3 (runner image).
- `Tools.t_append_entry`, `Agent.system`, `Setup` (twice) use `self.ledger.today()`.
- `Store(path, keep_days=30, timezone=clock.DEFAULT_TZ)`, and `usage()` uses `clock.today(self.tz).strftime("%Y-%m")`.
- `hisab/loop.py` passes `cfg["timezone"]` to both constructors, and `_export_ledger` uses `clock.now(self.cfg["timezone"])`, removing its own `datetime.now(ZoneInfo(...))`.
- `build_export_zip` writes each file through a `ZipInfo` whose `date_time` is the file's mtime converted into `ledger.tz`.
- `runner/activity.py` `snapshot` defaults `today` to `clock.today(runner_cfg.get("timezone"))`. The runner never sets a tenant timezone (`runner/tenant_config.py`), so tenant and runner both land on `DEFAULT_TZ`.

**Guard.** Smoke greps `hisab/*.py` and `runner/*.py` (excluding `clock.py`) for `date.today(`, `datetime.now(`, `time.strftime("%Y` and `time.localtime(`. A new bare clock read fails the check. Log-line timestamps (`time.strftime('%H:%M:%S')` in the loop) are operator logs, not ledger dates, and stay untouched; the guard pattern skips them.

`tests/make_sample.py` keeps passing explicit dates. It is unchanged.

## Success criteria

- [x] With `clock._utcnow` fixed at `2026-09-30T20:30Z` (01:30 PKT on 1 Oct): `Agent.system()` contains `Today is 2026-10-01`; a dateless `append_entry` writes `2026-10-01` into `2026-Q4.md`; `month_summary()` reports `2026-10`; an entry dated `2026-10-01` passes the future-date guard; `store.usage()["month"] == "2026-10"`; `snapshot()` reads `usedThisMonth` for `2026-10` — `verify: python3 tests/smoke.py`
- [x] `Ledger.hledger` passes `--today=2026-10-01` at that clock, so `report("register")` over "this month" returns the 1 Oct entry and not September's — `verify: python3 tests/smoke.py`
- [x] Files inside an export ZIP carry mtimes in the ledger's timezone (a file touched at `2026-09-14T05:59Z` reads `(2026, 9, 14, 10, 59, …)`) — `verify: python3 tests/smoke.py`
- [x] No bare clock read is left in `hisab/` or `runner/` outside `hisab/clock.py` — `verify: python3 tests/smoke.py` (grep guard)
- [x] Terminal, real model: `500 chai` on a scratch copy of the sample at a real time posts with local today's date — `verify: manual 1. docker exec the runner: python -m hisab.loop --stdin --config /tmp/hosted.yaml 2. type 500 chai 3. grep the new entry's date in /tmp/sv/2026-Q3.md equals TZ=Asia/Karachi date +%F`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Clock module and every call site
**Status:** Done — `hisab/clock.py`; Ledger/Store take the timezone, `Ledger.hledger` passes `--today`; tools/agent/setup/loop/archive/activity read the clock; smoke "clock:" block + a grep guard; the #36 caption test moved to `clock._utcnow`
- Files: new `hisab/clock.py`; `hisab/config.py:6-20`; `hisab/ledger.py:21-26,32-37,62,97,212,246`; `hisab/tools.py:64`; `hisab/agent.py:51`; `hisab/setup.py:136,142`; `hisab/store.py:11-15,67-72`; `hisab/loop.py:36-37,120-130`; `hisab/archive.py:31-33`; `runner/activity.py:64-67`; `tests/smoke.py`
- Change: as in Approach.
- Test: one smoke block, "clock:". It patches `hisab.clock._utcnow`, runs every assertion in the first three criteria on a scratch copy of `sample-vault`, then runs the grep guard.

### Phase 2 — Live check in the runner image
**Status:** Done — rebuilt runner (hledger 1.32.3): at a fixed 20:30Z a dateless entry went to `2026-10-01` in `2026-Q4.md` and "this month" registered October; a real Gemini `500 chai` posted `2026-09-14` (the PKT date) in `2026-Q3.md`
- `make runner-down && make runner-up`, then the manual criterion.

## Risks

- `--today` on every hledger call: `check --strict` ignores relative dates, so it is unaffected. An older hledger without `--today` would fail loudly on the first call, and both known installs have it.
- Two timezone defaults could drift. The runner imports `clock.DEFAULT_TZ` instead of repeating the string.

## Out of scope

- Operator log timestamps (`[HH:MM:SS]` lines) stay container time.
- Per-tenant timezones chosen in setup or the portal (Pakistan-only scope).
