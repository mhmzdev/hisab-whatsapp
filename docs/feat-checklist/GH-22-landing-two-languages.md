---
type: Checklist
title: GH-22-landing-two-languages
description: Acceptance checklist for writing Hisab in English and Urdu only — landing, portal and the agent's fixed strings — while users can still chat in Roman Urdu.
tags: [checklist, portal, landing, language, setup]
timestamp: 2026-09-14T00:00:00Z
---

# GH-22-landing-two-languages — acceptance checklist   (15 proven · 3 manual · 0 failing)

Plan: [GH-22-landing-two-languages](../exec-plans/completed/GH-22-landing-two-languages.md) · Issue: [#22](https://github.com/mhmzdev/hisab-whatsapp/issues/22) · Scope extended 2026-09-14 by the owner to the agent's fixed strings and setup.

## Landing and portal (Phases 1–2)
- [x] The switcher offers English and اردو only — `make landing`, served `landing/out` locally, Playwright read the `aria-pressed` buttons: `["English:true", "اردو:false"]`
- [x] A saved `roman` preference falls back to English — same page, `localStorage.setItem('hisab-lang','roman')` + reload: English pressed, `dir="ltr"`, h1 "A ledger you text"
- [x] Urdu still works — clicking اردو saved `ur`, set `dir="rtl"`, h1 "ایک کھاتہ جسے آپ لکھتے ہیں"
- [x] `landing/content/strings.json` is exactly `{en, ur}` per key, `portal_lang_roman` removed — the plan's `json.load` one-liner exits 0; `grep '"roman":'` over `hisab runner landing/app landing/content` finds nothing
- [x] `tests/check_landing.py` requires exactly `en` and `ur` — smoke asserts an extra `roman` fails ("unexpected language 'roman'") and a missing `ur` fails; mutation: disabling the rule makes smoke fail
- [x] The static export builds after both commits — `make landing` → "prerendered as static content"

## Agent (Phase 3)
- [x] Every `S`/`Q` string is ⊆ `{en, ur}`, `LANGS == ("en", "ur")`, `MODEL_LANG` is `{en, ur}` and its `en` line names Roman Urdu — `python3 tests/smoke.py` ("i18n: en/ur only; stored roman reads as en")
- [x] No language question: the greeting asks personal/shop in English and Urdu — smoke setup loop (`"personal" in q and "ذاتی" in q`)
- [x] A Latin first answer runs setup in English with the `/lang اردو` note exactly once; `language() == "en"` — smoke `[personal]`/`[shop] setup ok`
- [x] An Urdu first answer runs setup in Urdu with the `/lang english` note once; `PKR`/`cash` later do not flip it; `language() == "ur"` — smoke "urdu setup ok"; mutation: `detect_lang` always `en` makes smoke fail
- [x] An unrecognised first answer asks again in its own language without locking it; a setup saved mid-flow with the old language step resumes at the mode question — smoke "urdu setup ok"
- [x] `/lang اردو` mid-setup switches the next question to Urdu with no note, `/lang english` switches back, `/lang roman urdu` asks again with the two options — smoke "lang: /lang mid-setup ok"
- [x] A stored `language: roman` reads as `en` in `Ledger.language()` and in the runner's activity snapshot — smoke (i18n line and activity block)
- [x] Hosted pending reminder and welcome are English + Urdu with no Roman Urdu line; the welcome ends with the bilingual greeting and an Urdu answer continues in Urdu — smoke "runner: pending mute…" and the welcome block
- [x] Terminal path: fresh ledger, `500 chai` → bilingual no-ledger lines + greeting; `دکان` → `کرنسی؟` + `_جواب اردو میں۔ انگلش کے لیے /lang english بھیجیں۔_`; remaining questions in Urdu; `settings.json` `language: ur`; the parked `500 chai` then goes to the model — driven through `Hisab.run_stdin` with a scratch config and a stub model (no key read)

Repo check: `python3 tests/smoke.py` — ALL OK.

## Needs a human
- [?] The model answers Roman Urdu in Roman Urdu on an `en` ledger — terminal: `bash tests/demo_terminal.sh` (sample ledger is `en`), type `Metro ko 20000 diye`, expect a one-line Roman Urdu shape like `post ho gaya #N — Metro 20,000 — …`; then `2500 cash sale today`, expect the English shape. Only the prompt line changed; no model ran in this review
- [?] Phone, self-host on a scratch vault (`HISAB_VAULT=./scratch-empty docker compose up -d --build`): send `hello` → bilingual greeting; reply `ذاتی` → Urdu currency question with the italic note rendering as italics in WhatsApp
- [?] Portal Connected screen for a tenant whose `settings.json` says `ur` reads "اردو"/"Urdu", and one still stored as `roman` reads "English" after the runner's next activity sync — `make up`, connected demo tenant

## Conventions
- Surface, writes, transport: untouched — six tools, `Ledger.append`, offset and dedup unchanged; `handle()` still intercepts `/lang` before setup and the model.
- Language: this diff *changes* the rule by owner decision — fixed strings `en`/`ur`, Roman Urdu model-only; `AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `landing/README.md` and the lifecycle skills now say so. Input-side mentions of Roman Urdu (agent prompt parsing, transcription, rule templates) intentionally stay.
- Privacy: no local path, token or personal data in the diff (grep over added lines).
- Tests: every new path has a smoke assertion; two mutation checks bite.

## Findings
FINDING-01 · Minor · landing/app/LanguageProvider.jsx:16 — a legacy `hisab-lang=roman` stays in `localStorage` until the user clicks the switcher. Harmless (ignored on read). Not fixed, by plan.
FINDING-02 · Minor · hisab/setup.py:58 — deviation from the rule agreed in chat: a message parked before setup (`2500 coffee`) does **not** decide the language; the answer to the greeting does. Reason: a parked entry is digits plus a Latin word even from an Urdu speaker, so it would put most Urdu users into English setup. Owner to confirm.
FINDING-03 · Minor · hisab/loop.py:57 — pre-existing: on self-host, a very first message of `/lang اردو` (no ledger, no setup yet) gets `lang_ask` and does not start setup. Not introduced here; hosted mode always has setup active after the welcome.
FINDING-04 · Minor · hisab/loop.py (welcome) — the hosted welcome still stacks two headers ("Connected ✓ · جڑ گیا ✓" then "Welcome to Hisab · حساب میں خوش آمدید") before the question, as it did before this change. Cosmetic, out of scope.
