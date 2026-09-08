# Hisab on WhatsApp

A ledger you text. Send **"2500 coffee"**, a voice note in Urdu, Roman Urdu or English, or a photo of a receipt to your own WhatsApp agent, and it posts a real double-entry transaction to a plain-text ledger you own. One line comes back: the entry number and where the month stands.

*Hisab* (حساب) is the word every Urdu speaker already uses for exactly this.

> **Status:** scaffold, pre-hackathon. Built for the AI Tinkerers global hackathon *Agents, Everywhere* on 2026-09-12. Extracted from a personal system running since early September 2026; the public version is being written here.

## Why WhatsApp

Expense tracking dies at the moment of paying. The app has to be opened, a category picked, and the moment passes. WhatsApp is already open. A voice note takes three seconds and works in whatever language you actually think in. The agent is useful *because* it lives where the money moment happens.

## What's under it

- **hledger** — a real plain-text accounting engine. The ledger is a markdown file you can open anywhere. Every append is validated; a bad entry rolls back.
- **A small tool-calling agent loop** on OpenRouter — one key for the model and for voice transcription. Six tools, nothing else: append, undo, report, learn a category rule, read accounts, add account. No shell, no file access.
- **The WhatsApp Agent Platform** — a long-poll API with one hard rule: an agent talks only to the person who created it. Private by construction.
- **Setup is a conversation** — the first message triggers up to eight questions and writes your chart of accounts.

## Viewing

The ledger is a markdown file. Open it in Obsidian with [hledger-dashboard](https://github.com/cousine/hledger-dashboard) for a balance sheet, monthly trends, a register and budget-versus-actual. [Hledger Notes](https://github.com/bzimor/obsidian_hledger) is a desk-side entry modal for batch backfill. Neither is part of this project.

## Android only, for now

The WhatsApp Agent Platform has not shipped agent creation on iOS.

## Related

[`whatsapp-agent-relay`](https://github.com/mhmzdev/whatsapp-agent-relay) — the generic WhatsApp → coding-agent relay this project grew out of. Separate repo, after the event.

## License

MIT.
