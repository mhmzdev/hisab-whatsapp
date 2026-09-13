---
type: Checklist
title: GH-7-connect-portal-user — acceptance checklist
description: Review of the portal-to-agent connection (phone auth, sealed key, nonce verification, pending reminder, welcome, auth-failure exit) against issue #7 and the exec plan.
tags: [checklist, hosted-hisab, portal, runner]
timestamp: 2026-09-13T00:00:00Z
---

# GH-7-connect-portal-user — acceptance checklist   (12 proven · 1 manual · 0 failing)

Scope: one commit on `GH-7-connect-portal-user` (37 files): `firestore.rules`, `tests/rules/`, `landing/app/portal/{page.jsx,firebase.js,crypto.js}`, `landing/content/strings.json`, `runner/{verify.py,errors.py,reconcile.py,firestore_listener.py,main.py,workers.py}`, `hisab/{loop.py,store.py,wa.py,i18n.py,config.py}`, `Makefile`, `docker-compose.runner.yml`, `tests/smoke.py`, docs. Reviewed on 2026-09-13 in the main checkout before merge.

- [x] A signed-in client cannot write `status` or `creatorId`, cannot read another uid's document, can write its own `agentName`/`keyCiphertext` and refresh the nonce without disturbing runner fields — `make rules-test` → 5/5 pass against a throwaway Firestore emulator (2026-09-13).
- [x] A ciphertext sealed in the browser's JS decrypts in Python to the identical string — `python3 tests/smoke.py` → `runner: JS (libsodium) -> Python (PyNaCl) sealed-box round trip ok` (needs `landing/node_modules`; skipped with a note otherwise).
- [x] The runner assigns `pending` only to a decryptable `keyCiphertext` with no status — `python3 tests/smoke.py` → `runner: reconcile ok`.
- [x] Exact case-insensitive `verify <nonce>` flips a pending tenant to `connected` with the creator id; a bare number, a wrong nonce and an expired nonce do not — `python3 tests/smoke.py` → `runner: verify ok`.
- [x] Tenant A's nonce never verifies tenant B — same test.
- [x] A pending worker sends the reminder at most once per 10 minutes, never for a verify-shaped message, posts nothing and calls no model — `python3 tests/smoke.py` → `runner: pending mute ok` / reminder assertions.
- [x] The welcome is sent exactly once across a simulated restart; `welcome` and `pending_reminder` exist in `en`/`ur`/`roman` — `python3 tests/smoke.py`.
- [x] The worker exits on 401/`190` and invalid-token 400/`100`, retries on 503 and connection errors — `python3 tests/smoke.py`.
- [x] The runner writes `lastError: auth` on that exit — `python3 tests/smoke.py`.
- [x] Every runner `lastError` code has a `portal_error_<code>` string in three languages; verification direction unchanged — `python3 tests/check_landing.py` (run inside smoke) → `landing: ok`.
- [x] `landing/` builds to a static export with both routes — `cd landing && npm run build` (built 2026-09-12 by the branch author; `landing/out` served on 3031 in the manual run).
- [?] End to end against the demo agent — run once by the branch author on 2026-09-12 (emulator OTP sign-in, browser-sealed key opened by the runner, mixed-case `Verify <nonce>` connected within 2 s, welcome once, setup on the phone). Not re-run at review time; the PR Test Plan carries it.
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`.

## Conventions

- **Surface.** Six tools unchanged; `verify` is matched by the runner from the message log and never reaches the model loop. No new network surface in `hisab/` — the Firestore client stays in `runner/`.
- **Writes / transport.** No ledger code touched. Dedup-by-id and offset-after-batch untouched; the pending path records ids like any other message. The reminder goes through `wa.send`, so the #17 limiter covers it.
- **Language.** `welcome` and `pending_reminder` are trilingual under all three keys by design (no language is chosen before setup). Portal strings gained nine keys in `en`/`ur`/`roman`.
- **Privacy.** `.env.example` and `landing/.env.example` carry names only. Fixtures use `demo-hisab` and fake uids. No project id, token or phone number in the diff.
- **Docs.** `runner/README.md`, `landing/README.md`, `AGENTS.md`, `docker-compose.runner.yml` comments updated on the branch. Plan moved to `docs/exec-plans/completed/` at merge.

## Findings

None new at review time. The branch's own Phase 5 recorded and fixed one: `runner/config.example.yaml` paths resolved to `runner/runner-data`, outside the compose mount — now `../runner-data`.
