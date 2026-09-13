---
slug: GH-22-landing-two-languages
issue: 22
status: completed
open_questions: none
---

# feat: Landing and portal in English and Urdu only; Roman Urdu stays in the agent          ✅ COMPLETED — 2026-09-14

## Problem
[#22](https://github.com/mhmzdev/hisab-whatsapp/issues/22). The landing page and portal ship every string in `en`, `ur` and `roman`. The Roman Urdu marketing copy was never reviewed, reads as transliterated marketing English rather than the agent's register, and every new portal string costs a third translation. Roman Urdu is how people *text* the ledger, not how they read a landing page. The agent (`hisab/i18n.py`, `MODEL_LANG`) keeps all three languages.

## Approach
Two languages is a `landing/`-only contract; nothing under `hisab/` or `runner/` changes.

- **Switcher** — drop the `roman` option from `OPTIONS` in `landing/app/LanguageSwitcher.jsx:5-9`.
- **Provider** — `landing/app/LanguageProvider.jsx:16` accepts only `en` and `ur` from `localStorage`; any other saved value (including a legacy `roman`) is ignored, so state stays at its initial `'en'`. The stored value is not rewritten; the next click on the switcher overwrites it.
- **Strings** — remove every `roman` value from `landing/content/strings.json` (104 keys) with a one-off `json.load` → delete → `json.dumps(ensure_ascii=False, indent=2) + "\n"` pass; the file round-trips byte-for-byte through that serializer today, so the diff is pure deletions. `portal_lang_roman` **stays as a key** (en "Roman Urdu" / ur) — the Connected screen's Language row renders the *agent's* language (`landing/app/portal/page.jsx:326`, `portal_lang_${tenant.language}`), which can still be `roman`.
- **Check** — `tests/check_landing.py:7` `LANGS = ("en", "ur")`, and a new rule: any language key outside `LANGS` on a string fails (`strings.json[<key>]: unexpected language 'roman'`). That is what makes "exactly `en` and `ur`" enforceable rather than merely "at least".
- **Regression test** — `tests/smoke.py` (landing block, `:655-662`) runs `check_landing.run` against a temp root holding a minimal `strings.json` plus a `firebase.json`, once with a `roman` value (must fail with "unexpected language") and once with `ur` missing (must fail with "missing or empty").
- **Comment** — `landing/app/portal/page.jsx:298` no longer mentions the page being in Roman Urdu.
- **Docs** — `landing/README.md:31` states the two-language contract (and that the agent keeps three); `landing/README.md:14` and `Makefile:59` say "two-language"; `AGENTS.md:54` and `runner/README.md:19` say the portal renders `lastError` codes in two languages; `ARCHITECTURE.md:81` invariant 5 is scoped to the agent's `hisab/i18n.py` with the portal's `en`/`ur` noted.

Invariants kept: six tools, strict check, entry numbers, offset-after-batch untouched; three languages in `hisab/i18n.py` untouched; no privacy surface.

## Success criteria
- [ ] The switcher offers English and اردو only; a saved `roman` preference falls back to English — `verify: manual 1. make landing && make emulators 2. open http://localhost:3031/ — the switcher shows two buttons, English and اردو 3. DevTools console: localStorage.setItem('hisab-lang','roman'); reload 4. page renders in English with English pressed`
- [ ] `LanguageSwitcher.jsx` and `LanguageProvider.jsx` carry no `roman` — `verify: ! grep -n roman landing/app/LanguageSwitcher.jsx landing/app/LanguageProvider.jsx`
- [ ] `landing/content/strings.json` has no `roman` values — `verify: python3 -c "import json,sys; d=json.load(open('landing/content/strings.json')); sys.exit(any(set(v)!={'en','ur'} for v in d.values()))"`
- [ ] `tests/check_landing.py` requires exactly `en` and `ur` (missing `ur` fails, extra `roman` fails) — `verify: python3 tests/check_landing.py` plus the new smoke assertions
- [ ] `hisab/i18n.py` still has `en`, `ur`, `roman` for every key; `/lang` and setup unchanged — `verify: git diff --quiet main -- hisab/ && python3 tests/smoke.py`
- [ ] `landing/README.md` states the two-language contract — `verify: grep -n "{en, ur}" landing/README.md`
- [ ] The static export still builds — `verify: make landing`
- [ ] Repo check passes — `verify: python3 tests/smoke.py`

## Phases
### Phase 1 — Portal code, strings and the check
**Status:** Done — switcher and provider are en/ur only, 104 `roman` values dropped, `check_landing.py` rejects any other language key, smoke asserts both failure modes (mutation-checked)
- Files: `landing/app/LanguageSwitcher.jsx:5-9`, `landing/app/LanguageProvider.jsx:16`, `landing/app/portal/page.jsx:298`, `landing/content/strings.json`, `tests/check_landing.py:1,7,36-44`, `tests/smoke.py:655-662`
- Change: as in Approach. The "unexpected language" loop sits beside the "missing or empty" loop in `check_landing.run`; the module docstring says "two-language completeness".
- Test: smoke builds a temp root (`strings.json` with `brand` en "Hosted Hisab" and one `*verify_instruction*` key, plus `firebase.json` with `hosting.public: landing/out` and `emulators.hosting.port`), asserts a `roman` extra yields an "unexpected language" failure and a missing `ur` yields "missing or empty", then runs the real check as today.

### Phase 2 — Docs
**Status:** Done — `landing/README.md` states the `{en, ur}` contract, `Makefile`, `AGENTS.md`, `runner/README.md` and `ARCHITECTURE.md` scope three languages to the agent; `make landing` builds
- Files: `landing/README.md:14,31`, `Makefile:59`, `AGENTS.md:54`, `runner/README.md:19`, `ARCHITECTURE.md:81`
- Change: wording only, as in Approach.
- Test: `python3 tests/smoke.py`; `make landing`.

## Risks
- A browser with `hisab-lang=roman` saved keeps that value in storage until the user clicks the switcher; harmless, since the provider ignores it.
- `node_modules`/network needed for `make landing`; if unavailable the build criterion is recorded as not run rather than ticked.

## Out of scope
- `hisab/i18n.py`, `MODEL_LANG`, setup and `/lang` — the agent keeps three languages.
- Rewriting or reviewing the Urdu copy.
- Historical docs (`docs/brainstorm/`, `docs/specs/`, completed plans) — they record what was decided then.
