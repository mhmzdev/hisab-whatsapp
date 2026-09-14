---
type: Checklist
title: GH-37-portal-pk-phone-normalise
description: Acceptance checklist for the portal normalising Pakistani mobile numbers before phone sign-in.
tags: [checklist, portal, auth, landing]
timestamp: 2026-09-14T00:00:00Z
---

# GH-37-portal-pk-phone-normalise — acceptance checklist   (5 proven · 0 manual · 0 failing)

Plan: [GH-37-portal-pk-phone-normalise](../exec-plans/completed/GH-37-portal-pk-phone-normalise.md) · Issue: [#37](https://github.com/mhmzdev/hisab-whatsapp/issues/37) · Scope: Pakistani mobiles only (owner).

- [x] `03460159889`, `3460159889`, `0346 0159889`, `0346-0159889`, `+923460159889`, `923460159889`, `00923460159889` and `+92 346 0159889` → `+923460159889` — `python3 tests/smoke.py` ("portal: 14 phone inputs normalise…", via node on `landing/app/portal/phone.js`)
- [x] `02134567890`, `346015988`, `034601598890`, `+14155550100`, `""` and `9234601598` → `null` — same test
- [x] `page.jsx` imports and calls `normalizePkMobile` and no longer builds `+92${…}` — `python3 tests/check_landing.py`; mutation: with the old `page.jsx` restored, both guards fail
- [x] Portal on the `make up` emulators after `make landing` (Playwright): `0346 0159889` → the emulator's `verificationCodes` holds `+923460159889`, and the screen reads `Sent to +92 3•• ••• 9889`; `021 34567890` → "Couldn't send the code. Check the number and try again.", with no new verification code
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`

## Conventions
- No new strings (reuses `portal_signin_error`); `landing/content/strings.json` is untouched.
- No Firebase, rules or runner change. The landing page still doesn't import portal code.

## Findings
_None._ Note: the owner's earlier emulator sign-in as `+9203460159889` is a different uid from `+923460159889`. It exists only on the local emulator; there's nothing to migrate.
