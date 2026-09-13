---
type: Index
title: exec-plans
description: Implementation plans and where each one is in its life. A plan is a contract — no open questions — and moves between the four directories as work progresses.
tags: [index, plans]
timestamp: 2026-09-12T00:00:00Z
---

# exec-plans

Up: [docs/INDEX.md](../INDEX.md). Written by `/create-plan` into `backlog/`; `/implement` moves a plan to `active/` on start and `completed/` on finish; a plan overtaken by events goes to `superseded/` with a line saying by what.

## Backlog
| Plan | Problem it solves | Depends on |
|---|---|---|

## Active
| Plan | Started | Issue |
|---|---|---|

## Completed
| Plan | Shipped | Summary |
|---|---|---|
| [GH-7-connect-portal-user](completed/GH-7-connect-portal-user.md) | 2026-09-13 | Owner-scoped `firestore.rules` + `tests/rules/`; portal signs in by phone (Firebase Auth), seals the key with libsodium and writes only the five client fields; `runner/verify.py` matches `verify <nonce>` from the muted worker's message log and flips the tenant to `connected`; worker sends a throttled pending reminder, a one-time welcome, and exits on permanent auth failure; `make emulators` / `runner-up` / `rules-test` |
| [GH-4-hosted-tenant-runner](completed/GH-4-hosted-tenant-runner.md) | 2026-09-12 | New `runner/` package: sealed-box key decryption, UID-scoped per-tenant config (absolute paths, always-global model/transcription), idempotent Firestore reconciliation via `hisab.loop` subprocesses, `pending`-mute in `hisab/loop.py`, `docker-compose.runner.yml`, local/dev Firebase profiles |
| [GH-3-hosted-landing-portal-shell](completed/GH-3-hosted-landing-portal-shell.md) | 2026-09-12 | Static Next.js landing page + four-state portal shell (mocks only); `tests/check_landing.py` wired into smoke |
| [GH-2-dev-config-selection](completed/GH-2-dev-config-selection.md) | 2026-09-12 | `docker-compose.yml` config mount now follows `HISAB_CONFIG`; `make dev` selects the gitignored OpenRouter `config-dev.yaml`; `make up`/`stdin`/`demo` stay on Gemini |

## Superseded
| Plan | Superseded by |
|---|---|
