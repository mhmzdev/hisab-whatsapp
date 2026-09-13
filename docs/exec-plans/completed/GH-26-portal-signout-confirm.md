---
slug: GH-26-portal-signout-confirm
issue: 26
status: completed
open_questions: none
---

# fix: Portal sign-out asks for confirmation before dropping the session          ✅ COMPLETED — 2026-09-14

## Problem
[#26](https://github.com/mhmzdev/hisab-whatsapp/issues/26). The portal's "Sign out" button in the eyebrow row calls `signOut(firebase().auth)` straight from `onClick` (`landing/app/portal/page.jsx:467`). One stray tap drops the user back to the phone form, and signing back in costs an SMS OTP round trip. Revoke already asks first; sign-out should too.

## Approach
**Changed mid-build by the owner (2026-09-13):** the first build reused Revoke's inline `.confirmBox` exactly, as the issue asked. On seeing it the owner asked for a modal instead ("make this as alert or modal. Not some in-line UI"). What shipped is the modal; `.confirmRow`, `.buttonDangerSolid` and `.buttonOutline` are still reused from Revoke (`portal.module.css:277-318`).

- `Portal` gains `askingSignOut` state; `onAuthStateChanged` resets it, so a dialog never survives into the next session.
- The eyebrow button's `onClick` becomes `() => setAskingSignOut(true)`.
- `confirmSignOut()` in `Portal` is the only call site of `signOut(firebase().auth)`: it closes the dialog, clears the error, and on failure logs and sets `portal_error_unknown`, matching `confirmRevoke`.
- New `SignOutDialog({ t, onConfirm, onCancel })`, rendered after `.frame` inside `<main>` when `user && askingSignOut`: a fixed full-page `.modalBackdrop` holding a `.modal` card with `role="alertdialog"`, `aria-modal`, and title/description ids. Escape or a backdrop click cancels; clicks inside the card don't bubble up. Focus starts on "Stay signed in", so Enter after a stray open keeps the session. Cancel sits first, confirm second (solid red).
- New CSS: `.modalBackdrop`, `.modal`, `.modal h2`, `.modal p` in `portal.module.css`, using the existing `--surface` / `--line` / `--text2` tokens.
- Four new keys in `landing/content/strings.json` after `portal_signout`, each in `en`, `ur`, `roman` (#22 is still open):
  - `portal_signout_confirm_title` — "Sign out?" · "سائن آؤٹ کریں؟" · "Sign out karein?"
  - `portal_signout_confirm_text` — "Your agent keeps running. Signing back in needs a new SMS code." · "آپ کا ایجنٹ چلتا رہے گا۔ دوبارہ سائن ان کے لیے نیا SMS کوڈ درکار ہوگا۔" · "Aap ka agent chalta rahega. Dobara sign in ke liye naya SMS code chahiye hoga."
  - `portal_signout_confirm_yes` — "Sign out" · "سائن آؤٹ" · "Sign out"
  - `portal_signout_confirm_no` — "Stay signed in" · "سائن ان رہیں" · "Sign in rahein"

The text is accurate: `signOut` only clears the browser's auth session, and the runner and worker never read it. The wording steers clear of `check_landing.py`'s reverse-verification denylist.

Invariants untouched: no agent, tool, ledger, store or runner change. Firestore writes unchanged.

## Success criteria
- [x] Clicking "Sign out" opens a modal; Escape, a backdrop click, "Stay signed in" and Enter (default focus) all keep the session; confirm signs out and lands on the phone form — `verify: manual 1) make landing && make emulators-up, 2) open http://localhost:3031/portal/, sign in with a test number, OTP from curl localhost:9099/emulator/v1/projects/demo-hisab/verificationCodes, 3) click Sign out → alertdialog over the page, 4) Escape / backdrop / Enter / "Stay signed in" → dialog gone, still signed in, 5) Sign out → "Sign out" in the dialog → phone form`
- [x] Only the confirm handler calls `signOut` — `verify: test "$(grep -c 'signOut(firebase().auth)' landing/app/portal/page.jsx)" = 1 && ! grep -n 'onClick={() => signOut' landing/app/portal/page.jsx`
- [x] The four confirm strings exist in en/ur/roman and landing checks pass — `verify: python3 tests/check_landing.py && python3 -c "import json;s=json.load(open('landing/content/strings.json'));assert all(k in s for k in ['portal_signout_confirm_title','portal_signout_confirm_text','portal_signout_confirm_yes','portal_signout_confirm_no'])"`
- [x] The static export still produces both routes — `verify: cd landing && npm run build && test -f out/portal/index.html && test -f out/index.html`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases
### Phase 1 — Confirm dialog and strings
**Status:** Done — inline box first, replaced by `SignOutDialog` on owner feedback; all verify commands green, manual path walked in Playwright (en desktop, ur at 400px)
- Files: `landing/app/portal/page.jsx` (`:418-434` state + auth reset, `:466-468` eyebrow button, dialog rendered after `.frame`), `landing/app/portal/portal.module.css` (modal classes), `landing/content/strings.json` (`:442` four keys after `portal_signout`)
- Change: as in Approach.
- Test: `python3 tests/check_landing.py` covers three-language completeness of the new keys; build + manual run above.

## Risks
- The emulator run needs the self-host container stopped first (same agent token) — only relevant if bringing up the whole `make up` stack; the portal path alone needs just emulators + `landing/out`.
- The dialog doesn't trap Tab: focus can tab out to the page behind the backdrop. Acceptable for a two-button dialog; clicks can't reach the page.

## Out of scope
- Any agent/worker/runner behaviour on sign-out (there is none, by design).
- #22's language reduction.
- Converting Revoke's inline confirm to the same modal (possible follow-up for consistency).
- Restyling the eyebrow row.
