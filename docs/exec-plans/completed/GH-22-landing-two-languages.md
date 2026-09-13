---
slug: GH-22-landing-two-languages
issue: 22
status: completed
open_questions: none
---

# feat: English and Urdu are the only languages Hisab is written in; Roman Urdu stays something users can chat in          ✅ COMPLETED — 2026-09-14

## Problem
[#22](https://github.com/mhmzdev/hisab-whatsapp/issues/22). The landing page and portal ship every string in `en`, `ur` and `roman`. The Roman Urdu marketing copy was never reviewed, reads as transliterated marketing English rather than the agent's register, and every new portal string costs a third translation. Roman Urdu is how people *text* the ledger, not how they read a landing page.

**Scope extension (owner decision 2026-09-14, folded into the same issue and PR #32):** the agent's fixed strings drop Roman Urdu too. English and Urdu are the only languages Hisab is *written* in; a user can still *chat* in Roman Urdu and the model answers in kind. Setup loses its language question: the greeting asks personal-or-shop in English and Urdu, the answer sets the language, and a one-time italic note names `/lang` to switch.

## Approach
Phases 1–2 are the `landing/` contract. Phase 3 carries the same rule into the agent (see its section).

- **Switcher** — drop the `roman` option from `OPTIONS` in `landing/app/LanguageSwitcher.jsx:5-9`.
- **Provider** — `landing/app/LanguageProvider.jsx:16` accepts only `en` and `ur` from `localStorage`; any other saved value (including a legacy `roman`) is ignored, so state stays at its initial `'en'`. The stored value is not rewritten; the next click on the switcher overwrites it.
- **Strings** — remove every `roman` value from `landing/content/strings.json` (104 keys) with a one-off `json.load` → delete → `json.dumps(ensure_ascii=False, indent=2) + "\n"` pass; the file round-trips byte-for-byte through that serializer today, so the diff is pure deletions. `portal_lang_roman` **stays as a key** (en "Roman Urdu" / ur) — the Connected screen's Language row renders the *agent's* language (`landing/app/portal/page.jsx:326`, `portal_lang_${tenant.language}`), which can still be `roman`.
- **Check** — `tests/check_landing.py:7` `LANGS = ("en", "ur")`, and a new rule: any language key outside `LANGS` on a string fails (`strings.json[<key>]: unexpected language 'roman'`). That is what makes "exactly `en` and `ur`" enforceable rather than merely "at least".
- **Regression test** — `tests/smoke.py` (landing block, `:655-662`) runs `check_landing.run` against a temp root holding a minimal `strings.json` plus a `firebase.json`, once with a `roman` value (must fail with "unexpected language") and once with `ur` missing (must fail with "missing or empty").
- **Comment** — `landing/app/portal/page.jsx:298` no longer mentions the page being in Roman Urdu.
- **Docs** — `landing/README.md:31` states the two-language contract (and that the agent keeps three); `landing/README.md:14` and `Makefile:59` say "two-language"; `AGENTS.md:54` and `runner/README.md:19` say the portal renders `lastError` codes in two languages; `ARCHITECTURE.md:81` invariant 5 is scoped to the agent's `hisab/i18n.py` with the portal's `en`/`ur` noted.

Invariants kept: six tools, strict check, entry numbers, offset-after-batch untouched; no privacy surface. The language invariant changes by decision: fixed strings in `en` and `ur`; the model mirrors Roman Urdu.

## Success criteria
- [ ] The switcher offers English and اردو only; a saved `roman` preference falls back to English — `verify: manual 1. make landing && make emulators 2. open http://localhost:3031/ — the switcher shows two buttons, English and اردو 3. DevTools console: localStorage.setItem('hisab-lang','roman'); reload 4. page renders in English with English pressed`
- [ ] `LanguageSwitcher.jsx` and `LanguageProvider.jsx` carry no `roman` — `verify: ! grep -n roman landing/app/LanguageSwitcher.jsx landing/app/LanguageProvider.jsx`
- [ ] `landing/content/strings.json` has no `roman` values — `verify: python3 -c "import json,sys; d=json.load(open('landing/content/strings.json')); sys.exit(any(set(v)!={'en','ur'} for v in d.values()))"`
- [ ] `tests/check_landing.py` requires exactly `en` and `ur` (missing `ur` fails, extra `roman` fails) — `verify: python3 tests/check_landing.py` plus the new smoke assertions
- [ ] Every `S`/`Q` string in `hisab/i18n.py` is exactly `{en, ur}`, `MODEL_LANG` is `{en, ur}` and its `en` line tells the model to answer Roman Urdu in Roman Urdu — `verify: python3 tests/smoke.py` (i18n assertions)
- [ ] Setup has no language step: the greeting asks personal/shop in English and Urdu; an Urdu answer runs setup in Urdu, a Latin answer in English, and the next question carries the `/lang` note exactly once — `verify: python3 tests/smoke.py` (setup assertions)
- [ ] `/lang اردو` mid-setup switches the next question to Urdu and suppresses the note; `/lang roman` asks again with the two options — `verify: python3 tests/smoke.py`
- [ ] A stored `language: roman` reads as `en` in `Ledger.language()` and in the runner's activity snapshot; the portal drops `portal_lang_roman` — `verify: python3 tests/smoke.py`
- [ ] No Roman Urdu fixed string or language code left: no `"roman":` key anywhere live, and every remaining "Roman Urdu" mention is about what users write — `verify: ! grep -rn '"roman":' hisab runner landing/app landing/content` plus a read of `grep -rni "roman" README.md AGENTS.md ARCHITECTURE.md .agents/skills hisab runner landing/app`
- [ ] Terminal: a fresh ledger answered in Urdu runs setup in Urdu — `verify: manual 1. a config pointing at a scratch vault, python3 -m hisab.loop --stdin 2. type 500 chai — expect the bilingual greeting 3. type دکان — expect the currency question in Urdu plus the italic /lang english note`
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

### Phase 3 — The agent: fixed strings in en/ur, language from the first answer
**Status:** Done — `i18n.py` en/ur only with `detect_lang`/`norm_lang`, setup starts at personal/shop and locks the language on the accepted answer with a one-time `/lang` note, `/lang` works mid-setup, stored `roman` reads as `en` (worker and runner), `portal_lang_roman` gone, docs and skills updated; smoke covers each path (mutation-checked on `detect_lang`)
- Files: `hisab/i18n.py` (all), `hisab/setup.py:10-11,33-78`, `hisab/loop.py:18,39,52-57,63-67`, `hisab/ledger.py:54-55`, `runner/activity.py:78`, `runner/errors.py:3`, `landing/app/portal/page.jsx:326`, `landing/content/strings.json` (`portal_lang_roman`), `tests/smoke.py:26-37,159-166,338-357,500-510`, `README.md:47,61`, `AGENTS.md` (Language non-negotiable), `ARCHITECTURE.md:81`, `landing/README.md:31`, `.agents/skills/{create-plan,implement,grill-me,to-spec}/SKILL.md` (the "three languages" lines)
- Change:
  - `i18n.py`: `LANGS = ("en", "ur")`; delete every `roman` value. `greeting` (en only, as today) becomes the welcome line plus the mode question in English and in Urdu. New `lang_note`: en `_Replying in English. Send /lang اردو to switch._`, ur `_جواب اردو میں۔ انگلش کے لیے /lang english بھیجیں۔_`. `lang_set` en/ur. `lang_ask` becomes `Send */lang English* or */lang اردو*.` (and Urdu). `pending_reminder` and `welcome` lose their Roman Urdu line and footer word. `MODEL_LANG` keeps `en` + `ur`; `en` adds: if the user writes Roman Urdu, reply in Roman Urdu with the shapes «post ho gaya #12 — chai 300 — mahine ka kharch 48,200» / «hata diya #12 — chai». `parse_lang` loses the `roman` branch and returns `None` for any text containing `roman` (so "roman urdu" is not read as Urdu). New `detect_lang(text)`: any Arabic-script letter (`[\u0600-\u06FF]`) → `ur`, else `en`. New `norm_lang(code)`: `code` if in `LANGS` else `en`.
  - `setup.py`: `PERSONAL`/`SHOP` start at `mode`. On a `mode` answer with no `answers.language` yet, `detect_lang(t)` picks the language for this attempt; `mode_again` replies in it. When the mode is accepted and the language was detected (not set by `/lang`), the next question is followed by `\n` + `lang_note` once. `lang()` normalizes. New `set_lang(lg)` writes `answers.language` into the active state. The first setup answer decides the language, not a parked message: a parked entry like `2500 coffee` is digits and a Latin word even from an Urdu user.
  - `loop.py`: `/lang` with a parsed language → `setup.set_lang` if setup is active, else `ledger.set_settings` if a ledger exists; replies `lang_set` in the new language; otherwise `lang_ask`. `no_ledger` / `no_ledger_parked` go out as the English line then the Urdu line, since no language is known yet.
  - `ledger.py`: `language()` returns `norm_lang(...)`. `runner/activity.py`: a stored language outside `en`/`ur` reports `en`. Portal: remove `portal_lang_roman`; the Language row renders `portal_lang_ur` for `ur`, else `portal_lang_en`.
  - Docs and skills: wording only — fixed strings in `en`/`ur`, the model mirrors Roman Urdu, `/lang` switches.
- Test: the setup loop drops its `"English"` first answer and asserts `led.language() == "en"` and the `/lang اردو` note appears once; the Urdu flow answers `ذاتی` first and expects `کرنسی` plus `/lang english`, no note on the next reply, `language() == "ur"`; `Hisab.handle("/lang اردو")` mid-setup switches the next question to Urdu; `parse_lang("roman urdu") is None`; `set_settings({"language": "roman"})` → `language() == "en"`; every `S`/`Q` dict's keys ⊆ `{en, ur}` and `MODEL_LANG` keys == `{en, ur}`; reminder has no `Roman`; welcome test answers `دکان` and expects `کرنسی`; activity snapshot maps `roman` → `en`.

## Risks
- A browser with `hisab-lang=roman` saved keeps that value in storage until the user clicks the switcher; harmless, since the provider ignores it.
- `node_modules`/network needed for `make landing`; if unavailable the build criterion is recorded as not run rather than ticked.

- Existing ledgers stored as `roman` switch their fixed strings to English; the model still answers them in Roman Urdu when they write it.
- An Urdu speaker who answers the greeting in Latin (`shop`) gets English setup; the note tells them `/lang اردو`.

## Out of scope
- Detecting language on every message after setup — the setting is sticky; `/lang` changes it.
- Transcription config comments about Roman Urdu input (`config.example.yaml`, `examples/`) — input, not our copy.
- Rewriting or reviewing the Urdu copy.
- Historical docs (`docs/brainstorm/`, `docs/specs/`, completed plans) — they record what was decided then.
