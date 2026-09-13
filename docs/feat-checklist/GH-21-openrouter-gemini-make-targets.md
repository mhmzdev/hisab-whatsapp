---
type: Checklist
title: GH-21-openrouter-gemini-make-targets — acceptance checklist
description: Review of dropping direct-OpenAI/agents_sdk, splitting the runner compose file into local/dev profiles, and restructuring make up/dev into the hosted Gemini/OpenRouter stacks (self-host renamed to make selfhost) against issue #21 and the exec plan.
tags: [checklist, hosted-hisab, runner, makefile]
timestamp: 2026-09-13T00:00:00Z
---

# GH-21-openrouter-gemini-make-targets — acceptance checklist   (11 proven · 0 manual · 0 failing)

Scope: 21 files on `GH-21-openrouter-gemini-make-targets` (branched from `origin/GH-7-connect-portal-user`,
tip 37fa8ca, since PR #20 had not merged to `main` at plan time): `hisab/{config.py,transcribe.py}`,
`runner/config.py`, `tests/smoke.py`, `config.example.yaml`, `.env.example`, `examples/config.{openrouter,gemini}.yaml`
(`examples/config.openai.yaml` deleted), `docker-compose.runner.yml`, new `docker-compose.runner.dev.yml`,
`runner/config.example.yaml`, new `examples/runner-config.openrouter.yaml`, `Makefile`, `.gitignore`,
`README.md`, `AGENTS.md`, `runner/README.md`, `landing/README.md`, docs INDEX. Reviewed on 2026-09-13
in the `GH-21` worktree.

- [x] No OpenAI-provider or `agents_sdk` residue; `examples/config.openai.yaml` gone — `grep -rniE 'provider == "openai"|OPENAI_API_KEY|agents_sdk|config\.openai' hisab runner tests examples config.example.yaml .env.example` → no output, exit 1; `test ! -f examples/config.openai.yaml` → OK.
- [x] `transcription.provider` accepts exactly `openrouter`/`gemini` and fails at config load with a one-line message otherwise, in both `hisab/config.py:load()` and `runner/config.py:load()` — `python3 tests/smoke.py` prints `config: rejects unknown transcription provider` and `runner config: rejects unknown transcription provider`.
- [x] The two runner compose profiles are syntactically valid — `docker compose -f docker-compose.runner.yml config -q` and the same `-f docker-compose.runner.dev.yml` layered on top, both exit 0.
- [x] The portal builds in both modes — `cd landing && NEXT_PUBLIC_USE_EMULATORS=1 npm run build && NEXT_PUBLIC_USE_EMULATORS=0 npm run build`, both succeed.
- [x] `make dev` fails fast naming the missing service-account file — ran `make dev` from repo root with no `./service-account.json`: one line, `./service-account.json missing — the dev Firebase project isn't provisioned yet`, exit 1.
- [x] `make up` alone brings up the emulators in the background, the runner on Gemini, and the portal at `http://localhost:3031/portal/`; `make down` stops all of it cleanly — ran end to end: `curl -sf http://localhost:3031/portal/ | grep -qi hisab` passed, `.emulators.pid` and ports 3031/9099/8080 all clear after `make down`.
- [x] The runner refuses to start when the self-host container is running (the guard lives in `runner-up`, so `make up`'s only path to starting the runner carries it) — brought the self-host container up directly, ran `make runner-up`: refused with `self-host container is running (docker-compose.yml) — same agent token risks HTTP 409 from two pollers. Run 'make selfhost-down' first.`, exit 1.
- [x] The self-host path is one command under its own name and README names it — `docker compose -f docker-compose.yml ps` showed it running after the self-host container was brought up; `README.md:60` and `AGENTS.md`'s Container row both name `make selfhost`.
- [x] `check_endpoint` passes for both runner profiles with real keys — Gemini (`runner/config.yaml`) is `ALL PASS`. OpenRouter (`runner/config-dev.yaml`) initially failed 3/6 with `HTTP 401 API key expired` (reproduced identically against the pre-existing, untouched root `config-dev.yaml`, confirming an expired sponsor key, not a wiring bug); the owner rotated `OPENROUTER_API_KEY` mid-review, the worktree's gitignored `.env` was updated with the new value, and a re-run is `ALL PASS`.
- [x] Docs describe the two stacks and their targets — read `AGENTS.md`, `runner/README.md`, `landing/README.md`, `README.md` back; all four now describe `make up`/`make dev`/`make selfhost`/`make selfhost-dev` correctly with no stale reference to the old meanings.
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`.

## Conventions

- **Surface.** Six tools unchanged; no code path here is model- or WhatsApp-facing — this is provider config, compose files and Make targets only.
- **Writes / transport.** No ledger, store or transport code touched.
- **Language.** No new user-facing (WhatsApp) string; nothing to add to `i18n.py`. Makefile echoes and config-load error messages are operator/CLI text, outside `i18n.py`'s scope by the same logic as every other `make` target's `##` help text and fail-fast message in this repo.
- **Conventions the dashboard reads.** Untouched.
- **Privacy.** All gitignored local copies this work needed (`config.yaml`, `config-dev.yaml`, `runner/config.yaml`, new `runner/config-dev.yaml`) stay gitignored — confirmed with `git check-ignore -v` on all four plus `.env`/`service-account.json`. No personal path, token or key appears in the diff or the new plan/checklist docs (`git diff | grep -i hamza` and the same on the new files: no output).
- **Tests.** Both new validation units exercised in `tests/smoke.py`; the plan also caught and fixed a pre-existing fixture (`tests/smoke.py:266` used `"transcription": {"provider": "fake-provider"}`, which the new `hisab.config.load` check would have broken via `write_tenant_config` → `hisab_load`) rather than leaving it to fail. No `setup.py` change, so the sample ledger doesn't need regenerating.
- **Docs.** `README.md`, `AGENTS.md`, `runner/README.md`, `landing/README.md`, `config.example.yaml` all updated. The lead is landing a parallel GH-5 PR touching `README.md:71`'s paragraph further, the Makefile's `runner-down-v` help line, `runner/README.md`'s lifecycle table/Layout list, and `AGENTS.md`'s runner/ repo-map line — verified none of those exact spots are touched by this diff, so the two branches should rebase cleanly regardless of merge order.

## Findings

FINDING-01 · Minor · `docker-compose.runner.yml:10` (fixed) — the base file's own header comment said
the dev profile "clears FIRESTORE_EMULATOR_HOST"; the actual clearing happens in `Makefile`'s `dev`
target via `env -u FIRESTORE_EMULATOR_HOST` (added specifically because an empty-string value in the
compose file itself would not have worked — `google-cloud-firestore` checks presence, not
truthiness). Harmless (didn't affect behavior, just described the mechanism one file over from where
it actually lives) — reworded to name `env -u FIRESTORE_EMULATOR_HOST` directly; re-verified both
compose profiles with `docker compose config -q` and `python3 tests/smoke.py` (`ALL OK`) after.

Note for the record, not a finding against this diff: a second `make up` run during this review hit
"port 3031 is in use by something else" — a firebase emulator started from the main checkout by a
concurrent session on the same machine was holding the port. The first `make up`/`make down` run
earlier in this review, with the ports genuinely free, completed and tore down cleanly — that is the
result recorded above.
