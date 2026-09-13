---
type: Architecture
title: Hisab on WhatsApp — bird's-eye view
description: One page on how a WhatsApp message becomes a validated ledger entry, what state exists, which invariants hold, and where things fail.
resource: https://github.com/mhmzdev/hisab-whatsapp
tags: [architecture, agent, hledger, whatsapp]
timestamp: 2026-09-12T00:00:00Z
---

# Architecture

Hisab is a **tool-calling agent** with exactly six tools, sitting between a **WhatsApp agent** (one creator, long-poll, no webhook) and a **plain-text hledger ledger** in markdown. Every write to the ledger passes `hledger check --strict` and rolls back if it fails. There is no server of ours: one process, one person, one folder of files.

Read in this order: [`AGENTS.md`](AGENTS.md) (how to work here) → this file (how it fits together) → [`docs/INDEX.md`](docs/INDEX.md) (the artifacts) → the code.

## The flow of one message

```
 phone ──(text · voice note · photo)──▶ WhatsApp Agent Platform ──long-poll──▶ hisab/loop.py
                                                                                   │
                                     ┌─────────────────────────────────────────────┤
                                     │ store.py  dedup by message id · offset      │
                                     │           advanced only after the batch     │
                                     ▼                                             ▼
                          no ledger yet?  ──▶ setup.py  (language first, ≤8 Qs)  ──▶ templates/ → ledger folder
                                     │
                          voice note ──▶ transcribe.py (OpenRouter endpoint | Gemini) ──▶ text
                          photo      ──▶ base64 image in the model message
                                     │
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
                                     ▼
                          one-line reply ──▶ wa.py (markdown→WhatsApp, chunk < 3,500) ──▶ phone
                                     │
                          store.py   reply + entry number recorded beside the inbound message id
```

The same pipeline runs without WhatsApp: `python -m hisab.loop --stdin` reads lines from a terminal. That is how a judge or a self-hoster without an Android agent verifies it.

## Components

| Component | Responsibility | Talks to |
|---|---|---|
| [`hisab/loop.py`](hisab/loop.py) | Orchestration: poll, route (command / setup / agent), reply, record | everything below |
| [`hisab/wa.py`](hisab/wa.py) | WhatsApp Agent Platform: `GET /updates` long-poll, media download, typing indicator, `POST /messages` with chunking, a per-method rate limiter | the platform |
| [`hisab/store.py`](hisab/store.py) | Runtime state on disk: `offset`, `messages.jsonl`, `setup.json`, `creator.json`; the rolling window; entry-number ↔ message-id map | loop |
| [`hisab/setup.py`](hisab/setup.py) | The first conversation: language, then personal/shop questions; writes the ledger folder from `templates/` | ledger, i18n, store |
| [`hisab/i18n.py`](hisab/i18n.py) | Every fixed string in `en` / `ur` / `roman`; the model's reply-shape line per language | setup, loop, agent |
| [`hisab/agent.py`](hisab/agent.py) | The system prompt and the tool-calling loop; endpoint and key are config | the model API, tools |
| [`hisab/tools.py`](hisab/tools.py) | The six tools: JSON schemas for the model and the Python that runs each | ledger |
| [`hisab/ledger.py`](hisab/ledger.py) | hledger on markdown: files, append with strict check and rollback, undo by number, accounts, rules, periodic rules, reports, settings | `hledger` binary |
| [`hisab/transcribe.py`](hisab/transcribe.py) | Voice → text, two providers | OpenRouter or Gemini |
| [`hisab/config.py`](hisab/config.py) | `config.yaml` merged over defaults; secrets only from `.env` / environment | everything |

## State on disk

| Where | What | Owner |
|---|---|---|
| **Ledger folder** (`vault/` by default, mounted into the container) | `hisab.md` (master: commodities + includes) · `accounts.md` (chart of accounts, `~ monthly` rules) · `rules.md` (keyword → account, learned) · `YYYY-Qn.md` (transactions, `## YYYY-MM` headings, `n:` tags) · `settings.json` (language, mode, currency) | the user; written only through `ledger.py` |
| **State folder** (`data/`, a named Docker volume) | `offset` · `messages.jsonl` · `setup.json` · `creator.json` · `media/` | `store.py` and `loop.py` |
| **Config** | `config.yaml` (safe to commit, gitignored anyway) · `.env` (secrets, never committed) | the operator |

The ledger folder is the product. Open it in Obsidian with hledger-dashboard and it is a balance sheet; `hledger` on the command line reads it as-is.

## Invariants

1. **Six tools.** The model cannot do anything that is not one of them. No shell, no file access.
2. **Strict check or nothing.** `Ledger.append` writes, checks, and restores the previous file on rejection. Undeclared accounts, unbalanced postings and future dates never land.
3. **Entry numbers are monotonic** across quarter files (`next_entry_number` scans them all) and are the only handle for undo.
4. **Idempotent transport.** A message id already in the store is skipped; the offset advances after the batch, so a crash replays rather than drops or doubles.
5. **Three languages or none.** A fixed agent string (`hisab/i18n.py`) exists in `en`, `ur`, `roman` or it does not ship. The hosted landing page and portal (`landing/content/strings.json`) ship exactly `en` and `ur`.
6. **Conventions the dashboard reads:** alphabetic commodities, three-posting transfers via `equity:transfer`, `~ monthly` rules, `P` price lines.
7. **Private by platform.** The agent replies only to its creator. Nothing goes anywhere but the model provider, the transcription provider and WhatsApp.

## Where it fails, and what happens

| Failure | Behaviour |
|---|---|
| Poll request fails (hotspot, 5xx) | log, sleep 5 s, retry; offset unchanged |
| A WhatsApp method nears its limit (`messages`/`statuses`/`updates`/`media` each 12–15/min, own rolling 60 s window, per agent) | the rate limiter blocks before the request is sent — the poll loop can never exceed 15/min even when every long-poll returns instantly |
| WhatsApp returns 429 (`error.code 130429`) | the method's window is marked fully spent; the next call backs off until it can plausibly have reset, not a flat delay |
| WhatsApp returns 409 on a poll (`error.code 1752041`) | logged as "another poller is using this agent" — the two-pollers-on-one-agent footgun, not a generic failure |
| Model call fails (429, 5xx, timeout, connection) | 4 attempts, 0/2/4/8 s backoff; then a plain message in the user's language |
| hledger rejects the block | file restored, tool returns the error, model replies "not posted: …" |
| Transcription fails | plain message asking for text; nothing posted |
| Reply over 4,096 chars | split on paragraph boundaries under 3,500, numbered `(i/N)` |
| Container restarts mid-batch | replay from the stored offset; already-seen ids skipped |
| Laptop closed for a day | WhatsApp buffers 30 days; entries post on the next poll |

## Deployment shapes

- **Docker** (`docker-compose.yml`): the image has Python, hledger, the code; `.env` supplies the two keys; `./vault` and a named data volume are mounted. One container per WhatsApp agent — two pollers on one agent fight over the cursor.
- **Terminal**: `python -m hisab.loop --stdin` with the same config; `tests/demo_terminal.sh` runs it on a copy of the sample ledger.
- **Someone else's shop**: the owner creates the agent on their phone and hands over the key; the operator runs the container; the owner texts, the owner gets replies.

## Not here, on purpose

Shared wallets (the platform has no groups) · chart images · a phone UI (Obsidian is the viewer) · the Claude Code relay this grew out of (`whatsapp-agent-relay`, separate repo).

Hosted multi-tenant mode is a separate surface, not this pipeline: [`runner/README.md`](runner/README.md) reconciles a Firestore tenant into one isolated worker of the same self-host code, with its own custody, verification and quota rules on top.
