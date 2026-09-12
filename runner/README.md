# Runner — hosted Hisab's Firestore reconciler

Turns a Firestore tenant document into one isolated `hisab.loop` worker process. Not a rewrite of
`hisab/` — it execs the existing entrypoint (`python -m hisab.loop --config <per-tenant path>`)
per tenant, with UID-scoped `vault/<uid>` and `data/<uid>` paths and the runner's own global
model/transcription config, never a tenant-supplied one. See
[docs/exec-plans/completed/GH-4-hosted-tenant-runner.md](../docs/exec-plans/completed/GH-4-hosted-tenant-runner.md)
for the design, and [issue #4](https://github.com/mhmzdev/hisab-whatsapp/issues/4).

This is infrastructure only: nonce verification and revoke are separate work
([#7](https://github.com/mhmzdev/hisab-whatsapp/issues/7),
[#5](https://github.com/mhmzdev/hisab-whatsapp/issues/5)). A tenant with `status: pending` runs a
worker that receives inbound WhatsApp messages but sends nothing at all — no ledger, no reply —
until later work flips it to `connected`. The monthly model-call allowance
([#6](https://github.com/mhmzdev/hisab-whatsapp/issues/6)) and `export-ledger`
([#8](https://github.com/mhmzdev/hisab-whatsapp/issues/8)) are already in: see `quota` below and
`hisab/loop.py`'s `_agent`/`_export_ledger`.

## One-time setup

```
cp runner/config.example.yaml runner/config.yaml
python -m runner.keygen   # prints a public key (goes in the portal build) and RUNNER_PRIVATE_KEY (goes in .env)
```

`RUNNER_PRIVATE_KEY` is a secret exactly like `WHATSAPP_TOKEN`/`OPENROUTER_API_KEY` — `.env`,
never committed. Rotation for this MVP is manual: regenerate, redeploy, and any tenant whose
ciphertext was sealed under the retired key must resubmit it through the portal.

## Two profiles — neither a production project or a payment provider

| Profile | Firestore | Credentials | Command |
|---|---|---|---|
| `local` | Firebase Emulator Suite, any `demo-*` project id | none — the emulator needs no real credentials | `firebase emulators:start --only firestore,auth` (host), then `FIRESTORE_EMULATOR_HOST=localhost:8080 python -m runner.main` |
| `dev` | An existing dedicated Firebase project — never production | a gitignored service-account JSON | `GOOGLE_APPLICATION_CREDENTIALS=<path> python -m runner.main` |

Docker: `docker compose -f docker-compose.runner.yml up -d --build` (see the commented `dev`
block in that file for the service-account mount). Neither profile enables real subscription
payments — that stays out of scope for the whole hosted MVP (spec 001).

## Layout

- `crypto.py` — sealed-box decrypt/encrypt/keygen.
- `config.py` — `runner/config.yaml` + `RUNNER_PRIVATE_KEY`; resolves `vault_root`/`data_root`/`tenants_dir` to absolute paths.
- `tenant_config.py` — UID-scoped per-tenant config, always the runner's global model/transcription
  and `quota.monthly_limit` (`config.yaml`'s `quota` block — every tenant shares the same allowance
  for now). The worker itself (`hisab/loop.py`'s `_agent`, `hisab/store.py`'s `usage()`) counts
  model calls and enforces the limit; the runner only sets the number.
- `workers.py` — `WorkerManager`: start/stop/restart a tenant's `hisab.loop` subprocess.
- `reconcile.py` — the whole tenant collection → desired worker state, idempotent by content hash.
- `firestore_listener.py` / `main.py` — the one Firestore snapshot listener and the process entrypoint.

`firebase-admin` lives in `runner/requirements.txt`, not the base `requirements.txt` — a
self-host Docker build never pulls it. `pynacl` is the one addition to the base
`requirements.txt`, needed so the crypto contract is unit-testable without network.
