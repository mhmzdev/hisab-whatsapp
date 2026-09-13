# Hisab on WhatsApp

![Hisab — a ledger you text](showcase/hisab-cover.png)

A ledger you text. Send **"2500 coffee"**, a voice note in Urdu, Roman Urdu or English, or a photo of a receipt to your own WhatsApp agent, and it posts a real double-entry transaction to a plain-text ledger you own. One line comes back: the entry number and where the month stands.

*Hisab* (حساب) is the word every Urdu speaker already uses for exactly this.

> Built for the AI Tinkerers global hackathon *Agents, Everywhere* (2026-09-12). Extracted from a personal system the author has run since early September 2026; this is the public, API-level rewrite. Android only for the WhatsApp path — the platform has not shipped agent creation on iOS — so the terminal path below is how anyone else verifies it.

## Run it in your terminal, right now

No phone, no WhatsApp, one key. The same pipeline, against a committed sample ledger (a kiryana store, two weeks, fake numbers).

```bash
git clone https://github.com/mhmzdev/hisab-whatsapp && cd hisab-whatsapp
pip install -r requirements.txt            # needs python3 and hledger on PATH (brew install hledger / apt install hledger)
cp .env.example .env                       # put an OpenRouter key on the OPENROUTER_API_KEY line
cp examples/config.openrouter.yaml config.yaml
python3 tests/check_endpoint.py             # key valid, model has tools, transcription answers
bash tests/demo_terminal.sh
```

Then type, one per line:

```
Metro ko kitna dena hai
is mahine vs pichla
aaj ki sale 45000
what can I afford
undo
```

You will see the supplier balance, a two-column month table, a posted entry with its number, an affordability block, and the entry reversed. Every reply is the model calling one of six tools against `hledger`; nothing is scripted.

## Why this is not a chatbot on WhatsApp

- **Undo is a reply.** Quote the old message, say *undo*, and that entry reverses. A native WhatsApp gesture is the agent's control surface.
- **Every ledger line sits beside the message that made it.** Entries carry a number; the store maps it to the WhatsApp message id and keeps the posted block. The chat is the audit trail.
- **Private by platform.** A WhatsApp agent talks only to the person who created it. Self-hosted, there is no server of ours, no account, nothing to breach.

## What's under it

- **hledger**, a real plain-text accounting engine, not a categoriser. The ledger is a markdown file you can open anywhere. Every append runs `hledger check --strict`; a bad entry rolls back. Transfers are transfers, not spend, so the month total is honest.
- **A small tool-calling loop** on any OpenAI-compatible endpoint (OpenRouter by default, one key for the model and voice transcription). **Six tools, nothing else:** append, undo, report, learn a category rule, read accounts, add account. No shell, no file access.
- **The WhatsApp Agent Platform**: long-poll, one creator, thirty days of buffered messages. Idempotent by message id; the offset advances only after a batch, so a crash replays rather than drops or doubles. Model calls retry with backoff.
- **Setup is a conversation, in your language.** The first message asks, in English and Urdu, whether the ledger is personal or for a shop. Whichever you answer in becomes your language for up to eight questions and every fixed reply after; a one-line note says `/lang` switches it. Hisab is written in English and اردو; write to it in Roman Urdu and it answers in Roman Urdu.
- **Forwarded bank SMS are entries.** Long-press the bank's message, share it to the agent, done.
- **`export-ledger` returns your books.** Send it to the agent and the ledger folder comes back as a ZIP document: no keys, no chat history.

Architecture in one page: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Run it for real

You need an Android phone with WhatsApp, Docker, and an [OpenRouter](https://openrouter.ai) key.

1. In WhatsApp: Settings → Agents → Create an agent → Chat info → copy the API key.
2. `cp .env.example .env` and paste the WhatsApp key and your OpenRouter key.
3. `cp config.example.yaml config.yaml`. The defaults are fine; change the model if you like.
4. `docker compose up -d` (or `make selfhost`)
5. Send your agent any message. It asks personal or shop (in English and Urdu, answer in either), then up to seven more questions in that language, writes your chart of accounts, and posts what you sent.

Your ledger lives in `./vault/` on your machine. Nothing goes to anyone but your model provider.

**Setting it up for someone else** (a shop): they create the agent on *their* phone and send you the key; you run the container. They text, they get replies. You only ever see the ledger file, and only if they show you.

## Hosted Hisab (in progress)

For people who will never run Docker: sign in with a phone number, paste your agent's key, send the code the portal shows you to your agent, and we run the worker. Your key and ledger then live on our server, encrypted. Send `export-ledger` to your agent and the ledger comes back as a ZIP; revoke stops the worker and deletes the key. Self-host (above, `make selfhost`) keeps both on your own machine. 300 PKR/month is the presentation price; nothing in this repo collects it.

What exists today: the landing page and portal in `landing/` (phone sign-in, the key sealed in the browser, the `verify <code>` step, a Connected screen with live activity and a working Revoke), the runner in `runner/` that turns a Firestore tenant into one isolated worker, matches the code, enforces the monthly model-call allowance and retains a revoked ledger for 30 days, and the `export-ledger` command. `make up` runs the whole local hosted stack — the Auth/Firestore/Hosting emulators, the runner on Gemini, and the portal at http://localhost:3031/portal/ — as one command (see `runner/README.md`); `make dev` runs the runner on OpenRouter against the dedicated dev Firebase project once it exists. Design: [`docs/brainstorm/hosted-portal.md`](docs/brainstorm/hosted-portal.md); spec: [`docs/specs/001-hosted-portal.md`](docs/specs/001-hosted-portal.md).

## Viewing

The ledger is a markdown file. Open the folder in Obsidian with [hledger-dashboard](https://github.com/cousine/hledger-dashboard) for a balance sheet, monthly trends, a register, transfers and budget-versus-actual, all read from the same file. [Hledger Notes](https://github.com/bzimor/obsidian_hledger) is a desk-side entry modal for batch backfill. Neither is part of this project. `hledger` on the command line reads the folder as-is.

## What else this pattern does

The same shape, one creator, long-poll, a fenced tool surface, is a different product with different tools. None of these is built here.

- **A coding agent in your pocket.** Read-only over a repo by default; *what did I leave broken in auth yesterday* from the bus. This is where Hisab came from.
- **Personal ops.** A morning message with today's three things; an evening voice note captured to a file.
- **Small-business back office.** Stock counts, supplier orders, staff attendance, the same six-tool discipline.
- **Field capture.** Site visits, deliveries, inspections: a photo plus a sentence, where the moment happens.

## Privacy

Entries, voice notes and receipt photos go to the model provider you configured, through OpenRouter or the endpoint you set. Nothing goes to the author. To keep one provider, set `model.provider_pin`. The ledger, the message store and your keys never leave the machine you run this on.

## Origin and related

Extracted from a personal system running since September 2026: a bash relay on a VPS between a WhatsApp agent and Claude Code over a private vault, plus a ledger skill. This repo is the public rewrite as a plain API loop so it runs with any model. The relay itself is [`whatsapp-agent-relay`](https://github.com/mhmzdev/whatsapp-agent-relay), a separate repo, after the event.

## License

MIT.
