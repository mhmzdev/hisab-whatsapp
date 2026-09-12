# Hisab on WhatsApp

A ledger you text. Send **"2500 coffee"**, a voice note in Urdu, Roman Urdu or English, or a photo of a receipt to your own WhatsApp agent, and it posts a real double-entry transaction to a plain-text ledger you own. One line comes back: the entry number and where the month stands.

*Hisab* (حساب) is the word every Urdu speaker already uses for exactly this.

> **Status:** pre-hackathon build. Core, setup, tools and Docker in place; model and voice tests pending. Built for the AI Tinkerers global hackathon *Agents, Everywhere* on 2026-09-12. Extracted from a personal system running since early September 2026; the public version is being written here.

## Why WhatsApp

Expense tracking dies at the moment of paying. The app has to be opened, a category picked, and the moment passes. WhatsApp is already open. A voice note takes three seconds and works in whatever language you actually think in. The agent is useful *because* it lives where the money moment happens.

## Why this is not a chatbot on WhatsApp

- **Undo is a reply.** Quote the old message, say *undo*, and that entry reverses. A native WhatsApp gesture is the agent's control surface.
- **Every ledger line links to the message that made it.** Entries carry a number; the message store maps it to the WhatsApp message id. The chat is the audit trail.
- **Capture happens where the money moves.** A voice note at the till beats a form you open later.
- **Private by platform.** A WhatsApp agent talks only to the person who created it. There is no server, no account with us, nothing to breach.

## What's under it

- **hledger** — a real plain-text accounting engine. The ledger is a markdown file you can open anywhere. Every append is validated; a bad entry rolls back.
- **A small tool-calling agent loop** on OpenRouter — one key for the model and for voice transcription. Six tools, nothing else: append, undo, report, learn a category rule, read accounts, add account. No shell, no file access.
- **The WhatsApp Agent Platform** — a long-poll API with one hard rule: an agent talks only to the person who created it. Private by construction.
- **Setup is a conversation, in your language** — the first message asks English, اردو or Roman Urdu, then up to eight questions in that language, and writes your chart of accounts. Every reply after that follows the same choice; `/lang` changes it.

## Run it

You need: an Android phone with WhatsApp, Docker, and an [OpenRouter](https://openrouter.ai) key.

1. In WhatsApp: Settings → Agents → Create an agent → Chat info → copy the API key.
2. `cp .env.example .env` and paste the WhatsApp key and your OpenRouter key.
3. `cp config.example.yaml config.yaml`. The defaults are fine; change the model if you like.
4. `docker compose up -d`
5. Send your agent any message. It asks up to eight questions, writes your chart of accounts, then posts what you sent.

Your ledger lives in `./vault/` on your machine. Open that folder in Obsidian for the dashboard (below). Nothing goes to anyone but your model provider through OpenRouter; there is no server of ours.

Without WhatsApp, the same pipeline runs in a terminal: `python -m hisab.loop --stdin`.

**Setting it up for someone else** (the shop case): they create the agent on *their* phone and send you the key; you run the container. They text, they get replies. You only ever see the ledger file, and only if they show you.

## Try the sample

`sample-vault/` is a kiryana store, two weeks, fake numbers. Point `ledger.path` at it and ask *Metro ko kitna dena hai*, *is mahine vs pichla*, *balances*. Open it in Obsidian with hledger-dashboard to see the budget tab populated from its `~ monthly` rules.

## Viewing

The ledger is a markdown file. Open it in Obsidian with [hledger-dashboard](https://github.com/cousine/hledger-dashboard) for a balance sheet, monthly trends, a register and budget-versus-actual. [Hledger Notes](https://github.com/bzimor/obsidian_hledger) is a desk-side entry modal for batch backfill. Neither is part of this project.

## Android only, for now

The WhatsApp Agent Platform has not shipped agent creation on iOS.

## What's next

A hosted version for people who will never run Docker: sign up with a phone number, paste your agent's key, and we run the worker. Your key and ledger would then live on our server, encrypted, and you could take the ledger and revoke the key any time. Design notes in [`docs/brainstorm/hosted-portal.md`](docs/brainstorm/hosted-portal.md). Not part of this submission.

## Related

[`whatsapp-agent-relay`](https://github.com/mhmzdev/whatsapp-agent-relay) — the generic WhatsApp → coding-agent relay this project grew out of. Separate repo, after the event.

## License

MIT.
