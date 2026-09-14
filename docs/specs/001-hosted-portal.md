---
type: Spec
slug: hosted-portal
title: Hosted Hisab — landing page and portal
description: A hosted Hisab service that connects one WhatsApp agent and one plain-text ledger to a phone-authenticated portal, with local-first development and no real subscription payments in the initial demo.
tags: [spec, hosted, portal]
timestamp: 2026-09-12T00:00:00Z
status: shipped
parent: https://github.com/mhmzdev/hisab-whatsapp/issues/1
last_verified: 2026-09-14
---

# 001 — Hosted Hisab — Spec

## Problem

A shop owner or other non-technical user cannot run Docker or manage a VPS, so using Hisab currently requires a technical relative to operate the worker. The hosted product should let a person connect a WhatsApp agent from a browser, then use the same Hisab conversation without seeing a terminal.

This changes the privacy promise: hosted Hisab holds the agent key and the ledger. The product must state that plainly and provide ownership verification, revocation, export, and retention boundaries that match the custody model.

## Solution

Provide a static landing page and portal where a person signs in with their phone number, connects one WhatsApp agent, proves control of that agent through an in-band WhatsApp challenge, and sees connection/activity metadata. A runner reconciles Firestore tenant state with one Hisab worker and one ledger folder per tenant. The worker remains the existing Hisab product: a WhatsApp conversation over a strict hledger markdown ledger.

The initial demo implements the complete product flow except real subscription payments. Local development can use Firebase emulators with a resettable ledger while the demo WhatsApp agent and model provider remain real integrations. A separate `dev` profile can use an existing dedicated Firebase project for realistic Firebase integration without touching production.

## User stories

1. As a shop owner, I can understand the hosted/self-hosted distinction on the landing page so that I know who holds my key and ledger.
2. As a new user, I can sign in with a phone number and SMS OTP so that the portal has a Firebase identity.
3. As an authenticated user, I can enter an agent name and API key once so that Hisab can connect the agent without showing the key again.
4. As an authenticated portal user, I can see a short-lived `verify <nonce>` command and send it to my agent so that Hisab can bind my portal account to the phone that controls the connected agent.
5. As a pending user, I receive a language-neutral reminder for non-verification messages, and those messages are not treated as ledger traffic before ownership verification.
6. As a verified user, my agent sends the existing Hisab welcome and starts setup with language first; subsequent replies follow English, Urdu, or Roman Urdu as selected in setup.
7. As a connected user, I can see agent name, connected-since time, last activity, entries this month, language, and revoke access, without seeing ledger contents in the browser.
8. As a connected user, I can send the exact `export-ledger` command and receive a ZIP ledger bundle as a WhatsApp document.
9. As an operator, I can run a resettable local `vault/` for first-time onboarding or a pre-seeded `sample-vault/` for an existing-ledger demo, while using real model and demo-agent calls.
10. As a plan owner, I receive up to 1,000 model calls per agent per month in the initial plan and a clear limit response when the quota is exhausted.

## Decisions

### Trust and authentication

- Hosted Hisab is a trusted custodian. The VPS can decrypt and use a tenant's agent key and ledger at runtime; encryption at rest and access controls do not claim operator-blind plaintext.
- Authentication has two independent proofs:
  - Firebase Phone Auth proves control of the portal phone number and establishes the Firebase `uid`.
  - The portal displays a short-lived nonce to that authenticated session. The runner accepts only a matching case-insensitive fixed command such as `verify 482913` inbound from the agent creator, then records the creator and connects the tenant. A bare number is not valid.
- Firebase's login OTP is not relayed through WhatsApp. The agent challenge is our own nonce flow.
- The WhatsApp API key is never a browser login credential. The portal encrypts it client-side with a runner-held public key; Firestore receives only ciphertext, and the runner alone holds the private key.
- No public VPS ingestion endpoint or Firebase Function is required for the MVP.

### Verification and language

- A fresh agent cannot send an unsolicited challenge until it has received an inbound message. The pending worker sends nothing. The portal instructs the signed-in user to send the displayed `verify <nonce>` command to the agent; a matching first inbound reveals the creator identifier, connects the tenant, and only then triggers the welcome.
- While pending, non-matching messages are not processed or queued as ledger entries. The agent sends a short language-neutral reminder to send the verification code shown in the portal.
- Language is not selected before verification. Pending reminders include the supported language labels without assuming a language. The existing in-chat setup asks for language first, then all fixed strings and model replies follow `en`, `ur`, or `roman`.

### Tenancy and ledger ownership

- MVP tenancy is one WhatsApp agent and one ledger per Firebase account/plan. Personal and shop ledgers require separate agents/accounts for now; future multi-agent plans do not share a ledger.
- A runner holds one Firestore snapshot listener and runs one worker per tenant. Workers never share an agent key.
- Firestore is control-plane metadata: tenant status, encrypted key, creator ID, language, plan, timestamps, activity, quota counters, and desired worker state. It is not the accounting source of truth.
- The canonical ledger remains the hledger markdown folder on disk. Tenant paths use the opaque Firebase UID (`vault/<uid>/`, `data/<uid>/`); do not derive paths from phone numbers, creator IDs, or agent names. A second UUID mapping is deferred.

### Ledger export and data formats

- `export-ledger` is an exact runner-level command intercepted before the model loop, preserving the six-tool contract.
- The worker creates a ZIP document containing `hisab.md`, all included quarter files, `accounts.md`, `rules.md`, and `settings.json`.
- The bundle excludes API keys/ciphertext, `.env`, worker state, message history, and downloaded media. It is sent as a WhatsApp document, subject to the platform's 16 MB limit; it is not rendered as chat text.
- CSV is not the canonical MVP format. A later CSV export may be derived for analysis. Any future CSV import must regroup postings into transactions and pass every entry through strict ledger validation; it must never replace the markdown ledger directly.

### Revoke, quota, and money

- Revoke stops the worker immediately and deletes the encrypted key. The inactive ledger folder is retained for 30 days, and users are expected to export before revoking; it is not an active tenant during retention.
- The initial plan allows 1,000 model calls per agent per month, rather than 1,000 inbound messages. Warn at 80%; hard-stop model-dependent work at the limit with a localized response. Verification, `/help`, `/lang`, and exact runner commands such as `export-ledger` remain available. Future plans may vary `maxAgents` and model-call allowance.
- The demo presents plan and subscription UX but takes no real subscription payments and enables no payment provider. Manual JazzCash/Easypaisa confirmation and automated payment rails are later work.
- The initial commercial placeholder is roughly 300 PKR per agent/month with a free first month; this is presentation scope, not a payment integration.

### Environments

- `local`: Firebase Auth, Firestore, and Hosting emulators; local Docker runner/worker; real demo WhatsApp agent and model provider through local secrets; resettable `vault/`; no real payments.
- `dev`: an existing dedicated Firebase project (never production) with the same real demo agent/model integrations; no real payments.
- Empty `vault/` follows first-time setup. `sample-vault/` is a pre-seeded existing-ledger fixture for regression and demo cases.
- Firebase Storage is not in the current worker path. It may later hold backups, exports, or media; local worker state and downloaded media remain on the local filesystem for this scope.
- `config.yaml` remains the existing Gemini model/transcription configuration for normal local commands. Gitignored `config-dev.yaml` selects OpenRouter (`openai/gpt-4.1-mini` plus `openai/gpt-4o-transcribe`) only for `make dev`; Docker receives the selected file through `HISAB_CONFIG`. Gemini remains the rollback.

### Existing Hisab invariants

- Exactly six model tools remain; no shell, free file access, or arbitrary network tool is introduced.
- Every ledger write goes through `Ledger.append` and `hledger check --strict`; rejected blocks roll back.
- Entry numbers remain monotonic across quarter files, undo remains by entry number, and message replay remains idempotent.
- WhatsApp polling keeps the existing message-id deduplication, offset-after-batch rule, and reply chunking limits.
- Ledger conventions remain alphabetic commodities, three-posting transfers with `equity:transfer`, periodic `~ monthly` rules, and `P` rates.

## Testing decisions

- Primary acceptance seam: a real phone interacting with the demo WhatsApp agent through the local or dedicated `dev` portal flow. This proves Firebase login, key submission, nonce verification, worker startup, setup language, ledger writes, quota behavior, revoke, and `export-ledger`.
- Regression seam: `python3 tests/smoke.py` remains the no-network check for setup, strict append/undo/report behavior, store invariants, and transport formatting.
- The local profile is the resettable development loop: wipe/reseed `vault/`, run the emulator services and Docker runner, and use the real model/demo agent. The `sample-vault/` fixture covers existing-ledger paths.
- Before the OpenRouter demo profile is used, `python3 tests/check_endpoint.py --config config-dev.yaml` must report `ALL PASS`.
- Tests must never use a personal ledger, production Firebase project, personal WhatsApp agent, or real payment provider.

## Out of scope

- Real subscription collection, merchant integrations, Stripe, refunds, or payment webhooks.
- Multi-agent/shared-ledger tenancy, owner-plus-cashier workflows, or agent count tiers beyond the future plan fields.
- Ledger contents, charts, balances, or a ledger viewer in the browser.
- Firebase Storage as the canonical ledger/media store.
- CSV as the canonical ledger or an MVP CSV import path.
- Shared wallets, mobile apps, iOS platform support, multi-currency per tenant, and anything required before the hackathon submission.

## Further notes

- Source discussion: [`docs/brainstorm/hosted-portal.md`](../brainstorm/hosted-portal.md).
- The spec deliberately leaves the future payment rail open after the manual/demo phase.
- Durable contract: [Hosted Hisab landing page and portal #1](https://github.com/mhmzdev/hisab-whatsapp/issues/1). Its linked children are the implementation slices; this spec is now temporary.
