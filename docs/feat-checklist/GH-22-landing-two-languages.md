---
type: Checklist
title: GH-22-landing-two-languages
description: Acceptance checklist for dropping Roman Urdu from the landing page and portal while the agent keeps three languages.
tags: [checklist, portal, landing, language]
timestamp: 2026-09-14T00:00:00Z
---

# GH-22-landing-two-languages — acceptance checklist   (8 proven · 1 manual · 0 failing)

Plan: [GH-22-landing-two-languages](../exec-plans/completed/GH-22-landing-two-languages.md) · Issue: [#22](https://github.com/mhmzdev/hisab-whatsapp/issues/22)

- [x] The switcher offers English and اردو only — `make landing`, served `landing/out` locally, Playwright read the `aria-pressed` buttons: `["English:true", "اردو:false"]`
- [x] A saved `roman` preference falls back to English — same page, `localStorage.setItem('hisab-lang','roman')` + reload: English pressed, `dir="ltr"`, h1 "A ledger you text"; the stored value stays `roman` until the next click (by design)
- [x] Urdu still works after the change — clicking اردو saved `ur`, set `dir="rtl"`, h1 "ایک کھاتہ جسے آپ لکھتے ہیں"
- [x] `LanguageSwitcher.jsx` and `LanguageProvider.jsx` carry no `roman` value — `! grep -n roman landing/app/LanguageSwitcher.jsx landing/app/LanguageProvider.jsx` exits 0
- [x] `landing/content/strings.json` has no `roman` values; every key is exactly `{en, ur}` — the plan's `json.load` one-liner exits 0 (104 keys)
- [x] `tests/check_landing.py` requires exactly `en` and `ur` — `python3 tests/check_landing.py` exits 0; `tests/smoke.py` asserts an extra `roman` yields "unexpected language 'roman'" and a missing `ur` yields "missing or empty"; mutation check: disabling the new rule makes smoke fail with `AssertionError`
- [x] `hisab/i18n.py` keeps `en`, `ur`, `roman`; `/lang` and setup unchanged — `git diff --quiet main -- hisab/` exits 0 and `python3 tests/smoke.py` prints ALL OK
- [x] `landing/README.md` states the two-language contract — `grep -n "{en, ur}" landing/README.md` matches line 31; `AGENTS.md`, `runner/README.md`, `ARCHITECTURE.md` and `Makefile` no longer say the portal is three-language
- [?] Connected screen still names an agent set to Roman Urdu — needs a live tenant: `make up`, sign in at http://localhost:3031/portal/, connect the demo agent, answer setup with *Roman Urdu*; expect the Language row to read "Roman Urdu" (English page) and "رومن اردو" (Urdu page). The key `portal_lang_roman` exists with both values (checked), but the render was not run

Repo check: `python3 tests/smoke.py` — ALL OK. Build: `make landing` — static export OK.

## Conventions
- Surface, writes, transport: untouched (no file under `hisab/` changed).
- Language: no new user-facing string; `hisab/i18n.py` still three-language; the landing contract is now two-language by decision in #22.
- Privacy: nothing personal, no token or local path in the diff.
- Tests: the new rule in `check_landing.py` is exercised in `tests/smoke.py` both ways.
- Docs: every place that described the portal as three-language updated; historical brainstorm/spec/completed plans left as records.

## Findings
FINDING-01 · Minor · landing/app/LanguageProvider.jsx:16 — a legacy `hisab-lang=roman` stays in `localStorage` until the user clicks the switcher. Harmless (ignored on read, overwritten on click); noted, not fixed, as the plan chose.
