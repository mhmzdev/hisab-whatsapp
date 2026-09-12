---
type: Checklist
title: GH-3-hosted-landing-portal-shell — acceptance checklist
description: Review of the Hosted Hisab landing page and portal shell against issue #3 and the exec plan.
tags: [checklist, hosted-hisab, landing]
timestamp: 2026-09-12T00:00:00Z
---

# GH-3-hosted-landing-portal-shell — acceptance checklist   (7 proven · 2 manual · 0 failing)

Scope: `landing/` (new, 16 files), `firebase.json`, `tests/check_landing.py`, `tests/smoke.py`, `Makefile`, `.gitignore`, `README.md`, `docs/exec-plans/{INDEX.md,completed/GH-3-hosted-landing-portal-shell.md}` — 26 files touched on branch `GH-3-hosted-landing-portal-shell`, none committed yet. `docs/brainstorm/hosted-portal.md`, `docs/specs/001-hosted-portal.md` and `docs/specs/INDEX.md` are pre-existing working-tree edits this plan depends on but did not touch, and are out of this review's scope.

- [x] A visitor can see the hosted/self-hosted custody distinction, three product examples, the 300 PKR/month presentation plan and a Get-started path — `python3 tests/check_landing.py` passes (brand/pricing/no-payment checks); content present in `landing/app/page.jsx` blocks 1–6, confirmed in-browser this session (Playwright, 1280px and 400px, light and dark, all three languages — Urdu renders RTL, dark mode follows `prefers-color-scheme`).
- [x] The portal shell renders Connect agent, Check your WhatsApp, Connected, and Revoked states without exposing ledger contents or accepting a real payment — `python3 tests/check_landing.py` passes (payment-input/provider scan, verify-direction denylist); all four states screenshotted this session via Playwright at `?state=connect|check|connected|revoked`, confirmed no transaction/balance/account-name value anywhere.
- [x] The portal's Check-your-WhatsApp copy tells the user to send `verify <nonce>` to the agent, in all three languages, and no string claims a code was sent to the phone — `python3 tests/check_landing.py` (asserts `portal_verify_instruction` contains `verify` + `{nonce}` in en/ur/roman, and the whole strings blob against the reverse-verification denylist).
- [x] No payment collection anywhere under `landing/` — `python3 tests/check_landing.py` (no card/CVV/IBAN input, no payment-provider script/href/action).
- [x] No WhatsApp logo asset and no "WhatsApp" inside the product name; brand is exactly `Hosted Hisab` — `python3 tests/check_landing.py`.
- [x] `firebase.json` serves `landing/out` and configures the hosting emulator — `python3 tests/check_landing.py`; `firebase.json` also hand-verified against the plan's literal shape.
- [x] `landing/` builds to a static export containing both routes — `cd landing && npm run build` → `out/index.html` and `out/portal/index.html` present (re-run after the lead's edits to `check_landing.py`/`strings.json`, still green).
- [x] Repo check passes — `python3 tests/smoke.py` → prints `landing: ok` then `ALL OK`.
- [?] The exact manual walkthrough in the plan (`make landing && make landing-serve`, open `http://localhost:5000/`, toggle language and OS dark mode, step the portal's demo switcher, capture the four screenshots for the write-up) — functionally equivalent steps were run this session via Playwright, all passed, but port 5000 is claimed by macOS AirPlay Receiver on this dev machine (verified against `:5050` instead), and the four write-up screenshots were not retained. A human should do the literal walkthrough once (on a machine where 5000 is free, or with AirPlay Receiver turned off) and capture the screenshots for the submission.

## Conventions

- **Surface.** No new Python beyond a test (`tests/check_landing.py`); `hisab/` untouched; six tools unchanged.
- **Writes / transport.** N/A — this slice has no ledger or WhatsApp-transport code.
- **Language.** `landing/content/strings.json` follows `hisab/i18n.py`'s `{en, ur, roman}` shape; every key has all three, non-empty (checker-enforced); Roman Urdu register matches the agent's own voice, not translated marketing copy.
- **Privacy.** Scanned `landing/`, `firebase.json`, `tests/check_landing.py` for paths, tokens, real names — clean. No `.firebaserc`. `landing/node_modules/`, `.next/`, `out/` gitignored (`git add --dry-run landing/` confirms none would be staged).
- **Tests.** `check_landing.py` is exercised from `tests/smoke.py` (skips gracefully if `landing/` is absent).
- **Docs.** `README.md` carries a short "Hosted Hisab (in progress)" section after "Run it for real"; `landing/README.md` documents the three commands and the `strings.json` contract.

## Findings

None. The lead's post-implementation edits (`check_landing.py` now fails loudly if no `verify_instruction` key exists at all; a `portal_connect_key_note` wording tweak) are both sound and don't regress anything — re-verified with a fresh `npm run build`, `check_landing.py`, and `smoke.py` after picking them up.
