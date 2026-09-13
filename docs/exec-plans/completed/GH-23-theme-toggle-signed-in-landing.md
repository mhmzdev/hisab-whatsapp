---
slug: GH-23-theme-toggle-signed-in-landing
issue: 23
status: completed
open_questions: none
---

# feat: Theme toggle and signed-in landing — logo links home, Get started becomes Go to portal          ✅ COMPLETED — 2026-09-14

## Problem
[#23](https://github.com/mhmzdev/hisab-whatsapp/issues/23). The landing page and portal only follow `prefers-color-scheme` (`landing/app/globals.css:27`), with no way to pick light on a dark phone or dark on a light one. The header brand mark (`landing/app/layout.jsx:15-18`) doesn't link anywhere. The landing page's calls to action (`landing/app/page.jsx:30`, `:218`) read "Get started" even for someone who already connected an agent.

## Approach
Owner scope (2026-09-14): all three parts of the issue in one PR. The theme tokens already exist; this adds a way to choose between them and makes the choice persist.

**Theme.**
- **Tokens.** `globals.css:27` changes `@media (prefers-color-scheme: dark) { :root {…} }` into a single `:root[data-theme="dark"] {…}` block, so the dark tokens are written once and the attribute is the only switch.
- **No flash.** `layout.jsx` gets a blocking inline `<script>` in `<head>`. It reads `localStorage['hisab-theme']` (`system` | `light` | `dark`, default `system`), resolves `system` through `matchMedia('(prefers-color-scheme: dark)')`, and sets `document.documentElement.dataset.theme` to `light` or `dark` before first paint. It is wrapped in try/catch: if storage throws, it falls back to the media query. `<html>` gets `suppressHydrationWarning` because the attribute is set before React hydrates.
- **Toggle.** New `landing/app/ThemeToggle.jsx` is one button that cycles System → Light → Dark. It persists to `localStorage['hisab-theme']`, sets the attribute, and while on System follows live `matchMedia` changes. Its label comes from `t('theme_<mode>')` and its `aria-label` from `t('theme_toggle_label')`. It uses the same pill style as `LanguageSwitcher.jsx:22-30`.
- **Placement.** The layout wraps `LanguageSwitcher` and `ThemeToggle` together on the right of the header. The header is in `layout.jsx`, so it renders on both routes.
- **Without JavaScript**, the page renders light. The site needs JS anyway (the portal is client-only).

**Brand mark.** `layout.jsx:15` changes `<div className="brand-mark">` to `<a className="brand-mark" href="/">`. `globals.css` gives `.brand-mark` `text-decoration: none` and a visible focus ring.

**Signed-in landing.**
- **Portal side.** The portal's `onAuthStateChanged` (`portal/page.jsx:459-465`) writes `localStorage['hisab-signed-in'] = '1'` when there is a user and removes it when there isn't. Sign-out goes through the same callback.
- **Landing side.** `page.jsx` reads the flag in a `useEffect` (try/catch). Hero (`:30`) and pricing (`:218`) CTAs render `t('cta_go_to_portal')` when the flag is set, and `hero_cta` / `price_cta` otherwise. The href stays `/portal/`.
- **Bundle.** The landing page imports nothing from `firebase/*`, `./portal/` or `libsodium`, so signed-out visitors load no Firebase code.
- **Stale flag.** If a session expires without the user visiting the portal, the landing page still says "Go to portal", and the portal then shows sign-in. That's the accepted cost of not loading Firebase on the landing page.

**Strings** (`landing/content/strings.json`, `en` + `ur`): `theme_toggle_label`, `theme_system`, `theme_light`, `theme_dark`, `cta_go_to_portal`.

**Check.** `tests/check_landing.py` adds two rules:
- `landing/app/page.jsx` must not import `firebase`, `libsodium` or anything under `./portal/`. This is the issue's bundle rule, made mechanical.
- `landing/app/layout.jsx` must contain the `hisab-theme` pre-paint script, so the no-flash guarantee can't be silently removed.

`tests/smoke.py` runs both rules against a fake root, once passing and once failing, like the GH-22 language rule.

Invariants: nothing under `hisab/` or `runner/`; `firestore.rules` untouched; no new network call; two languages.

## Success criteria
- [ ] The header on `/` and `/portal/` has the theme toggle; the choice survives a reload and the first paint already matches — `verify: manual 1. make landing, serve landing/out 2. on /, click the toggle to Dark, reload — html[data-theme=dark] before hydration (read in a script inserted at the top of body) 3. same on /portal/ 4. Light on an emulated dark scheme stays light after reload 5. System follows an emulated scheme change without a reload`
- [ ] The brand mark links to `/` on both routes — `verify: manual — from /portal/, click the brand mark, land on /`
- [ ] Signed in through the portal, the hero and pricing buttons read "Go to portal"; signed out, "Get started" — `verify: manual — make up, sign in with the emulator OTP, open /, both buttons read Go to portal; sign out in the portal, open /, both read Get started`
- [ ] The landing page loads no Firebase or libsodium — `verify: python3 tests/check_landing.py` (import rule) and `grep -L firebase landing/out/_next/static/chunks/app/page-*.js`
- [ ] New strings exist in `en` and `ur` and `tests/check_landing.py` passes — `verify: python3 tests/check_landing.py`
- [ ] `cd landing && npm run build` still exports both routes — `verify: make landing && test -f landing/out/index.html && test -f landing/out/portal/index.html`
- [ ] Repo check passes — `verify: python3 tests/smoke.py`

## Phases
### Phase 1 — Theme toggle, persistence, no flash, brand link
**Status:** Done — dark tokens under `:root[data-theme="dark"]` (+ `color-scheme`), `theme.js` pre-paint script in `<head>` (verified in both exported HTML files), `ThemeToggle.jsx` cycles System → Light → Dark next to the language switcher, brand mark is `<a href="/">`, four `theme_*` strings
- Files: `landing/app/globals.css:27-52,93-97`, `landing/app/layout.jsx`, new `landing/app/ThemeToggle.jsx`, `landing/content/strings.json`
- Change: as in Approach (Theme, Brand mark, the four `theme_*` strings).
- Test: `make landing`; `python3 tests/check_landing.py`.

### Phase 2 — Signed-in landing CTAs
**Status:** Done — `signedIn.js` holds the key; portal sets/removes it in `onAuthStateChanged`; hero and pricing CTAs read `cta_go_to_portal` when set; all 7 scripts `out/index.html` loads are free of Firebase/libsodium (the portal's chunks are not)
- Files: `landing/app/portal/page.jsx:459-465`, `landing/app/page.jsx:19-30,218`, `landing/content/strings.json` (`cta_go_to_portal`)
- Change: as in Approach (Signed-in landing).
- Test: `make landing`; the bundle grep.

### Phase 3 — Guards and docs
**Status:** Done — `check_landing.py` rejects Firebase/libsodium/portal imports in `page.jsx` and a layout without the pre-paint script; smoke proves pass and fail for each (both mutation-checked); `landing/README.md` documents the two keys
- Files: `tests/check_landing.py`, `tests/smoke.py` (landing block), `landing/README.md` (a short "Theme and signed-in hint" section: the two storage keys, who writes them, the no-Firebase-on-landing rule)
- Change: the two check rules; smoke runs each against a fake root, once passing and once failing.
- Test: `python3 tests/smoke.py`.

## Risks
- A browser that blocks storage gets System on every visit and "Get started" always. It degrades, it doesn't break.
- A stale `hisab-signed-in` flag after the session expires elsewhere (see Approach).
- Next's static export can re-order `<head>` children. Verify from the built `out/index.html` that the script lands in `<head>` before the stylesheet paints.

## Out of scope
- Syncing the theme to the account or across devices. The issue says per browser.
- A server-side signed-in check.
- Theming the WhatsApp agent or `hisab_dark.png` / `hisab_light.png` usage.
