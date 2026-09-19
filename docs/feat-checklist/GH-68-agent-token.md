---
type: Checklist
title: GH-68-agent-token — acceptance checklist
description: Review of reading the WhatsApp token from WHATSAPP_AGENT_TOKEN with WHATSAPP_TOKEN as a noted fallback, the hosted runner's per-tenant token handoff and HISAB_NO_DOTENV, and the docs switched to the new name, against issue #68.
tags: [checklist, config, runner, hosted, docs]
timestamp: 2026-09-20T00:00:00Z
---

# GH-68-agent-token — acceptance checklist   (9 proven · 2 manual · 0 failing)

Scope: 14 files on `GH-68-agent-token`: `hisab/config.py`, `hisab/loop.py`, `runner/reconcile.py`, `tests/smoke.py`, the docs and comments (`.env.example`, `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `runner/README.md`, `runner/crypto.py`, `docker-compose.runner.yml`, `docs/self-host-vps.md`) and the plan + INDEX. Intent: [#68](https://github.com/mhmzdev/hisab-whatsapp/issues/68) "Done when", the plan [GH-68-agent-token](../exec-plans/completed/GH-68-agent-token.md), and the lead's two additions (tenant workers never read `.env`; an empty new name falls back). No live run: a set token would poll WhatsApp.

- [x] Only `WHATSAPP_AGENT_TOKEN` set → it is used, no note — `python3 tests/smoke.py` (config: `_token_load(WHATSAPP_AGENT_TOKEN=…)`)
- [x] Only `WHATSAPP_TOKEN` set → it is used, the rename note prints exactly once across two loads, names both variables, never the value — `python3 tests/smoke.py`
- [x] Both set → the new one wins, no note — `python3 tests/smoke.py`
- [x] New name empty or whitespace-only with the old one set → the old one is used, with the note — `python3 tests/smoke.py` (`blank in ("", "   ")`)
- [x] Empty token exits naming the new variable — `env -i … GEMINI_API_KEY=fake WHATSAPP_AGENT_TOKEN= python3 -m hisab.loop --config <scratch>/none.yaml` → `WHATSAPP_AGENT_TOKEN is empty; put it in .env`, exit 1, before any poll (also with `"   "`)
- [x] A hosted tenant worker polls with its own token whatever the runner's environment sets: with `RUNNER_PRIVATE_KEY`, `WHATSAPP_AGENT_TOKEN=operator-new` and `WHATSAPP_TOKEN=operator-old` in the runner's environ, the tenant env has `WHATSAPP_AGENT_TOKEN` = the tenant token, no `WHATSAPP_TOKEN`, no `RUNNER_PRIVATE_KEY`, `HISAB_NO_DOTENV=1`, and `whatsapp_token(tenant_env)` = the tenant token — `python3 tests/smoke.py` (runner: reconcile block)
- [x] A tenant worker never reads `.env`; self-host still does — `python3 tests/smoke.py` (temp cwd `.env` with `RUNNER_PRIVATE_KEY` and `WHATSAPP_TOKEN`: `loop.load_env()` loads neither under the marker, both without it)
- [x] `state_hash` follows the tenant token and ignores the operator's environ; payload key unchanged (`"token"`), so running tenants don't restart — `python3 tests/smoke.py`; the existing idempotency assert (`launcher.calls == 1`) still holds
- [x] No user-facing doc tells anyone to set `WHATSAPP_TOKEN` — `! git grep -n WHATSAPP_TOKEN -- '*.md' '*.yml' .env.example ':!docs/exec-plans' ':!docs/feat-checklist' | grep -v WHATSAPP_AGENT_TOKEN` exits 0
- [?] Self-host starts with only the new name (post-merge, owner + lead): put only `WHATSAPP_AGENT_TOKEN=<demo agent key>` in a scratch `.env`, `docker compose up -d --build`, expect `Polling WhatsApp.` in `docker compose logs --tail 50` and no rename note; send the demo agent a message, expect a reply
- [?] Hosted runner still connects a tenant (post-merge, owner + lead): stop the self-host container, `make up`, connect a tenant through the portal at :3031 with the demo agent key, send `verify <nonce>`, expect the portal to show Connected and a reply on WhatsApp

Also proven: the three smoke additions each catch their regression. Removing the operator-name strip, setting the tenant token under the old name, and making `load_env` always load each failed `python3 tests/smoke.py`; the files were then restored and smoke re-run green.

## Conventions
- Surface: six tools unchanged; no new network call. Writes, transport, dashboard conventions: untouched.
- Language: no new user-facing string — the rename note and the empty-token exit are operator stderr, not replies, so no `i18n.py` or `errors.py` change.
- Privacy: no value is ever printed (the note names variables only; smoke asserts the value is absent). The diff has no personal paths, keys or ids (grep for home paths, email, `sk-or-`, `AIza`: nothing). `.env`, `config.yaml`, `vault/` untouched.
- Docs: README, AGENTS.md, ARCHITECTURE.md, runner/README.md and the self-host guide are all true to the new behaviour; no new config key, so `config.example.yaml` is unchanged.

## Findings
None.
