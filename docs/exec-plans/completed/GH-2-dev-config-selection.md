---
slug: GH-2-dev-config-selection
issue: 2
status: completed
open_questions: none
---

# chore: Keep local Gemini while `make dev` uses the OpenRouter sponsor config          ✅ COMPLETED — 2026-09-12

## Problem

[#2](https://github.com/mhmzdev/hisab-whatsapp/issues/2) — normal local work (`make up`, `make stdin`, `make demo`) must stay on the existing Gemini `config.yaml`, while `make dev` (the sponsor demo, against `./sample-vault`) must run the OpenRouter config named in the [hosted-portal brainstorm](../../brainstorm/hosted-portal.md)'s "Model configuration split (locked)" paragraph and [spec 001](../../specs/001-hosted-portal.md)'s "Environments" decision: `openai/gpt-4.1-mini` plus `openai/gpt-4o-transcribe`. The selected file must reach Docker without ever overwriting `config.yaml`. Blocked by: nothing.

**Lifecycle stages skipped, per `AGENTS.md`'s track B:** no `/grill-me` — the WHAT is already locked in the brainstorm and spec, and this issue only restates it. No `/to-spec` or `/file-an-issue` — the issue already exists and is scoped. This is small, low-risk configuration plumbing that touches no `hisab/` runtime code, so it goes straight from the existing issue to this plan.

## Approach

Two things are true today and stay true:

- `hisab/config.py:24` (`load()`) already resolves `Path(path or os.environ.get("HISAB_CONFIG", "config.yaml"))` — this is the **Python-side** selector, already used directly (no Docker) by `tests/demo_terminal.sh:8` (`HISAB_CONFIG=config-sample.yaml python3 -m hisab.loop --stdin`) and `tests/bakeoff.sh:18`, and already accepted as `--config` by `tests/check_endpoint.py`.
- `docker-compose.yml:6` hard-mounts `./config.yaml:/app/config.yaml:ro` — there is no **Docker-side** selector at all. This is the actual gap #2 asks to close.

The fix reuses the exact pattern already proven one line below it for the ledger: `docker-compose.yml:7` already does `${HISAB_VAULT:-./vault}:/app/vault`. Line 6 gets the same treatment: `${HISAB_CONFIG:-./config.yaml}:/app/config.yaml:ro`. This keeps one env var name, `HISAB_CONFIG`, meaning "path to the config file, relative to wherever the command that reads it is invoked from" in both its existing Python-direct use and its new Docker-compose use — repo root in every documented invocation (`make dev`, `make up`, `tests/demo_terminal.sh`, `tests/bakeoff.sh` all `cd` to or run from repo root), so there is no divergent resolution behavior to reconcile, only two consumers of the same convention. Nothing about `hisab/config.py` changes.

Because the compose mount now defaults to `./config.yaml` when `HISAB_CONFIG` is unset, `make up`, `make stdin` (which never touches Docker) and `make demo` (which derives `config-sample.yaml` from `config.yaml` via `sed` at `tests/demo_terminal.sh:6` — already Gemini today and untouched by this plan) all keep working exactly as before with zero Makefile changes. Only `make dev` needs a new line: set `HISAB_CONFIG ?= ./config-dev.yaml` alongside its existing `HISAB_VAULT ?= ./sample-vault`, and pass both through to `docker compose up -d --build`, mirroring the existing single-var pass-through at `Makefile:14`.

`config-dev.yaml` is a new file, modeled on `examples/config.openrouter.yaml` (same `ledger`/`memory`/`whatsapp`/`state` blocks, `model.base_url: null` and `model.api_key_env: null` so it falls back to `OPENROUTER_API_KEY`, already present in `.env`) but with `transcription.model: openai/gpt-4o-transcribe` instead of that example's `whisper-1`, per the issue's exact requirement. It is never committed: `.gitignore`'s existing `config-*.yaml` line already covers it, so no `.gitignore` change is needed — this plan only adds a criterion that proves the coverage.

Nothing in `hisab/` changes. This is `docker-compose.yml`, `Makefile`, one new gitignored config file, and documentation.

## Success criteria

- [x] `docker compose` mounts the config from `HISAB_CONFIG`, defaulting to `./config.yaml`, and never mounts a mutable path that could let a container write back into the tracked file — `verify: docker compose config | grep -q "source: $(pwd)/config.yaml" && HISAB_CONFIG=./config-dev.yaml docker compose config | grep -q "source: $(pwd)/config-dev.yaml"`
- [x] `make up` and `make dev` still pass `HISAB_VAULT` through unchanged, and `make dev` additionally defaults `HISAB_CONFIG` to `./config-dev.yaml` while `make up` leaves it unset (so it falls back to `./config.yaml`) — `verify: make -n up | grep -q 'HISAB_VAULT=./vault' && ! make -n up | grep -q 'HISAB_CONFIG' && make -n dev | grep -q 'HISAB_VAULT=./sample-vault' && make -n dev | grep -q 'HISAB_CONFIG=./config-dev.yaml'`
- [x] `config-dev.yaml` exists, is gitignored, and names exactly `openai/gpt-4.1-mini` for `model.id` and `openai/gpt-4o-transcribe` for `transcription.model` — `verify: git check-ignore -q config-dev.yaml && grep -q 'id: openai/gpt-4.1-mini' config-dev.yaml && grep -q 'model: openai/gpt-4o-transcribe' config-dev.yaml`
- [x] `config.yaml` is byte-for-byte unchanged by this work (Gemini stays the rollback) — `verify: git diff --quiet -- config.yaml`
- [x] `config-dev.yaml` validates end to end against a live OpenRouter key — `verify: manual — python3 tests/check_endpoint.py --config config-dev.yaml, expect every line to print [PASS] and no [FAIL]` — ran clean, `ALL PASS` (key, model listing, tools support, tool-call probe, transcription probe)
- [x] `AGENTS.md` documents `HISAB_CONFIG` alongside `HISAB_VAULT` in the Docker table/rules, naming Gemini `config.yaml` as the rollback — `verify: grep -q HISAB_CONFIG AGENTS.md`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Compose selector and the dev config file
**Status:** Done — docker-compose.yml:6 now `${HISAB_CONFIG:-./config.yaml}`; config-dev.yaml created (openai/gpt-4.1-mini, openai/gpt-4o-transcribe); default and override mount sources verified via `docker compose config`, gitignore coverage and config.yaml immutability confirmed.
- Files: `docker-compose.yml:6`, `config-dev.yaml` (new)
- Change:
  - `docker-compose.yml:6`: `- ./config.yaml:/app/config.yaml:ro` → `- ${HISAB_CONFIG:-./config.yaml}:/app/config.yaml:ro`, same style as the `HISAB_VAULT` line immediately below it (`docker-compose.yml:7`).
  - `config-dev.yaml` (new, repo root, gitignored by the existing `config-*.yaml` rule): copy the shape of `examples/config.openrouter.yaml` — `ledger.path: ./vault`, `ledger.template: personal`, `ledger.currency: PKR`, `model.id: openai/gpt-4.1-mini`, `model.base_url: null`, `model.api_key_env: null`, `model.provider_pin: null`, `model.agents_sdk: false`, `transcription.provider: openrouter`, `transcription.model: openai/gpt-4o-transcribe`, `transcription.language: null`, `memory.window_turns: 20`, `memory.keep_days: 30`, `whatsapp.poll_timeout: 20`, `whatsapp.chunk_chars: 3500`, `state.path: ./data`. (`make dev` overrides `ledger.path` via `HISAB_VAULT`, not this file, so the `ledger.path` value here only matters for a bare `HISAB_CONFIG=./config-dev.yaml docker compose up`.)
- Test: `docker compose config | grep -q "source: $(pwd)/config.yaml"` (default, no env set); `HISAB_CONFIG=./config-dev.yaml docker compose config | grep -q "source: $(pwd)/config-dev.yaml"` (override); `git check-ignore -q config-dev.yaml`; `git diff --quiet -- config.yaml`.

### Phase 2 — Makefile wiring and docs
**Status:** Done — `make dev` now defaults `HISAB_CONFIG` to `./config-dev.yaml` alongside `HISAB_VAULT`; `make up` unchanged (no HISAB_CONFIG, falls back to Gemini config.yaml); AGENTS.md documents HISAB_CONFIG in the commands table, the docker section intro, the docker table, and the rules-for-agents bullet. All `make -n` checks green.
- Files: `Makefile:12-14`, `AGENTS.md:56-58`, `AGENTS.md:60-81`
- Change:
  - `Makefile:12-14`: add `dev: HISAB_CONFIG ?= ./config-dev.yaml` above the existing `dev: HISAB_VAULT ?= ./sample-vault`, and change the recipe line to `HISAB_VAULT=$(HISAB_VAULT) HISAB_CONFIG=$(HISAB_CONFIG) docker compose up -d --build`. Update the `dev` help comment to mention it now also selects the OpenRouter sponsor config. `up` (`Makefile:8-10`) is untouched — it never sets `HISAB_CONFIG`, so the compose default (`./config.yaml`, Gemini) applies.
  - `AGENTS.md:56-58` (Commands table): add a row — `| Validate the sponsor config before a demo | python3 tests/check_endpoint.py --config config-dev.yaml |`.
  - `AGENTS.md:60-62` (the "Docker, and which ledger is mounted" intro paragraph): rename the section in prose to also cover config, and rewrite the sentence "It reads `config.yaml`…" to "It reads the config file selected by `HISAB_CONFIG` (default `./config.yaml`, Gemini) and mounts **one ledger folder** at `/app/vault`, selected the same way by `HISAB_VAULT` (default `./vault`)."
  - `AGENTS.md:64-73` (the table): add a row — `| Run the sponsor demo (OpenRouter, sample ledger) | HISAB_CONFIG=./config-dev.yaml HISAB_VAULT=./sample-vault docker compose up -d --build |`.
  - `AGENTS.md:79` (rules for agents, the `config.yaml` bullet): extend it to state that `HISAB_CONFIG` selects which gitignored config file is mounted, that it defaults to `./config.yaml`, that `config.yaml` (Gemini) is never overwritten by this selection and stays the rollback, and that `config-dev.yaml` is validated the same way (`python3 tests/check_endpoint.py --config <file>`).
- Test: `make -n dev` shows both `HISAB_VAULT=./sample-vault` and `HISAB_CONFIG=./config-dev.yaml` in the printed command; `make -n up` shows `HISAB_VAULT=./vault` and no `HISAB_CONFIG`; `grep -q HISAB_CONFIG AGENTS.md`; `python3 tests/smoke.py` still prints `ALL OK`.

## Risks

- If a future contributor sets `HISAB_CONFIG` globally in their shell, `make up` would silently pick up their override instead of Gemini — no different from the existing `HISAB_VAULT` behavior, and already covered by the same documented pattern in `AGENTS.md`.
- `docker compose config`'s exact output shape (`source: <abs path>`) was verified against the installed Docker Compose version in this environment; a materially different Compose version could format the resolved mount differently, which would only affect the verify command's grep, not the underlying `docker-compose.yml` change.

## Out of scope

- Any change to `hisab/config.py`, `hisab/loop.py`, or other runtime behavior.
- The `local`/`dev` Firebase-emulator environments from spec 001 — this plan is only the `HISAB_CONFIG` axis for the existing self-host Docker/Makefile flow.
- Committing real OpenRouter usage numbers, keys, or endpoints beyond the two public model ids already named in the issue and in `examples/config.openrouter.yaml`.
