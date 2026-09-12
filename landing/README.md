# Hosted Hisab — landing + portal shell

A static Next.js export: the marketing landing page and a portal shell that renders the four connection states (`connect`, `check`, `connected`, `revoked`) as mocks. No backend — see [issue #7](https://github.com/mhmzdev/hisab-whatsapp/issues/7) for the real connection flow.

## Commands

From the repo root:

| Command | What |
|---|---|
| `make landing` | `npm install && npm run build` — writes the static export to `landing/out/` |
| `make landing-check` | Runs `tests/check_landing.py` — three-language completeness, verification direction, no payment collection, `firebase.json` shape |
| `make landing-serve` | Serves `landing/out` at `http://localhost:5000` with Python's http server, the same layout Firebase Hosting serves |

`python3 tests/smoke.py` runs the landing check automatically once `landing/content/strings.json` exists.

## The `strings.json` contract

Every fixed user-facing string lives in `landing/content/strings.json`, one dict, key → `{en, ur, roman}`. A string ships in all three languages or it does not ship — `tests/check_landing.py` enforces this. Urdu is Urdu script; Roman Urdu is Latin, in the same register as the agent's own replies (see `hisab/i18n.py`), not translated marketing English.

Any key whose name contains `verify_instruction` must contain the literal word `verify` and the `{nonce}` placeholder in every language — the portal always tells the user to *send* a code to their agent, never that a code was *sent to* them.

## Portal shell, not portal

`/portal/?state=connect|check|connected|revoked` renders one of four states from `landing/content/mock.js`. There is no real nonce, no Firestore, no runner behind it — that is issues [#4](https://github.com/mhmzdev/hisab-whatsapp/issues/4)–[#8](https://github.com/mhmzdev/hisab-whatsapp/issues/8). The `data-demo-only` block at the foot of the portal card is the state switcher; it is not part of the product and is removed by that one selector once a real connection flow lands.
