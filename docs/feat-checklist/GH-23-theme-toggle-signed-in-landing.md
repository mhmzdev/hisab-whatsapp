---
type: Checklist
title: GH-23-theme-toggle-signed-in-landing
description: Acceptance checklist for the header theme toggle, the brand mark linking home, and the signed-in landing call to action.
tags: [checklist, landing, portal, theme]
timestamp: 2026-09-14T00:00:00Z
---

# GH-23-theme-toggle-signed-in-landing — acceptance checklist   (11 proven · 1 manual · 0 failing)

Plan: [GH-23-theme-toggle-signed-in-landing](../exec-plans/completed/GH-23-theme-toggle-signed-in-landing.md) · Issue: [#23](https://github.com/mhmzdev/hisab-whatsapp/issues/23)

Browser checks ran with Playwright against `make landing` output served locally. An init script recorded `<html data-theme>` at the moment `<body>` was first inserted, i.e. before first paint.

- [x] The header on `/` and `/portal/` has the theme toggle next to the language switcher — header buttons `["English", "اردو", "◐ System"]` on `/`; `☾ Dark` on `/portal/`
- [x] The toggle cycles System → Light → Dark and persists — clicks gave `☀ Light` (`hisab-theme=light`) then `☾ Dark` (`hisab-theme=dark`, body background `rgb(11, 20, 26)`)
- [x] The choice survives reload with no flash — after reload, `data-theme` was already `dark` when `<body>` appeared, on `/` and on `/portal/`
- [x] Light on a dark device stays light, and System follows the device — emulated dark scheme with `light` saved: `light` at body; `system` saved: `dark` at body, then switching the emulated scheme to light changed `data-theme` to `light` without a reload
- [x] An unknown stored value falls back to System — `hisab-theme=purple`: `light` at body on a light device, label `◐ System`
- [x] The brand mark links to `/` on both routes — `href="/"`; clicking it on `/portal/` landed on `/`
- [x] Landing CTAs follow the signed-in hint — no `hisab-signed-in`: hero and pricing read `["Get started", "Get started"]`; `hisab-signed-in=1`: `["Go to portal", "Go to portal"]`; in Urdu `["پورٹل پر جائیں", "پورٹل پر جائیں"]`, toggle `◐ سسٹم`, aria-label `تھیم: سسٹم`
- [x] The landing page loads no Firebase or libsodium — none of the 7 scripts `out/index.html` loads contain `identitytoolkit|firebaseapp|libsodium|crypto_box_seal`, while `/portal/`'s chunk `d8adc87b-…js` does (the positive control); `check_landing.py` import rule passes
- [x] Guards bite — smoke runs the import rule against `./portal/firebase`, `firebase/auth` and a dynamic `libsodium-wrappers` import (each fails) and a layout without `THEME_SCRIPT` (fails); mutating either rule makes smoke fail with `AssertionError`
- [x] New strings in `en` and `ur`, both routes export — `python3 tests/check_landing.py` exits 0; `make landing` → both `out/index.html` and `out/portal/index.html` exist with the theme script inside `<head>`
- [x] Phone width — 400px, `/portal/` dark: header wraps on one row, `scrollWidth` 385 ≤ 400, no horizontal scroll; no console errors besides a pre-existing `favicon.ico` 404

Repo check: `python3 tests/smoke.py` — ALL OK.

- [?] The portal writes and clears the hint on a real sign-in — `make up`, open http://localhost:3031/portal/, sign in with the emulator OTP (printed in the Auth emulator log), open http://localhost:3031/ → both buttons read "Go to portal"; back in the portal, Sign out → confirm, open `/` → both read "Get started". Not run: needs the emulator stack; the landing side of the hint is proven above, the portal side (`portal/page.jsx` `onAuthStateChanged`) only by reading

## Conventions
- Surface, writes, transport, ledger: untouched (no file under `hisab/` or `runner/`).
- Language: five new strings, each `en` + `ur`; no Roman Urdu.
- Privacy: two non-sensitive `localStorage` keys (a theme name, a `1`); no identifier, phone or uid is stored for the landing page; no local path in the diff.
- Tests: both new guards exercised both ways in `tests/smoke.py`.
- Docs: `landing/README.md` has a "Theme and the signed-in hint" section and the `landing-check` row names the new rules.

## Findings
FINDING-01 · Minor · landing/app/page.jsx:24 — the CTA label is decided after hydration, so a signed-in visitor briefly sees "Get started" before it becomes "Go to portal". The theme itself never flashes; only this label does. Fixing it would need another pre-paint script, which isn't worth it for a label.
FINDING-02 · Minor · landing/app/ThemeToggle.jsx:11 — the toggle's own label renders "System" until its effect reads storage, for one frame. Same cause as FINDING-01; the page colours are already right.
FINDING-03 · Minor · landing/app/signedIn.js:1 — a stale `hisab-signed-in` after a session expires elsewhere keeps "Go to portal" until the next portal visit. Accepted in the plan, to keep Firebase off the landing bundle.
