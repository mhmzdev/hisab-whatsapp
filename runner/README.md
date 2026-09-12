# Runner — hosted Hisab's Firestore reconciler

Turns a Firestore tenant document into one isolated `hisab.loop` worker process. Not a rewrite of
`hisab/` — it execs the existing entrypoint (`python -m hisab.loop --config <per-tenant path>`)
per tenant, with UID-scoped `vault/<uid>` and `data/<uid>` paths and the runner's own global
model/transcription config, never a tenant-supplied one. Design:
[GH-4](../docs/exec-plans/completed/GH-4-hosted-tenant-runner.md) (the reconciler) and
[GH-7](../docs/exec-plans/completed/GH-7-connect-portal-user.md) (the connection flow);
issues [#4](https://github.com/mhmzdev/hisab-whatsapp/issues/4) and
[#7](https://github.com/mhmzdev/hisab-whatsapp/issues/7).

## A tenant's life

| `status` | Written by | What runs |
|---|---|---|
| *(none)* | the portal creates `tenants/{uid}` with `agentName`, `keyCiphertext`, `nonce`, `nonceExpiresAt`, `createdAt` — and nothing else, `firestore.rules` rejects any other field from a client | nothing yet |
| `pending` | the runner, once `keyCiphertext` decrypts with `RUNNER_PRIVATE_KEY` (`reconcile.admission`) | a muted worker: records inbounds, sends the trilingual reminder at most once per 10 minutes, no ledger, no model call |
| `connected` | the runner, when that tenant's `messages.jsonl` holds an exact case-insensitive `verify <nonce>` sent before `nonceExpiresAt` (`verify.check_pending`, polled every 2 s by `main.tick`); `creatorId` and `connectedAt` are written with it | the worker restarts unmuted (`pending` is in the state hash), sends the welcome once (`welcomed.json` marker), and the normal setup conversation follows |
| `error` | the runner, when a worker exits with `hisab.wa.AUTH_EXIT_CODE` (WhatsApp rejected the token: 401/190 or 400/100); `lastError: "auth"` is a *code* the portal renders in three languages, `lastErrorKey` fingerprints the ciphertext that failed | nothing — no restart loop. Pasting a different key in the portal re-admits the tenant |
| `revoked` | [#5](https://github.com/mhmzdev/hisab-whatsapp/issues/5) | nothing |

The runner is the only thing that talks to Firestore; the worker never learns what Firebase is. The
runner never talks to WhatsApp; every send goes through the worker's `hisab/wa.py` and its rate limiter.
The monthly model-call allowance ([#6](https://github.com/mhmzdev/hisab-whatsapp/issues/6)) and
`export-ledger` ([#8](https://github.com/mhmzdev/hisab-whatsapp/issues/8)) live in the worker.

## One-time setup

```
cp runner/config.example.yaml runner/config.yaml     # paths resolve relative to runner/, so ../runner-data
python3 -m runner.keygen                              # public key → landing/.env.local; private key → .env
```

`RUNNER_PRIVATE_KEY` is a secret exactly like `WHATSAPP_TOKEN`/`OPENROUTER_API_KEY` — `.env`,
never committed. Rotation for this MVP is manual: regenerate, redeploy, and any tenant whose
ciphertext was sealed under the retired key must resubmit it through the portal.

## The full local loop

Three processes, one command each, from the repo root:

| Step | Command | Notes |
|---|---|---|
| 1. Build the portal | `make landing` | reads `landing/.env.local` (copy `landing/.env.example`; set `NEXT_PUBLIC_RUNNER_PUBLIC_KEY`) |
| 2. Emulators | `make emulators` | auth 9099, firestore 8080, hosting 3031 serving `landing/out`; **phone OTPs print in this terminal** |
| 3. Runner | `make runner-up` | Docker, `FIRESTORE_EMULATOR_HOST=host.docker.internal:8080`; `make runner-logs` / `make runner-down` / `make runner-down-v` |
| 4. Portal | http://localhost:3031/portal/ | sign in with any number (the emulator never sends SMS), paste a **demo** agent's key, send `verify <nonce>` from the phone that created that agent |

Then `make rules-test` for the rules as an attacker, `python3 tests/smoke.py` for everything else.

## Two profiles — neither a production project or a payment provider

| Profile | Firestore | Credentials | Command |
|---|---|---|---|
| `local` | Firebase Emulator Suite, any `demo-*` project id | none — the client uses anonymous credentials (firebase-admin itself refuses to start without ADC, so `firestore_listener._client` builds the underlying client directly) | `make emulators` then `make runner-up` |
| `dev` | An existing dedicated Firebase project — never production. Phone auth needs the Blaze plan | a gitignored service-account JSON | the commented `dev` block in `docker-compose.runner.yml` |

## Layout

- `crypto.py` — sealed-box decrypt/encrypt/keygen (PyNaCl `SealedBox` = libsodium `crypto_box_seal`, the same primitive `landing/app/portal/crypto.js` uses; `tests/smoke.py` proves the JS→Python round trip).
- `config.py` — `runner/config.yaml` + `RUNNER_PRIVATE_KEY`; resolves `vault_root`/`data_root`/`tenants_dir` to absolute paths relative to `runner/`.
- `tenant_config.py` — UID-scoped per-tenant config: always the runner's global model/transcription, `quota.monthly_limit`, `pending`, `hosted: true`.
- `verify.py` — `check_pending`/`poll_pending`: the nonce match, pure and file-based.
- `reconcile.py` — the whole tenant collection → desired worker state, idempotent by content hash; `admission` and `on_worker_exit` are the two status transitions it owns.
- `errors.py` — the `lastError` codes; `tests/check_landing.py` requires a portal string for each.
- `workers.py` — `WorkerManager`: start/stop/restart/reap a tenant's `hisab.loop` subprocess.
- `firestore_listener.py` / `main.py` — the one snapshot listener, the one write path, and the 2-second tick.

`firebase-admin` lives in `runner/requirements.txt`, not the base `requirements.txt` — a
self-host Docker build never pulls it. `pynacl` is the one addition to the base
`requirements.txt`, needed so the crypto contract is unit-testable without network.
