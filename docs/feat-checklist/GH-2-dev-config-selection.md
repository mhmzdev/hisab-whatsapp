---
type: Checklist
title: GH-2-dev-config-selection — acceptance checklist
description: Review of the HISAB_CONFIG Docker/Makefile config selection against issue #2 and the exec plan.
tags: [checklist, hosted-hisab, config]
timestamp: 2026-09-12T00:00:00Z
---

# GH-2-dev-config-selection — acceptance checklist   (7 proven · 0 manual · 0 failing)

Scope: `docker-compose.yml`, `Makefile`, `AGENTS.md`, `docs/exec-plans/{INDEX.md,completed/GH-2-dev-config-selection.md}`, new gitignored `config-dev.yaml` — 5 tracked files touched on branch `GH-2-dev-config-selection`, none committed yet.

- [x] `docker compose` mounts the config selected by `HISAB_CONFIG`, defaulting to `./config.yaml`, and never mounts a mutable path — `docker compose config` resolves the default mount to `<repo>/config.yaml`; with `HISAB_CONFIG=./config-dev.yaml` set, it resolves to `<repo>/config-dev.yaml`. Re-run fresh this session, both `source:` lines matched.
- [x] `make up`, `make stdin`, and `make demo` retain the Gemini local configuration; `make dev` selects `./config-dev.yaml` and `./sample-vault` unless overridden — `make -n up` prints `HISAB_VAULT=./vault docker compose up -d --build` with no `HISAB_CONFIG` (falls back to Gemini `config.yaml`); `make -n dev` prints both `HISAB_VAULT=./sample-vault` and `HISAB_CONFIG=./config-dev.yaml`. `make stdin` runs `python3 -m hisab.loop --stdin` directly (untouched, no Docker); `make demo` runs `tests/demo_terminal.sh`, which derives `config-sample.yaml` from `config.yaml` via `sed` (untouched by this change, so it stays Gemini).
- [x] `config-dev.yaml` uses `openai/gpt-4.1-mini` and `openai/gpt-4o-transcribe`, remains gitignored — `git check-ignore -q config-dev.yaml` exits 0 (matches the pre-existing `config-*.yaml` rule, no `.gitignore` change needed); file contains `model.id: openai/gpt-4.1-mini` and `transcription.model: openai/gpt-4o-transcribe`.
- [x] `config-dev.yaml` validates with `python3 tests/check_endpoint.py --config config-dev.yaml` reporting `ALL PASS` — ran live against `OPENROUTER_API_KEY` this session: key valid, `openai/gpt-4.1-mini` listed and tool-capable, a tool-call probe and a transcription probe both returned correct results. `ALL PASS`.
- [x] `config.yaml` is byte-for-byte unchanged (Gemini stays the rollback) — `git diff --quiet -- config.yaml` exits 0.
- [x] Help text and Docker guidance document `HISAB_CONFIG`, `HISAB_VAULT`, and Gemini as the rollback — `AGENTS.md` now names `HISAB_CONFIG` in the Commands table (a new "validate the sponsor config" row), the Docker section's intro sentence, the Docker table (a new sponsor-demo row), and the rules-for-agents `config.yaml` bullet, which states the selection never overwrites `config.yaml` and that it stays the Gemini rollback.
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`, re-run fresh this session.

## Conventions

- **Surface.** Zero changes under `hisab/`; six tools untouched. This is `docker-compose.yml`, `Makefile`, `AGENTS.md`, and one new gitignored config file only, as the plan scoped.
- **Writes / transport / language / dashboard conventions.** N/A — no ledger, transport, or user-facing-string code touched.
- **Privacy.** `config-dev.yaml` holds no key or personal endpoint (`api_key_env: null` falls back to the `OPENROUTER_API_KEY` env var already in `.env`, never embedded); it stays untracked (`git status --short` shows it as `??`, not staged). No path, token, or name from this machine entered `AGENTS.md` or the plan. `.env`, `config.yaml`, and `vault/` were not touched.
- **Tests.** No new `hisab/` unit exists to add to `tests/smoke.py` — this slice is pure configuration/plumbing (Docker mount + Makefile variables + docs), matching the plan's own testing decisions (shell `verify:` commands per criterion, `tests/smoke.py` as the umbrella check). Consistent with the "don't touch `hisab/` runtime behavior" constraint the plan set for itself.
- **Docs.** `AGENTS.md` updated per the plan. `README.md`'s existing `docker compose up -d` / `cp config.example.yaml config.yaml` lines remain true (untouched, no HISAB_CONFIG-specific claim there) and needed no change. `config.example.yaml` needed no change — `HISAB_CONFIG` is a new env var, not a new config-file key.

## Findings

None.
