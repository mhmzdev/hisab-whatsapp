---
type: Brainstorm
title: Hosted Hisab — landing page + portal
description: The roadmap after the hackathon — a small SaaS where a shop owner signs up with a phone number, pastes their WhatsApp agent key, and we run their Hisab worker on our VPS. Decided 2026-09-12, roadmap only for the hackathon.
tags: [brainstorm, hosted, portal, roadmap]
timestamp: 2026-09-12T08:00:00Z
status: leaning
---

# Hosted Hisab — Brainstorm

**Hackathon position (decided):** roadmap only. One line in the README and the written description; a five-second portal still in the video **only** if the UI exists by 15:00 on the day. Nothing in the demo claims a hosted service. The self-host story stays the product that is judged.

## Problem

The shop owner cannot run Docker, and the relative who could is not always there. Today the only route to a non-technical user is a technical relative running the container. Every Pakistani kiryana, committee treasurer or rider with an Android phone is one paste away from a ledger — if someone else runs the process.

## Goal

A person with an Android phone signs up on a page, pastes the key from their WhatsApp agent, and within a minute their agent greets them in Urdu or English and setup begins. We run the worker. They never see a terminal.

## What changes from the self-host claim, said plainly

Hosted means **we hold the key and the ledger**. The "no server of ours, private by platform" line is true for self-host and not for hosted. Hosted users get a different, honest sentence: *your key and ledger live on our server, encrypted, and you can take the ledger and revoke the key any time.* Never blur the two.

**Trust boundary (locked during grill):** the hosted MVP deliberately makes Hisab a trusted custodian. The VPS must be able to decrypt and use a tenant's key and ledger while that tenant's worker runs. Encryption at rest, access controls, revoke, and retention limits are safeguards around that custody—not a claim that the operator cannot technically access plaintext at runtime.

## The flow

1. **Landing page** → *Get started* opens the sign-up modal.
2. **Account** = phone number, Firebase phone auth (SMS OTP). Chosen over Google or email because the long-run user is a layman in Pakistan; a phone number is the identity they already have.
3. **Connect the agent.** The portal asks for the agent's name and the API key from WhatsApp → Settings → Agents → Chat info. It writes a tenant document to Firestore. The key is **never shown again** after entry.
4. **Prove ownership without Meta Business or a second OTP service.** The VPS runner picks up the new tenant and sends a six-digit challenge **through the user's own agent** to its creator (the API allows unprompted sends to the creator). The user replies with the verification text through that same WhatsApp conversation; the runner matches the challenge and reply, which proves control of the agent and hands us the creator id. No Meta Business API, no external SMS OTP service, no second phone verification.

The reply is a fixed, machine-readable command carrying the nonce (for example, `verify 482913`), matched case-insensitively with a short expiry; a bare six-digit number is not accepted as proof.

Language is not selected before verification. Pending-state reminders therefore stay language-neutral (with the three supported language labels), and the first post-verification interaction remains the existing setup's language question; all later replies follow that choice.

**Authentication contract (locked during grill):** Firebase Phone Auth proves control of the portal phone number and establishes the tenant's Firebase `uid`. Separately, the runner generates the short-lived nonce and accepts only the fixed `verify <nonce>` reply from the agent creator, binding that verified agent to the `uid`. The WhatsApp API key is never a browser login credential; it is submitted only for this connection flow and kept server-side thereafter.

**Submission/storage contract (locked during grill):** the portal encrypts the WhatsApp API key client-side with a runner-held public key (sealed-box/envelope encryption). Firestore stores only the ciphertext; the runner alone holds the private key needed to decrypt it. No public VPS ingestion endpoint or Firebase Function is required for the MVP.
5. **Welcome, in both languages, from the agent itself.** On verification the worker sends one message and then the existing in-chat setup takes over (language first, then the questions):

   > *Hisab is connected · حساب جڑ گیا*
   > Send anything to begin — a number, a voice note, a receipt photo. Reply *English*, *اردو* or *Roman Urdu* to choose your language.
   > شروع کرنے کے لیے کچھ بھی بھیجیں — رقم، وائس نوٹ، یا رسید کی تصویر۔ زبان چننے کے لیے *English*، *اردو* یا *Roman Urdu* لکھیں۔

6. **Portal after that** shows only: agent name, *connected since*, last activity time, entries this month, language, a *Send me my ledger* hint, and **Revoke key**. No ledger contents in the browser.
7. **The ledger stays on the VPS disk.** *"send me my ledger"* in WhatsApp sends the folder as a document (WhatsApp media, 16 MB cap). Mirroring to Firebase Storage is a later line, not this one.

For MVP, that document is a ZIP ledger bundle containing `hisab.md`, all included quarter files, `accounts.md`, `rules.md`, and `settings.json`. It never contains the API key/ciphertext, `.env`, worker state, message history, or downloaded media. The worker creates it locally and uploads it as a WhatsApp document; it is not rendered as ordinary chat text.

## Tenancy on the VPS

- One worker process per tenant, each long-polling its own agent (the platform allows one poller per agent; workers never share a key).
- Launch tenancy is one agent and one ledger per Firebase account/plan. A person who wants both a personal and shop ledger creates two agents.
- A **runner** holds one Firestore snapshot listener on `tenants` — one open connection, zero polling reads, so Firestore quotas are not a factor — and starts, stops or restarts a worker when a document changes. No public endpoint on the VPS.
- Keys are encrypted at rest with a secret that exists only on the VPS. Firestore holds the ciphertext. Revoke = delete the ciphertext, stop the worker, leave the ledger for 30 days, then delete.
- **Firestore is control-plane metadata, not the ledger:** it maps the Firebase `uid` to tenant status, encrypted key, creator and activity metadata so the runner can reconcile workers. The canonical accounting data remains the hledger markdown folder on the worker's disk.
- **Revoke (locked during grill):** stop the worker immediately and delete the encrypted key. Keep the ledger folder for the proposed 30-day retention window, but do not treat it as an active tenant; users should export before revoking.
- Model cost is ours: one OpenRouter key, a per-tenant monthly quota, replies degrade to *"limit reached this month"* rather than failing silently.
- Sizing: a worker idles on a 20-second long-poll and wakes per message. A 1 GB box carries dozens; the ceiling is memory, not CPU.

## Money

Paid SaaS, roughly **300 PKR per month per agent**, to cover the VPS, SMS auth and model cost. Free first month. Payment rail is the open question (below); the first tenants pay by JazzCash or Easypaisa transfer confirmed by hand, which is itself a Hisab entry.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Landing + portal | **Next.js, static export**, in this repo under `landing/` | Your preference; static export runs on Firebase Hosting; nothing in the flow needs server rendering |
| Hosting | Firebase Hosting (Blaze plan — phone auth needs it; the free allowance covers this traffic) | Same project as auth and Firestore, no second vendor. Vercel is the equivalent if Hosting ever bites |
| Auth | Firebase phone auth | The identity a layman already has |
| Data | Firestore: `tenants/{uid}` = {agentName, keyCiphertext, creatorId, status, language, plan, createdAt, lastSeenAt, entriesThisMonth} | Client writes under rules that only allow the owner; the VPS reads with a service account |
| Functions | **None yet** | Verification, welcome and the worker all live on the VPS runner |
| Worker | This repo's `hisab` package, unchanged, one process per tenant | The product is the same code |

Development uses the Firebase Local Emulator Suite for Auth, Firestore, Hosting and their rules, run locally in Docker alongside the portal and runner. The Auth emulator supports phone/SMS flows but prints test codes locally instead of sending carrier SMS; production SMS behavior remains a deployment check. The emulators are for development and integration testing, never production custody.

Local mapping: Firebase Auth and Firestore use their emulators; the static portal uses the Hosting emulator; the runner and one-worker-per-tenant processes run locally in Docker; WhatsApp uses the fake adapter by default (with an opt-in real-agent profile); the ledger is a mounted local `vault/` or `sample-vault/`; and worker state/media use the local data directory. Firebase Storage is not in the current worker path, but its emulator can be added when hosted media/export storage is introduced.

## Branding

WhatsApp **green palette**, light and dark, no logo, no "WhatsApp" in the product name. The name is Hisab.

## Pages (for whenever the UI is built)

**Landing** — hero: *A ledger you text* with a phone mock showing three real replies; three cards: text · voice note in Urdu · receipt photo; a "why not a chatbot" strip (undo is a reply, every line links to its message); pricing block (300/month, first month free); *Get started*; footer with the self-host link to the repo.

**Sign-up / login modal** — phone number → OTP → done. One modal, two states.

**Portal** — three states: *Connect your agent* (name + key fields, the four-step how-to with a screenshot of the WhatsApp settings path) → *Check your WhatsApp* (waiting for the six-digit code) → *Connected* (the status card above, Revoke).

## Surfaces touched

landing/ (new) · a `runner/` on the VPS (new, small) · `hisab/` unchanged except a `send me my ledger` command · Firestore rules · README roadmap line.

## Open questions

- [ ] Payment rail after the manual phase: JazzCash/Easypaisa merchant, or Stripe via a foreign entity.
- [ ] Quota per tenant per month, and what "limit reached" says.
- [ ] Ledger retention after revoke (30 days proposed).
- [ ] Whether a tenant can have two agents (owner + cashier on one ledger) — the platform allows it, the runner design allows it, pricing does not yet.

## Out of scope (YAGNI)

Shared wallets · a ledger viewer in the browser · charts · a mobile app · iOS (platform) · multi-currency per tenant · anything before the hackathon submission.

## Links

- Scope and decisions that this sits after: the self-host product in [`README.md`](../../README.md) and [`ARCHITECTURE.md`](../../ARCHITECTURE.md).
- Next step when this is picked up: `/grill-me docs/brainstorm/hosted-portal.md`, then `/to-spec`.
