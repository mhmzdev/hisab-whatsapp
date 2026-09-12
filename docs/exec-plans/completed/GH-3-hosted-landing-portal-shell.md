---
slug: GH-3-hosted-landing-portal-shell
issue: 3
status: completed
open_questions: none
---

# feat: Serve the Hosted Hisab landing page and portal shell          ✅ COMPLETED — 2026-09-12

## Problem

Hosted Hisab has a decided WHAT ([spec 001](../../specs/001-hosted-portal.md), [brainstorm](../../brainstorm/hosted-portal.md), parent issue [#1](https://github.com/mhmzdev/hisab-whatsapp/issues/1)) and no surface. [#3](https://github.com/mhmzdev/hisab-whatsapp/issues/3) is the first slice: a branded landing page that states the hosted custody trade honestly and presents the 300 PKR/month plan, plus a portal shell that renders the four connection states as static mocks. Nothing behind it — Firestore, the runner and Firebase Auth are [#4](https://github.com/mhmzdev/hisab-whatsapp/issues/4)–[#8](https://github.com/mhmzdev/hisab-whatsapp/issues/8) and are not this plan's scope.

Today's deliverable is also the demo asset: the landing hero is the still the submission video cuts to, and the four portal states are the screenshots the write-up uses. Blocked by: nothing.

## Approach

A new `landing/` **Next.js app, App Router, `output: 'export'`** — the stack locked in spec 001 — with **no UI framework and no web fonts**. Plain CSS custom properties carry the WhatsApp green palette in light and dark; every dependency beyond `next`/`react`/`react-dom` is a failure mode we cannot afford today, and Tailwind's setup churn buys nothing for two pages. Plain JavaScript (`.jsx`), no TypeScript, for the same reason. No `next/image` (it forces `images.unoptimized` under export); inline SVG and plain `<img>` only. `trailingSlash: true` so `out/portal/index.html` serves at `/portal/` under Firebase Hosting *and* under `python3 -m http.server`, with no rewrite rules needed to see it work.

**Three languages, the repo's way.** `hisab/i18n.py:6` is the pattern — one dict, key → `{en, ur, roman}`, and a string that lacks one of the three does not ship. The static landing cannot import Python, so it carries the same shape as **`landing/content/strings.json`**: JSON, not JS, so `tests/check_landing.py` reads it with stdlib `json` while Next imports it directly. A client `LanguageProvider` (React context, `localStorage` in try/catch, default `en`) switches the whole page; the wrapper div takes `lang`/`dir="rtl"` when Urdu is active. The portal shell is **fully** trilingual (issue criterion 4). The landing carries all three for the strings a visitor must understand to make a decision — hero, custody strip, the three example cards, pricing, CTA, footer — which is every fixed user-facing string on the page under this plan's copy budget.

**Verification direction is the one thing the copy must not get wrong.** The portal *displays* the nonce; the user *sends* `verify <nonce>` to their agent. The "Check your WhatsApp" state shows the command, a copy button, and a waiting indicator. It never says a code was sent to the phone. `tests/check_landing.py` enforces this positively (every language's check-state string contains both `verify` and the `{nonce}` placeholder) and negatively (a denylist of reverse-direction English phrasings across the whole strings file). The command token stays Latin `verify <nonce>` in all three languages because the runner matches it literally (spec 001, "Verification and language").

**No backend, and it must be obvious.** `/portal` renders one of four states from `?state=connect|check|connected|revoked` (default `connect`); all displayed values come from `landing/content/mock.js`, fake kiryana data in the register of `sample-vault/`. The demo nonce is a constant `482913`, display-only. A `data-demo-only` state-switcher row sits at the foot of the portal so the four screenshots are one click apart; #7 deletes it by that one selector.

**Custody honesty and no payment collection.** The landing carries a custody strip that says plainly that hosted Hisab holds the key and the ledger, next to the self-host link to this repo, which keeps its own "no server of ours" claim. Pricing is a presentation block — *300 PKR / month · first month free* — whose only action is *Get started* → `/portal`. No payment provider script, no card field; the check enforces both.

**The repeatable check.** `tests/check_landing.py`, pure stdlib Python, no node: three-language completeness, verification direction, no payment collection, no WhatsApp logo asset or "WhatsApp" in the product name, `firebase.json` shape. `tests/smoke.py` calls it before `ALL OK` (skipping with a printed note if `landing/content/strings.json` is absent, so a sparse checkout stays green), and `make landing-check` runs it alone. `make landing` builds; `make landing-serve` serves `landing/out` with Python's http server so the local Firebase Hosting workflow can be seen without waiting on an npm install of `firebase-tools`.

**Invariants kept.** Nothing here touches `hisab/`: six tools, the strict-check append path, entry numbers, offset-after-batch are untouched by design — this slice adds no Python beyond a test. Three-languages-or-none is extended, not bent. Privacy: every name, number and screenshot is fake sample data; no `.firebaserc` (a real project id) is committed; `landing/node_modules/`, `landing/.next/`, `landing/out/` are gitignored. Stage by name, never `git add -A`.

### Time box

Hard stop **14:15 PKT today**. Phases are ordered so the state at any moment is shippable, never half-built:

| By | State on disk |
|---|---|
| Phase 1 done | `landing/` builds to `out/`, check script green, Makefile wired — nothing user-facing yet |
| Phase 2 done | Every string exists in three languages; pages still skeletal |
| **Phase 3 done** | **The landing page is finished and screenshot-ready — the video still exists** |
| Phase 4 | Portal states land one at a time, each complete before the next starts: connect → check → connected → revoked |

**Tripwire:** if Phase 4 has not started by **13:45 PKT**, ship Phases 1–3 plus a `/portal` that renders the Connect state only, and move the other three states to a follow-up on #3. A finished landing plus one honest portal state beats four unfinished ones.

## Success criteria

- [x] `landing/` builds to a static export containing the landing page and the portal route — `verify: cd landing && npm install && npm run build && test -f out/index.html && test -f out/portal/index.html`
- [x] Every user-facing string carries `en`, `ur` and `roman`, non-empty — `verify: python3 tests/check_landing.py`
- [x] The portal's Check-your-WhatsApp copy tells the user to send `verify <nonce>` to the agent, in all three languages, and no string anywhere claims a code was sent to the phone — `verify: python3 tests/check_landing.py`
- [x] No payment collection: no card/CVV/IBAN input, no payment-provider script or form action anywhere under `landing/` — `verify: python3 tests/check_landing.py`
- [x] No WhatsApp logo asset and no "WhatsApp" inside the product name; the brand string is exactly `Hosted Hisab` — `verify: python3 tests/check_landing.py`
- [x] `firebase.json` serves `landing/out` and configures the hosting emulator — `verify: python3 tests/check_landing.py`
- [x] A visitor sees the hosted/self-hosted custody distinction, three product examples, the 300 PKR/month presentation plan and a Get-started path — verified in-browser (port 5000 is claimed by macOS AirPlay Receiver on this machine, so `landing-serve` was pointed at :5050 for this check instead): hero "A ledger you text", the custody line naming key and ledger, three example cards, the pricing block (300 PKR / month · first month free), and Get started → `/portal/`, all within two folds; اردو and Roman Urdu both verified, Urdu renders right-to-left; OS dark mode followed via `prefers-color-scheme`.
- [x] The portal shell renders all four states with no ledger contents and no live data — verified in-browser: Connect shows name + key fields and the four-step path; Check shows the literal `verify 482913` with a copy button and a waiting line, never claiming a code was sent to the phone; Connected shows agent name, connected since, last activity, entries this month, language and Revoke; Revoked shows the stopped state and the 30-day retention line; no transaction, balance or account name appears in any state.
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Scaffold, prove the build, wire the check
**Status:** Done — Next.js 15 App Router static export builds cleanly (no fallback needed); `firebase.json`, `tests/check_landing.py`, `smoke.py` wiring and `Makefile` targets all green.

- Files: `landing/package.json`, `landing/next.config.mjs`, `landing/jsconfig.json`, `landing/app/layout.jsx`, `landing/app/globals.css`, `landing/app/page.jsx`, `landing/app/portal/page.jsx`, `landing/content/strings.json`, `landing/.gitignore`, `firebase.json`, `tests/check_landing.py`, `tests/smoke.py:66`, `Makefile:4`, `.gitignore:26`
- Change:
  - `landing/package.json`: name `hisab-landing`, private, deps `next ^15`, `react ^19`, `react-dom ^19`, scripts `dev`/`build` (`next build`) — under `output: 'export'` Next 15 writes `out/` from `next build`, there is no separate export step.
  - `landing/next.config.mjs`: `export default { output: 'export', trailingSlash: true }`.
  - `landing/app/globals.css`: the palette as custom properties on `:root` — `--brand:#128C7E; --brand-strong:#075E54; --accent:#25D366; --bubble:#DCF8C6; --bg:#FFFFFF; --surface:#F7F8FA; --text:#111B21; --muted:#667781; --line:#E3E7EA` — redefined under `@media (prefers-color-scheme: dark)` as `--bubble:#005C4B; --bg:#0B141A; --surface:#111B21; --text:#E9EDEF; --muted:#8696A0; --line:#22303C`, `--brand`/`--accent` unchanged. System font stack; an `.urdu` class whose stack starts `"Noto Nastaliq Urdu", "Jameel Noori Nastaleeq"` and falls back to the system stack — **no web font is fetched**. `body` takes an explicit `--bg`/`--text`; max page width 1040px with 16px side padding that survives at 400px.
  - `landing/app/layout.jsx`: `<html lang="en">`, metadata title `Hosted Hisab`, imports `globals.css`. Pages are skeletons this phase: an `<h1>` each, enough to prove routing and export.
  - `landing/content/strings.json`: `{"brand": {"en": "Hosted Hisab", "ur": "Hosted Hisab", "roman": "Hosted Hisab"}}` plus the two keys Phase 2 will need first, so the checker has something real to assert against.
  - `firebase.json` at the repo root: `{"hosting": {"public": "landing/out", "ignore": ["firebase.json", "**/.*", "**/node_modules/**"], "cleanUrls": true}, "emulators": {"hosting": {"port": 5000}, "ui": {"enabled": false}}}`. No `.firebaserc` — it would carry a real project id; it is gitignored instead.
  - `tests/check_landing.py`: stdlib only. `LANGS = ("en", "ur", "roman")` mirroring `hisab/i18n.py:4`. A `run(root)` function returning a list of failures plus `if __name__ == "__main__"` printing each failure and exiting 1 on any. Checks: (a) every value in `strings.json` is an object with all three langs, each a non-empty string; (b) any key whose name starts `verify_` has `verify` and `{nonce}` in all three values; (c) the whole strings blob matches none of the reverse-direction denylist — `we (have )?(sent|will send)`, `code (was )?sent to (your|the) (phone|whatsapp|number)`, `check your (phone|messages) for the code`, `enter the code (we|hisab) sent`, case-insensitive; (d) no `<input` under `landing/app` whose `name`/`type`/`placeholder` matches `card|cvc|cvv|iban|expiry`, and no `src=`/`href=`/`action=` value matching `stripe|paypal|razorpay|jazzcash|easypaisa|checkout\.`; (e) no file under `landing/` matching `whatsapp*.svg|png|jpg|webp`, and no strings value matching `Hisab for WhatsApp|WhatsApp Hisab|Hisab WhatsApp`; (f) `strings.json["brand"]["en"] == "Hosted Hisab"`; (g) `firebase.json` parses, `hosting.public == "landing/out"`, `emulators.hosting.port` present. Each failure is one plain line naming the key or file.
  - `tests/smoke.py`: before `print("ALL OK")` at `tests/smoke.py:66`, add — if `landing/content/strings.json` exists, import `check_landing` from the tests directory, run it, `assert not failures, failures`, `print("landing: ok")`; else `print("landing: skipped (no landing/)")`.
  - `Makefile`: `landing` (`cd landing && npm install && npm run build`), `landing-check` (`python3 tests/check_landing.py`), `landing-serve` (`cd landing/out && python3 -m http.server 5000`), each with a `##` help line, added to `.PHONY` at `Makefile:4`.
  - `.gitignore`: add `landing/node_modules/`, `landing/.next/`, `landing/out/`, `landing/.env*.local`, `.firebaserc` under a `# landing build output` heading near the existing scratch block at `.gitignore:26`.
- Test: `cd landing && npm install && npm run build` produces `out/index.html` and `out/portal/index.html`; `python3 tests/check_landing.py` exits 0; `python3 tests/smoke.py` prints `landing: ok` then `ALL OK`. **This phase fails fast on purpose — if the toolchain fights back, we learn it at 13:00, not 14:00.**

### Phase 2 — The trilingual content file and the language switcher
**Status:** Done — full en/ur/roman key set for landing + portal in `strings.json`; `LanguageProvider`/`LanguageSwitcher` wired into `layout.jsx`, `localStorage` guarded with try/catch.

- Files: `landing/content/strings.json`, `landing/app/LanguageProvider.jsx`, `landing/app/LanguageSwitcher.jsx`, `landing/app/layout.jsx`
- Change:
  - Fill `strings.json` with every fixed string both pages need, each with `en`/`ur`/`roman`, grouped by key prefix: `brand`, `nav_*`, `hero_*`, `card_*` (three cards: text entry · Urdu voice note · receipt photo), `custody_*` (the hosted-holds-key-and-ledger line plus the self-host link label), `why_*` (undo is a reply · every line links to its message), `price_*` (300 PKR / month, first month free, what it covers, the Get started label), `footer_*`, and the portal keys `portal_connect_*`, `portal_verify_*`, `portal_connected_*`, `portal_revoked_*`. Urdu values are Urdu script; Roman Urdu values are Latin, in the register of `hisab/i18n.py:10-40` — the same voice as the agent's own replies, not translated marketing English.
  - `LanguageProvider.jsx` (`'use client'`): context holding `lang` and `setLang`, initial `en`, read from and written to `localStorage['hisab-lang']` inside try/catch (private windows and blocked storage must not break the page), and a `t(key)` helper that returns `strings[key][lang]` and falls back to `en` if a key is somehow missing at runtime.
  - `LanguageSwitcher.jsx`: three pills — `English` · `اردو` · `Roman Urdu` — mirroring the agent's own language question at `hisab/i18n.py:8`. The provider's wrapper div gets `lang={lang === 'ur' ? 'ur' : 'en'}` and `dir={lang === 'ur' ? 'rtl' : 'ltr'}` and the `.urdu` class when Urdu is active, so only copy flips, never the layout logic.
  - `layout.jsx` wraps children in the provider and renders the switcher in the header on both routes.
- Test: `python3 tests/check_landing.py` passes with the full key set (this is the phase where three-languages-or-none becomes a real constraint, not a formality); `python3 tests/smoke.py` green; the build still exports both routes.

### Phase 3 — The landing page
**Status:** Done — six blocks built and verified in-browser (1280px + 400px, all three languages, light + dark); custody strip sits beside the self-host link every time it appears.

- Files: `landing/app/page.jsx`, `landing/app/landing.module.css`, `landing/content/mock.js`
- Change: one page, six blocks, all copy through `t()`:
  1. **Hero** — *A ledger you text* over the custody-honest subline, a *Get started* button to `/portal/`, and a CSS phone mock (no image asset) showing three fake exchanges from `mock.js`, in the register of `sample-vault/2026-Q3.md`: `aaj ki sale 45000` → `#312 posted · sale PKR 45,000 · September in 1,184,500 / out 396,300`; a voice-note bubble `🎤 0:04` → `#313 posted · Metro stock PKR 31,000 on udhaar · Metro balance PKR 79,000`; `Metro ko kitna dena hai` → `Metro: PKR 79,000 outstanding`. Fake numbers, invented shop, no personal data.
  2. **Three cards** — text · voice note in Urdu · receipt photo.
  3. **Custody strip** — hosted Hisab holds the key and the ledger, encrypted, revocable, exportable; beside it the self-host line and a link to `https://github.com/mhmzdev/hisab-whatsapp` for the version where nothing leaves your machine. Both statements true, neither blurred.
  4. **Why not a chatbot** — undo is a reply; every ledger line sits beside the message that made it; every write passes `hledger check --strict`.
  5. **Pricing** — 300 PKR / month, first month free, one agent and one ledger, 1,000 model calls a month (spec 001). A single *Get started* action to `/portal/`; no price form, no provider, no card field.
  6. **Footer** — self-host repo link, the one-line hosted-vs-self-host distinction again, no logos.
  Responsive at 400px: blocks stack to one column, side padding set once on the page wrapper with `padding-block` for the vertical, no element wider than the viewport.
- Test: manual criterion 7 above, at 1280px and at 400px, in both themes and all three languages; `python3 tests/check_landing.py` and `python3 tests/smoke.py` green. **At the end of this phase the video still and the social screenshot exist.**

### Phase 4 — The portal shell, four states
**Status:** Done — all four states (connect → check → connected → revoked) built in order and verified in-browser; verify direction and no-ledger-contents confirmed by screenshot; `data-demo-only` wraps the whole switcher block for #7's one-selector removal.

- Files: `landing/app/portal/page.jsx`, `landing/app/portal/portal.module.css`, `landing/content/mock.js`
- Change: `/portal/` reads `?state=` (client-side, default `connect`) and renders exactly one state inside a shared card. Build them **in this order, each finished before the next begins** — the route must render something complete at every commit:
  1. **Connect agent** — agent name and API key fields (the key field `type="password"`, `autoComplete="off"`, and a line saying the key is never shown again), the four-step path *WhatsApp → Settings → Agents → your agent → Chat info → copy the API key* as text (no screenshot asset today), and a disabled-with-explanation *Connect* button — there is no backend yet and the UI must not pretend otherwise.
  2. **Check your WhatsApp** — the literal command `verify 482913` in a monospace block with a copy-to-clipboard button, the instruction to **send it to your agent**, a waiting indicator, and an expiry line. `mock.js` holds `NONCE = '482913'` with a comment marking it display-only until #7. This state is where the locked direction lives; the strings key is `portal_verify_instruction`, which the checker asserts on.
  3. **Connected** — agent name, connected since, last activity, entries this month, language, the *Send me my ledger* hint naming the exact `export-ledger` command, and a *Revoke key* button that only switches the local state. All values from `mock.js`. No transaction, balance or account name — the browser never shows ledger contents (spec 001, user story 7).
  4. **Revoked** — worker stopped, key deleted, the 30-day retention line, and how to reconnect.
  Below the card, a `data-demo-only` row of four links switching `?state=`, labelled as a demo control, so #7 removes it with one selector.
- Test: manual criterion 8 above — all four states screenshotted; `python3 tests/check_landing.py` (now asserting the verify keys for real) and `python3 tests/smoke.py` green.

### Phase 5 — Docs and the final pass
**Status:** Done — README.md and landing/README.md written; plan moved to completed/.

- Files: `README.md:60`, `landing/README.md`, `docs/exec-plans/INDEX.md`
- Change: a short **Hosted Hisab (in progress)** section in `README.md` after the *Run it for real* block — what the hosted service will be, that the key and ledger live on our server while self-host keeps them on yours, the 300 PKR/month figure marked as not yet collectable, and `make landing` / `make landing-serve` for running the page locally. `landing/README.md`: the three commands, the `strings.json` contract (a string ships in three languages or not at all), and the note that the portal is a shell with no backend until #7. Move this plan `backlog/ → completed/` and update its INDEX rows.
- Test: `python3 tests/smoke.py` green; `cd landing && npm run build` green; `git status` shows only intended paths and no `node_modules`, `out/`, `.firebaserc` or `*.pdf`.

## Risks

- **The clock.** Next.js `npm install` and first build are the only unbounded steps; Phase 1 exists to hit them first and to fail loudly. If `npm install` or `next build` is not green by **13:05 PKT**, drop Next entirely and re-target `landing/` as three hand-written static files (`index.html`, `portal/index.html`, `styles.css` + `strings.json` read by a small inline script) — the content, the checker, `firebase.json` and every criterion above survive that swap unchanged, because nothing in them depends on the framework. This is a decided fallback, not an open question; it costs the App Router and nothing else.
- **Copy volume.** Roughly forty keys × three languages is the largest single chunk of work and it lands in Phase 2, before either page is visible. Mitigation: Phase 2 writes keys in page order, so a shortfall truncates the bottom of the landing page rather than leaving a language half-done.
- **Saying the wrong thing about custody.** The landing sits next to a README that says "no server of ours". The custody strip must be adjacent to the self-host link every time it appears, so a reader never sees one claim without the other.
- **Reverse verification creeping back in.** "Enter the code we sent you" is the phrasing every sign-up flow trains us to write. The denylist in `tests/check_landing.py` is the guard, and it runs inside `tests/smoke.py`, so it cannot be forgotten.
- **A half-built portal at the stop.** Handled by the 13:45 tripwire and by building the four states one at a time rather than scaffolding all four and filling them in.

## Out of scope

- Firebase Auth, phone OTP, Firestore writes, the runner, and any real connection — [#4](https://github.com/mhmzdev/hisab-whatsapp/issues/4), [#7](https://github.com/mhmzdev/hisab-whatsapp/issues/7).
- Real nonce generation, expiry, and matching; the portal's `482913` is a display constant until #7.
- Quota display and enforcement ([#6](https://github.com/mhmzdev/hisab-whatsapp/issues/6)), `export-ledger` ([#8](https://github.com/mhmzdev/hisab-whatsapp/issues/8)), status/revoke against real state ([#5](https://github.com/mhmzdev/hisab-whatsapp/issues/5)).
- Any payment collection, provider, or checkout — presentation only, by decision.
- Ledger contents, balances, charts or a viewer in the browser.
- Deploying to a real Firebase project, `.firebaserc`, custom domains, analytics.
- A WhatsApp settings screenshot asset in the Connect state; the four steps are text today.
- Changes to `hisab/` — this slice adds no runtime Python.
