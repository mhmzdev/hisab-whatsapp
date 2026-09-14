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
| [GH-40-local-clock](completed/GH-40-local-clock.md) | 2026-09-14 | `hisab/clock.py` is the one clock (configured `timezone`, default Asia/Karachi): Ledger/Store take it, `Ledger.hledger` passes `--today`, and the prompt date, dateless entries, quarter files, future guard, reports, quota month, runner activity month and export ZIP times all read it; smoke fixes the clock at 01:30 PKT on 1 Oct and greps for bare clock reads |
| [GH-37-portal-pk-phone-normalise](completed/GH-37-portal-pk-phone-normalise.md) | 2026-09-14 | Portal sign-in sends only a normalised Pakistani mobile: `landing/app/portal/phone.js` `normalizePkMobile` accepts `03…`, `3…`, `+92…`, `92…`, `0092…` with spaces or dashes and refuses the rest before an OTP; smoke runs 14 inputs through node, `check_landing.py` forbids `+92${…}` |
| [GH-36-export-ledger-delivery](completed/GH-36-export-ledger-delivery.md) | 2026-09-14 | `export-ledger` delivers: the ZIP uploads as `application/octet-stream` (WhatsApp refuses `application/zip`), a 400/131053 refusal is `export_rejected`; new `timezone` config (default Asia/Karachi) names it `hisab-YYYY-MM-DD-HHMM.zip` with caption `Ledger backup · <date, time>` in en/ur |
| [GH-27-failure-replies-error-codes](completed/GH-27-failure-replies-error-codes.md) | 2026-09-14 | Failure replies never carry exception text: `hisab/errors.py` registers every failure as a code (chat replies and runner `lastError` portal codes, with exit statuses), `errors.reply` renders `err_<code>` in en/ur with a self-host override, detail and message id go to stderr; `_chat` maps 401/403/4xx/5xx to codes; hledger rejections are cleaned to reason + line; `runner/errors.py` folded in; smoke guards completeness and leaks; `.agents/rules/errors.md` with `.claude/rules` symlink |
| [GH-23-theme-toggle-signed-in-landing](completed/GH-23-theme-toggle-signed-in-landing.md) | 2026-09-14 | Header theme toggle (System/Light/Dark) persisted in `hisab-theme` and applied by a pre-paint `<head>` script; brand mark links to `/`; landing CTAs read "Go to portal" from the portal-written `hisab-signed-in` hint without loading Firebase; `check_landing.py` guards both |
| [GH-22-landing-two-languages](completed/GH-22-landing-two-languages.md) | 2026-09-14 | Hisab is written in English and Urdu only: landing/portal drop Roman Urdu (`check_landing.py` requires exactly `en`/`ur`); the agent's fixed strings are `en`/`ur`, setup has no language question (the bilingual personal/shop greeting's answer sets it, with a one-time `/lang` note), stored `roman` reads as `en`; the model still answers Roman Urdu in Roman Urdu |
| [GH-26-portal-signout-confirm](completed/GH-26-portal-signout-confirm.md) | 2026-09-14 | Portal "Sign out" opens a modal `alertdialog` (Escape, backdrop and default-focused "Stay signed in" all cancel); only its confirm calls `signOut`; four new strings in en/ur/roman |
| [GH-21-openrouter-gemini-make-targets](completed/GH-21-openrouter-gemini-make-targets.md) | 2026-09-13 | Dropped direct-OpenAI support and the dead `agents_sdk` flag, with `transcription.provider` validated at config load (both `hisab/config.py` and `runner/config.py`); split `docker-compose.runner.yml` into a base file plus `docker-compose.runner.dev.yml` override selected by `RUNNER_CONFIG`; renamed self-host to `make selfhost`/`make selfhost-dev`; `make up` now brings up the Gemini-on-emulators hosted stack in one command (with a self-host collision guard in `runner-up`), `make dev` the OpenRouter dev-profile stack (fails fast until the dev Firebase project exists) |
| [GH-5-connected-status-revoke](completed/GH-5-connected-status-revoke.md) | 2026-09-13 | `runner/activity.py` syncs the Connected screen's rows from the worker's files; `runner/lifecycle.py` revokes on the client's `revokeRequestedAt` (stop, move the ledger to `inactive/`, delete the ciphertext) and sweeps inactive ledgers after 30 days; revoked tenants re-admit on a new key; portal Connected/Revoked screens live |
| [GH-7-connect-portal-user](completed/GH-7-connect-portal-user.md) | 2026-09-13 | Owner-scoped `firestore.rules` + `tests/rules/`; portal signs in by phone (Firebase Auth), seals the key with libsodium and writes only the five client fields; `runner/verify.py` matches `verify <nonce>` from the muted worker's message log and flips the tenant to `connected`; worker sends a throttled pending reminder, a one-time welcome, and exits on permanent auth failure; `make emulators` / `runner-up` / `rules-test` |
| [GH-4-hosted-tenant-runner](completed/GH-4-hosted-tenant-runner.md) | 2026-09-12 | New `runner/` package: sealed-box key decryption, UID-scoped per-tenant config (absolute paths, always-global model/transcription), idempotent Firestore reconciliation via `hisab.loop` subprocesses, `pending`-mute in `hisab/loop.py`, `docker-compose.runner.yml`, local/dev Firebase profiles |
| [GH-3-hosted-landing-portal-shell](completed/GH-3-hosted-landing-portal-shell.md) | 2026-09-12 | Static Next.js landing page + four-state portal shell (mocks only); `tests/check_landing.py` wired into smoke |
| [GH-2-dev-config-selection](completed/GH-2-dev-config-selection.md) | 2026-09-12 | `docker-compose.yml` config mount now follows `HISAB_CONFIG`; `make dev` selects the gitignored OpenRouter `config-dev.yaml`; `make up`/`stdin`/`demo` stay on Gemini |

## Superseded
| Plan | Superseded by |
|---|---|
