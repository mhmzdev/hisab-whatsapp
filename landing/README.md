# Hosted Hisab — landing + portal

A static Next.js export: the marketing landing page and the portal that connects a signed-in phone
to one WhatsApp agent. The portal talks to Firebase directly (phone auth, one Firestore document);
the runner does the rest — see [runner/README.md](../runner/README.md) for the whole loop.

## Commands

From the repo root:

| Command | What |
|---|---|
| `make landing` | `npm install && npm run build` — writes the static export to `landing/out/`, hosted sign-up off. `NEXT_PUBLIC_HOSTED=1` to open it, `NEXT_PUBLIC_USE_EMULATORS=0` for the dev/remote profile |
| `make landing-check` | Runs `tests/check_landing.py` — no Firebase on the landing page, the pre-paint theme script, two-language completeness (exactly `en` and `ur`), verification direction, no payment collection, `firebase.json` shape, a portal string per runner `lastError` code |
| `make emulators` | Serves `landing/out` at http://localhost:3031 through the Hosting emulator, with Auth and Firestore beside it (foreground; `make up` is the background hosted stack) |
| `make up` | The whole hosted local stack: emulators in the background, the runner on Gemini, the portal at http://localhost:3031/portal/ |
| `make dev` | The runner on OpenRouter against the dedicated dev Firebase project, portal built with emulators off |
| `make selfhost` | Runs the self-host worker and serves `landing/out` at `http://localhost:3030` (no Firebase; the portal will not sign in) |

`python3 tests/smoke.py` runs the landing check automatically once `landing/content/strings.json` exists.

## Configuration

`landing/.env.local` (gitignored; copy `landing/.env.example`) is baked in at build time. None of it is
secret: `NEXT_PUBLIC_FIREBASE_*` is the public web config, `NEXT_PUBLIC_RUNNER_PUBLIC_KEY` is the public
half of `python3 -m runner.keygen`, and `NEXT_PUBLIC_USE_EMULATORS=1` points auth and Firestore at the
local Emulator Suite. Rebuild after changing any of them.

## Hosted sign-up is a build flag

`NEXT_PUBLIC_HOSTED=1` opens it; anything else is the public build, and that is the default. `landing/app/hosted.js` is the one place it is read.

| | `NEXT_PUBLIC_HOSTED=1` | off (default) |
|---|---|---|
| Hero and header CTA | Get started → `/portal/` (Go to portal when signed in) | Run it yourself → the README's self-host steps on GitHub |
| Setup section | as written | a Coming soon note above the three steps |
| Pricing | Get started, and the JazzCash/Easypaisa note | a Coming soon badge, Run it yourself, and "planned price, nothing to pay today" |
| `/portal/` | sign-in and the tenant screens | a coming-soon card; `firebase()` is never called |

`make up` and `make dev` build with it on; `make landing` and `make selfhost` build it off. A command-line value wins over `landing/.env.local`. `tests/check_landing.py` fails if a page stops importing the gate.

## The `strings.json` contract

Every fixed user-facing string lives in `landing/content/strings.json`, one dict, key → `{en, ur}`. A string ships in exactly those two languages or it does not ship — `tests/check_landing.py` fails on a missing one and on any other language key. Urdu is Urdu script. The page has no Roman Urdu: that is how people text the ledger, not how they read a landing page, and the agent follows the same rule: its fixed strings are `en` and `ur`, and the model answers a user who writes Roman Urdu in Roman Urdu.

Any key whose name contains `verify_instruction` must contain the literal word `verify` and the `{nonce}` placeholder in every language — the portal always tells the user to *send* a code to their agent, never that a code was *sent to* them. Every portal code in `hisab/errors.py` needs a `portal_error_<code>` key: the runner stores codes, the portal renders words.

## Fonts

`layout.jsx` loads Inter, IBM Plex Mono and Noto Nastaliq Urdu through `next/font/google`. The files are downloaded when the page is built and served from `landing/out/`, so a visitor never contacts Google, but `make landing` (and `npm run build`) needs network access.

The Urdu page reads in Jameel Noori Nastaleeq, `landing/assets/noori-nastaleeq.woff2`, loaded with `next/font/local`. It is about 4.7 MB, so it is never preloaded and only elements under `lang="ur"` use it (the `--urdu-face` token in `globals.css`); on the English page the few Urdu words (the header's حساب, the shop column, the footer watermark) stay in Noto and the file is never fetched. The woff2 is a subset of the source TTF (Urdu, Arabic presentation forms, basic Latin), which is not committed:

```
pip install fonttools brotli
pyftsubset noori.ttf --unicodes="U+0020-007E,U+00A0,U+060C-06FF,U+200C-200F,U+2013-2014,U+2018-201D,U+2026,U+FB50-FDFF,U+FE70-FEFF" \
  --layout-features='*' --no-hinting --flavor=woff2 --output-file=landing/assets/noori-nastaleeq.woff2
```

The logo mark comes from `landing/assets/` in both colours; `BrandMark.jsx` shows the one for the resolved theme.

## Theme and the signed-in hint

Two per-browser `localStorage` keys, nothing on a server:

| Key | Values | Written by | Read by |
|---|---|---|---|
| `hisab-theme` | `system` · `light` · `dark` | `ThemeToggle.jsx` (the header, both routes) | `theme.js` — `THEME_SCRIPT` runs inline in `<head>` and sets `<html data-theme="light\|dark">` before first paint, resolving `system` through `prefers-color-scheme`; the dark tokens in `globals.css` hang off `[data-theme="dark"]` |
| `hisab-signed-in` | `1` or absent | the portal's `onAuthStateChanged` (set on a user, removed on sign-out) | `page.jsx` — hero and pricing buttons read "Go to portal" instead of "Get started" |

The landing page never imports Firebase, libsodium or `./portal/` code; a signed-out visitor downloads none of it. `tests/check_landing.py` enforces that and the presence of the pre-paint script. A session that expires without a portal visit leaves the hint behind: the button says "Go to portal" and the portal shows sign-in.

## How the portal decides what to show

`app/portal/page.jsx` derives the screen from two facts — is someone signed in, and what their own
`tenants/{uid}` document says — never from a URL parameter:

| Signed in | Document | Screen |
|---|---|---|
| no | — | `signin` → `signin-code` (Firebase phone auth, invisible reCAPTCHA; the Auth emulator prints the OTP instead of texting) |
| yes | none, or `status: error` (with the `lastError` rendered) | `connect` — seals the key with `libsodium-wrappers` (`crypto_box_seal`) and writes the five client fields, nothing else |
| yes | no status / `pending` | `check` — the live nonce, Copy, New code, expiry |
| yes | `connected` | `connected` — every row is live from the document: agent name, connected since, last activity (`lastSeenAt`), entries this month, language, AI calls this month (`usedThisMonth` / `quotaLimit`); the runner computes them from the worker's files (`runner/activity.py`). "Revoke key" writes `revokeRequestedAt`, the one client field that starts a transition; the card shows "Revoking…" until the runner writes `revoked` |
| yes | `revoked` | `revoked` — the key is gone, the ledger is retained 30 days. "Connect an agent" shows the `connect` form over the revoked document; a new key re-admits the tenant as `pending` and setup starts from zero |

`firestore.rules` is what makes this trustworthy: a client can never write `status` or `creatorId`,
so "Connected" on this page always means the runner matched the code. `make rules-test` proves it.
