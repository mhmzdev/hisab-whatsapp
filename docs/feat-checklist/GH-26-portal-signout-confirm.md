---
type: Checklist
title: GH-26-portal-signout-confirm
description: Acceptance checklist for the portal sign-out confirmation dialog.
tags: [checklist, portal, landing]
timestamp: 2026-09-14T00:00:00Z
---

# GH-26-portal-signout-confirm — acceptance checklist   (7 proven · 1 manual · 0 failing)

Scope: 5 files. `landing/app/portal/page.jsx`, `landing/app/portal/portal.module.css`, `landing/content/strings.json`, plus the plan and INDEX. Intent: [#26](https://github.com/mhmzdev/hisab-whatsapp/issues/26) and [the plan](../exec-plans/completed/GH-26-portal-signout-confirm.md).

**Deviation from the issue, on purpose.** #26's first `Done when` box asks for "the same inline confirm box Revoke uses". That was built first, then replaced when the owner reviewed it mid-build and asked for a modal ("make this as alert or modal. Not some in-line UI"). The items below check the modal.

- [x] Clicking "Sign out" opens a modal `alertdialog` over the page and the session stays — Playwright on the emulator build (`make emulators-up`, :3031/portal/, test number +92 300 1234567, OTP from the Auth emulator's `verificationCodes`): snapshot showed `alertdialog "Sign out?"` over the Connect screen
- [x] Escape, a backdrop click (corner), Enter (focus starts on "Stay signed in") and "Stay signed in" all close the dialog and keep the user signed in — same run: `{"focused":"Stay signed in","afterEnter":{"dialog":0,"signedIn":1},"afterBackdrop":{"dialog":0,"signedIn":1}}`, plus a separate Escape step; a click inside the card left it open
- [x] Confirm signs out and lands on the phone form — same run: `"afterConfirm":{"dialog":0,"phoneForm":1}`
- [x] Only the confirm handler calls `signOut` — `test "$(grep -c 'signOut(firebase().auth)' landing/app/portal/page.jsx)" = 1 && ! grep -n 'onClick={() => signOut' …` passes
- [x] The four new strings exist in en/ur/roman and the landing checks pass — `python3 tests/check_landing.py` plus the key-presence assertion pass. Urdu renders right-to-left inside the dialog at 400px width (screenshot checked)
- [x] The static export still produces both routes — `cd landing && npm run build && test -f out/portal/index.html && test -f out/index.html` passes
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`
- [?] On a real phone against the real Firebase project (where #26 was found): open /portal/ signed in, tap Sign out → the dialog appears, tap outside → still signed in, tap Sign out → Sign out → phone form. Not run: the dev project isn't provisioned yet, and SMS OTPs cost money. Emulator and desktop/400px browser runs only.

## Conventions
- Surface, writes, transport, dashboard conventions: untouched. The change is portal-only; no agent, tool, ledger, store, runner or Firestore-write change.
- Language: landing strings live in `landing/content/strings.json` (not `i18n.py`), with all three languages present, and `check_landing.py` enforces it.
- Privacy: no personal path, token or number. The test number is a made-up emulator number, and the screenshots stay under the gitignored `.playwright-mcp/`.
- Tests: no JS test harness exists for the portal, so the dialog's behaviour is proven only by the Playwright run above. No smoke test covers it.
- Docs: no README or ARCHITECTURE line mentions sign-out, so there is nothing stale.

## Findings
FINDING-01 · Minor · landing/app/portal/page.jsx:420 — `SignOutDialog` doesn't trap Tab focus, so keyboard focus can tab out to controls behind the backdrop. Pointer clicks can't reach them. Acceptable for a two-button dialog; noted, not fixed.
FINDING-02 · Minor · landing/app/portal/portal.module.css — the page behind the dialog can still scroll (no body scroll lock). Harmless on the short portal card.
FINDING-03 · Minor · landing/app/portal/page.jsx:391-401 — Revoke still uses the inline confirm box, so the two confirmations now look different. Converting Revoke to the same dialog is a follow-up, outside #26.
FINDING-04 · Minor · landing/app/portal/page.jsx:420 — after a click inside the card (not on a button), focus leaves "Stay signed in" and Enter does nothing until Tab or a click. Safe direction (never signs out); seen in the Playwright run.
