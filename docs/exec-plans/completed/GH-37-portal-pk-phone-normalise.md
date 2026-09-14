---
slug: GH-37-portal-pk-phone-normalise
issue: 37
status: completed
open_questions: none
---

# fix: Portal sign-in normalises Pakistani mobile numbers to +923XXXXXXXXX          ✅ COMPLETED — 2026-09-14

## Problem

[#37](https://github.com/mhmzdev/hisab-whatsapp/issues/37): the sign-in field shows a fixed `+92` prefix but prepends it to whatever was typed (`landing/app/portal/page.jsx:38-47`: `digits.replace(/\D/g, '')`, `length < 9`, `` `+92${local}` ``). `0346 0159889`, the way most Pakistanis write a number, became `+9203460159889` on the #27 live test. A pasted `+92…` would become `+9292…`. Nothing checks the result is a Pakistani mobile. The owner's scope: Pakistani numbers only, until WhatsApp opens agents to more countries.

## Approach

A pure, dependency-free ES module, `landing/app/portal/phone.js`, sits beside `crypto.js`, which set the pattern for code that smoke exercises through `node`:

```js
// Pakistani mobiles only (#37): +92 then 3 and nine digits. Accepts how people actually type or paste one.
export function normalizePkMobile(input) {
  let d = String(input || '').replace(/\D/g, '')
  if (d.startsWith('0092')) d = d.slice(4)
  else if (d.startsWith('92') && d.length === 12) d = d.slice(2)
  else if (d.startsWith('0') && d.length === 11) d = d.slice(1)
  return /^3\d{9}$/.test(d) ? `+92${d}` : null
}
```

`SigninState.send` calls it and sets `portal_signin_error` when it returns `null`, before any reCAPTCHA or OTP request. It then passes the normalised number to `signInWithPhoneNumber` and `onSent`. The OTP mask (`page.jsx:126`) already slices `+92` and the `3`, so a normalised number masks as `+92 3•• ••• 9889` with no change. The input gets `maxLength={16}` and `inputMode="numeric"`. The placeholder, the `+92` prefix and the strings don't change, and no new string is needed.

A local mobile can't start with `9`, so a 12-digit `92…` is unambiguous. `0092` covers the international dialling prefix.

## Success criteria

- [x] `03460159889`, `3460159889`, `0346 0159889`, `0346-0159889`, `+923460159889`, `923460159889` and `00923460159889` all normalise to `+923460159889` — `verify: python3 tests/smoke.py` (runs `phone.js` through `node`, like the crypto round trip; skipped without node)
- [x] `02134567890` (landline), `346015988` (short), `034601598890` (long), `+14155550100` and an empty string all return `null` — same verify
- [x] `page.jsx` sends only the normalised number, sets `portal_signin_error` on `null` before any OTP request, and no longer builds `` `+92${local}` `` — `verify: python3 tests/check_landing.py` (a static check: `normalizePkMobile` is imported and used in `page.jsx`, and the old template literal is gone)
- [x] Phone: typing `0346 0159889` requests the code for `+923460159889` and the OTP screen shows `+92 3•• ••• 9889` — `verify: manual 1. make landing && make emulators-down && make emulators-up (rebuilds landing/out) 2. open http://localhost:3031/portal/ signed out 3. enter 0346 0159889 4. curl http://localhost:9099/emulator/v1/projects/demo-hisab/verificationCodes shows +923460159889 5. the screen reads "+92 3•• ••• 9889"`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Normaliser, portal wiring, checks
**Status:** Done — `phone.js` `normalizePkMobile`; `page.jsx` sends only its result (`inputMode=numeric`, `maxLength=16`); smoke runs 14 inputs through node; `check_landing.py` guards the import and the old `+92${…}` (fails on the old page)
- Files: new `landing/app/portal/phone.js`; `landing/app/portal/page.jsx:9,37-49,64-73`; `tests/smoke.py` (beside the crypto round trip, ~line 915); `tests/check_landing.py` (portal checks)
- Change: as in Approach.
- Test: a smoke node run of every input above, asserted against the expected output; `check_landing.py` asserts `from './phone'` or `import { normalizePkMobile }` in `page.jsx` and the absence of `` `+92${local}` ``.

### Phase 2 — The portal on the emulators
**Status:** Done — `make landing` (emulators left running); Playwright: `0346 0159889` → emulator code for `+923460159889`, screen `Sent to +92 3•• ••• 9889`; `021 34567890` → `portal_signin_error`, no OTP requested
- The manual criterion above.

## Risks

- A real user who already signed in with a malformed number (only possible on the emulator today; the hosted product isn't live) would get a different uid after this. Nothing to migrate.

## Out of scope

- Other countries and a country picker (owner: later, as WhatsApp opens agents).
- Firebase Auth-side validation or blocking.
