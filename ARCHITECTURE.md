---
type: Architecture
title: Hisab on WhatsApp — bird's-eye view
description: One page on how a WhatsApp message becomes a validated ledger entry, what state exists, which invariants hold, and where things fail.
resource: https://github.com/mhmzdev/hisab-whatsapp
tags: [architecture, agent, hledger, whatsapp]
timestamp: 2026-09-14T00:00:00Z
---

# Architecture

Hisab is a **tool-calling agent** with exactly six tools, sitting between a **WhatsApp agent** (one creator, long-poll, no webhook) and a **plain-text hledger ledger** in markdown. Every write to the ledger passes `hledger check --strict` and rolls back if it fails. Self-hosted, there is no server of ours: one process, one person, one folder of files. Hosted mode runs that same process once per tenant; it is a layer on top, not a different pipeline (see [Hosted mode](#hosted-mode)).

Read in this order: [`AGENTS.md`](AGENTS.md) (how to work here) → this file (how it fits together) → [`docs/INDEX.md`](docs/INDEX.md) (the artifacts, and every other README) → the code.

## The flow of one message

```
 phone ──(text · voice note · photo)──▶ WhatsApp Agent Platform ──long-poll──▶ hisab/loop.py
                                                                                   │
                                     ┌─────────────────────────────────────────────┤
                                     │ store.py  dedup by message id · offset      │
                                     │           advanced only after the batch     │
                                     ▼                                             │
                          hosted + pending? ──▶ record it, at most a reminder; stop (runner/verify.py reads it)
                                     │
                          fixed command? ──▶ export-ledger → archive.py ZIP → send_document
                                     │       /help · /clear · /setup · /lang   (no model call, no quota)
                                     ▼                                             ▼
                          no ledger yet?  ──▶ setup.py  (8 numbered Qs)  ──▶ templates/ → ledger folder
                                     │
                          voice note ──▶ wa.py → wa-agent (OpenRouter | Gemini) ──▶ text
                          photo      ──▶ base64 image in the model message
                                     │
                          hosted quota spent? ──▶ quota_exceeded reply; no model call
                                     ▼
                          agent.py   SYSTEM prompt (rendered per message: date, currency, default
                                     account, language line, declared accounts) + last 20 turns
                                     + [rule hint from rules.md]  ──▶  OpenAI-compatible chat API
                                     │            ▲
                                     │ tool_calls │ tool results          (≤ 6 rounds, retries w/ backoff)
                                     ▼            │
                          tools.py   append_entry · undo_last · report · learn_rule · read_accounts · add_account
                                     │
                                     ▼
                          ledger.py  quarter file append ──▶ hledger check --strict ──▶ keep | roll back
                                     │
                                     ▼        (any exception ──▶ errors.py: code → log detail → fixed reply)
                          one-line reply ──▶ wa.py → wa-agent (markdown→WhatsApp, chunk < 3,500) ──▶ phone
                                     │
                          store.py   reply + entry number recorded beside the inbound message id
```

Media is processed, never stored: a voice note is deleted once transcribed, a photo once the model call returns, and a failed turn's leftovers are swept after 24 h.

The same pipeline runs without WhatsApp: `python -m hisab.loop --stdin` reads lines from a terminal. That is how a judge or a self-hoster without a WhatsApp agent verifies it.

## Components

| Component | Responsibility | Talks to |
|---|---|---|
| [`hisab/loop.py`](hisab/loop.py) | Orchestration: poll, route (pending / command / setup / agent), reply, record; the hosted welcome, pending reminder, quota check and media sweep | everything below |
| [`hisab/wa.py`](hisab/wa.py) | Thin adapter over the pinned [`wa-agent`](https://pypi.org/project/wa-agent/) package, which does the platform calls: `GET /updates` long-poll, media download, typing indicator, `POST /messages` with chunking, document send, a per-method rate limiter, and voice → text (OpenRouter or Gemini). The adapter maps config onto it, maps every wa-agent failure code to a Hisab code, flattens Obsidian wikilinks, and `inbound()` is the one reader of the message dict; a rejected token exits with status 3 | the platform (via wa-agent) |
| [`hisab/store.py`](hisab/store.py) | Runtime state on disk: `offset`, `messages.jsonl`, `setup.json`, `creator.json`, `usage.json`, `welcomed.json`, `reminder.json`; the rolling window; entry-number ↔ message-id map | loop |
| [`hisab/errors.py`](hisab/errors.py) | The failure registry: every chat reply and portal `lastError` is a code; `classify` → `log` → `reply` | loop, agent, runner, landing check |
| [`hisab/archive.py`](hisab/archive.py) | `export-ledger`'s ZIP: the canonical ledger files only, never state, keys or media | loop |
| [`hisab/clock.py`](hisab/clock.py) | The one clock: every "today", quota month and export name in the configured `timezone`, never the container's UTC | ledger, store, loop, runner |
| [`hisab/setup.py`](hisab/setup.py) | The first conversation: eight numbered questions (personal/shop, the account holder name, …); writes the ledger folder from `templates/` | ledger, i18n, store |
| [`hisab/i18n.py`](hisab/i18n.py) | Every fixed string in `en` / `ur`; the model's reply-shape line per language (the `en` line answers Roman Urdu in Roman Urdu) | setup, loop, agent |
| [`hisab/agent.py`](hisab/agent.py) | The system prompt and the tool-calling loop; endpoint and key are config | the model API, tools |
| [`hisab/tools.py`](hisab/tools.py) | The six tools: JSON schemas for the model and the Python that runs each | ledger |
| [`hisab/ledger.py`](hisab/ledger.py) | hledger on markdown: files, append with strict check and rollback, undo by number, accounts, rules, periodic rules, reports, settings | `hledger` binary |
| [`hisab/config.py`](hisab/config.py) | `config.yaml` merged over defaults; secrets only from `.env` / environment; `provider: auto` picks OpenRouter if its key is set, else Gemini, unless a config pins one | everything |

## State on disk

| Where | What | Owner |
|---|---|---|
| **Ledger folder** (`vault/` by default, mounted into the container) | `hisab.md` (master: commodities + includes) · `accounts.md` (chart of accounts, `~ monthly` rules) · `rules.md` (keyword → account, learned) · `YYYY-Qn.md` (transactions, `## YYYY-MM` headings, `n:` tags) · `settings.json` (language, mode, currency) | the user; written only through `ledger.py` |
| **State folder** (`data/`, a named Docker volume) | `offset` · `messages.jsonl` · `setup.json` · `creator.json` · hosted only: `usage.json` (model calls this month), `welcomed.json`, `reminder.json` · `media/` and `exports/` (transient: a media file is deleted once transcribed or seen by the model, an export ZIP once sent; a failed turn's file is swept after 24 h; never exported, never stored elsewhere) | `store.py` and `loop.py` |
| **Config** | `config.yaml` (no secrets, gitignored) · `.env` (secrets, never committed) · hosted: a per-tenant config the runner writes | the operator |

The ledger folder is the product. Open it in Obsidian with hledger-dashboard and it is a balance sheet; `hledger` on the command line reads it as-is.

## Invariants

1. **Six tools.** The model cannot do anything that is not one of them. No shell, no file access.
2. **Strict check or nothing.** `Ledger.append` writes, checks, and restores the previous file on rejection. Undeclared accounts, unbalanced postings and future dates never land.
3. **Entry numbers are monotonic** across quarter files (`next_entry_number` scans them all) and are the only handle for undo.
4. **Idempotent transport.** A message id already in the store is skipped; the offset advances after the batch, so a crash replays rather than drops or doubles.
5. **Two written languages or none.** A fixed string — the agent's (`hisab/i18n.py`) or the portal's (`landing/content/strings.json`) — exists in `en` and `ur` or it does not ship. Roman Urdu is never written by us; users may chat in it and the model replies in kind. Setup takes the language from the first answer; `/lang` changes it.
6. **Conventions the dashboard reads:** alphabetic commodities, three-posting transfers via `equity:transfer`, `~ monthly` rules, `P` price lines.
7. **Private by platform.** The agent replies only to its creator. Nothing goes anywhere but the model provider, the transcription provider and WhatsApp.
8. **Failures are codes.** No exception text, HTTP body, hledger banner or provider name reaches a user; `hisab/errors.py` is the only place a failure becomes words.
9. **One clock.** Dates come from `hisab/clock.py` in the configured timezone, so an entry after midnight in Karachi is dated today, not yesterday.

## Where it fails, and what happens

| Failure | Behaviour |
|---|---|
| Poll request fails (hotspot, 5xx) | log, sleep 5 s, retry; offset unchanged |
| A WhatsApp method nears its limit (`messages`/`statuses`/`updates`/`media` each 12–15/min, own rolling 60 s window fixed by wa-agent, per agent) | wa-agent's rate limiter blocks before the request is sent — the poll loop can never exceed 15/min even when every long-poll returns instantly |
| WhatsApp returns 429 (`error.code 130429`) | the method's window is marked fully spent; the next call backs off until it can plausibly have reset, not a flat delay |
| WhatsApp returns 409 on a poll (`error.code 1752041`) | logged as "another poller is using this agent" — the two-pollers-on-one-agent footgun, not a generic failure |
| WhatsApp rejects the token (401/190, 400/100) | the worker exits with status 3; hosted, the runner writes `lastError: "auth"` and does not restart it |
| Model call fails (429, 5xx, timeout, connection) | 4 attempts, 0/2/4/8 s backoff; then code `model_unavailable`. A 401/403 is `model_auth` and a different 4xx is `model_rejected`, both without a retry. Hosted, a `model_*` failure refunds the monthly allowance |
| The model loops past 6 tool rounds | `too_many_steps`: try a shorter message |
| Hosted monthly allowance reached | `quota_exceeded`, no model call; a warning line is appended from 80% |
| Any failure a user is told about | a code from `hisab/errors.py`, rendered in the user's language with the next step (self-host and hosted can differ); the raw detail and the message id go to stderr, never to WhatsApp |
| hledger rejects the block | file restored; the tool returns the cleaned reason (no banner, no path) and the model replies; outside a tool call the user gets `ledger_rejected` |
| Voice note or photo download fails (any wa-agent code, including an expired media url) | `media_fetch_failed`; nothing posted |
| Transcription fails (also an `[inaudible]` transcript) | `transcription_failed`: send it as text or try again; nothing posted |
| `export-ledger` document send fails | the ZIP goes up as `application/octet-stream` (WhatsApp refuses `application/zip`); any refusal (wa-agent `platform_rejected`, e.g. 400/131053) is `export_rejected` (no retry suggested), anything else `export_failed`; a ZIP over the document limit is `export_too_large` and never sent |
| Reply over 4,096 chars | split on paragraph boundaries under 3,500, numbered `(i/N)` |
| Container restarts mid-batch | replay from the stored offset; already-seen ids skipped |
| Laptop closed for a day | WhatsApp buffers 30 days; entries post on the next poll |

## Deployment shapes

- **Docker** (`docker-compose.yml`): the image has Python, hledger, the code; `.env` supplies the two keys; `./vault` and a named data volume are mounted. One container per WhatsApp agent — two pollers on one agent fight over the cursor.
- **Terminal**: `python -m hisab.loop --stdin` with the same config; `tests/demo_terminal.sh` runs it on a copy of the sample ledger.
- **Someone else's shop**: the owner creates the agent on their phone and hands over the key; the operator runs the container; the owner texts, the owner gets replies.
- **Hosted** (built and running locally with `make up`; not deployed): see below.

## Hosted mode

```
 portal (landing/, static Next.js) ──phone auth · sealed key · revoke──▶ Firestore tenants/{uid}
                                                                              │ snapshot listener
                                                                              ▼
 runner/ (the only thing that talks to Firestore) ── decrypt key · write per-tenant config ──▶ python -m hisab.loop
        ▲   verify.py reads the worker's messages.jsonl for "verify <nonce>"                     (one per tenant,
        │   activity.py reads its files for the Connected screen                                  vault/<uid>, data/<uid>)
        └── lifecycle.py: revoke (stop, move to inactive/, delete ciphertext), sweep after 30 days
```

The worker is the self-host code with three runner-set flags: `pending` (muted until verified), `hosted` (welcome once, hosted error wording) and `quota.monthly_limit`. Its environment comes only from the runner: that tenant's token as `WHATSAPP_AGENT_TOKEN`, never the operator's (either name) or `RUNNER_PRIVATE_KEY`, and `HISAB_NO_DOTENV=1` so it never reads a `.env`. It never learns what Firebase is; the runner never talks to WhatsApp. `firestore.rules` lets a client write five fields and never `status` or `creatorId`, so "Connected" always means the runner matched the code. The whole story, tenant state by tenant state: [`runner/README.md`](runner/README.md); the portal's screens: [`landing/README.md`](landing/README.md).

## Not here, on purpose

Shared wallets (the platform has no groups) · chart images · a ledger UI on the phone (Obsidian is the viewer; the portal only connects and revokes) · payments (300 PKR/month is a presentation price) · the Claude Code relay this grew out of (`wa-agent relay`, coming in [whatsapp-agent-cli](https://github.com/mhmzdev/whatsapp-agent-cli), which also holds the WhatsApp transport Hisab moves onto in #57).
