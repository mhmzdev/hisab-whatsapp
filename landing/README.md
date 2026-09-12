# Hosted Hisab — landing + portal

A static Next.js export: the marketing landing page and the portal that connects a signed-in phone
to one WhatsApp agent. The portal talks to Firebase directly (phone auth, one Firestore document);
the runner does the rest — see [runner/README.md](../runner/README.md) for the whole loop.

## Commands

From the repo root:

| Command | What |
|---|---|
| `make landing` | `npm install && npm run build` — writes the static export to `landing/out/` |
| `make landing-check` | Runs `tests/check_landing.py` — three-language completeness, verification direction, no payment collection, `firebase.json` shape, a portal string per runner `lastError` code |
| `make emulators` | Serves `landing/out` at http://localhost:3031 through the Hosting emulator, with Auth and Firestore beside it |
| `make up` | Runs the self-host worker and serves `landing/out` at `http://localhost:3030` (no Firebase; the portal will not sign in) |

`python3 tests/smoke.py` runs the landing check automatically once `landing/content/strings.json` exists.

## Configuration

`landing/.env.local` (gitignored; copy `landing/.env.example`) is baked in at build time. None of it is
secret: `NEXT_PUBLIC_FIREBASE_*` is the public web config, `NEXT_PUBLIC_RUNNER_PUBLIC_KEY` is the public
half of `python3 -m runner.keygen`, and `NEXT_PUBLIC_USE_EMULATORS=1` points auth and Firestore at the
local Emulator Suite. Rebuild after changing any of them.

## The `strings.json` contract

Every fixed user-facing string lives in `landing/content/strings.json`, one dict, key → `{en, ur, roman}`. A string ships in all three languages or it does not ship — `tests/check_landing.py` enforces this. Urdu is Urdu script; Roman Urdu is Latin, in the same register as the agent's own replies (see `hisab/i18n.py`), not translated marketing English.

Any key whose name contains `verify_instruction` must contain the literal word `verify` and the `{nonce}` placeholder in every language — the portal always tells the user to *send* a code to their agent, never that a code was *sent to* them. Every code in `runner/errors.py` needs a `portal_error_<code>` key: the runner stores codes, the portal renders words.

## How the portal decides what to show

`app/portal/page.jsx` derives the screen from two facts — is someone signed in, and what their own
`tenants/{uid}` document says — never from a URL parameter:

| Signed in | Document | Screen |
|---|---|---|
| no | — | `signin` → `signin-code` (Firebase phone auth, invisible reCAPTCHA; the Auth emulator prints the OTP instead of texting) |
| yes | none, or `status: error` (with the `lastError` rendered) | `connect` — seals the key with `libsodium-wrappers` (`crypto_box_seal`) and writes the five client fields, nothing else |
| yes | no status / `pending` | `check` — the live nonce, Copy, New code, expiry |
| yes | `connected` | `connected` — agent name and date are live; activity, entries, language, plan and the quota bar stay mock until [#5](https://github.com/mhmzdev/hisab-whatsapp/issues/5) |
| yes | `revoked` | `revoked` (Revoke itself is #5) |

`firestore.rules` is what makes this trustworthy: a client can never write `status` or `creatorId`,
so "Connected" on this page always means the runner matched the code. `make rules-test` proves it.
