---
type: Checklist
title: GH-5-connected-status-revoke — acceptance checklist
description: Review of the live Connected screen, revoke, re-admission and retention against issue #5 and the exec plan.
tags: [checklist, hosted-hisab, runner, portal]
timestamp: 2026-09-13T00:00:00Z
---

# GH-5-connected-status-revoke — acceptance checklist   (9 proven · 1 manual · 0 failing · 2 findings fixed)

Scope: 19 files on branch `GH-5-connected-status-revoke` (based on the GH-7 tip, 37fa8ca): new `runner/activity.py`, `runner/lifecycle.py`; `runner/{config.py,config.example.yaml,main.py,reconcile.py,workers.py,README.md}`; `firestore.rules`, `tests/rules/tenants.test.js`; `landing/app/portal/page.jsx`, `landing/content/{strings.json,mock.js}`, `landing/README.md`; `README.md`, `AGENTS.md`, `Makefile`; `tests/smoke.py`; the plan and the two indexes. `hisab/` is untouched.

- [x] `runner/activity.py` computes `lastSeenAt` from the last inbound, `entriesThisMonth` from `n:` lines dated this month (last month's entry not counted, a missing quarter file is 0), `language` from `settings.json` (`None` before setup), `usedThisMonth`/`quotaLimit` from `usage.json` and the runner config — `python3 tests/smoke.py` → `runner: activity ok`.
- [x] Two activity passes over unchanged files produce no second write; a new inbound produces one — same test (`poll_activity` returns `{}` on the echoed snapshot, then the uid with a newer `lastSeenAt`).
- [x] A running tenant carrying `revokeRequestedAt` is stopped with a bounded wait, its vault and state move under `inactive_root/<uid>/<ts>/` with `revoked.json`, its per-tenant config is deleted, the write sets `status: "revoked"`/`revokedAt` and deletes the key, creator, nonce, `connectedAt`, the request and every activity field; a second pass is a no-op — `python3 tests/smoke.py` → `runner: revoke + retention ok`.
- [x] A `revoked` document with a new decryptable `keyCiphertext` is re-admitted as `pending` with `revokedAt` (and a stale `revokeRequestedAt`) cleared, and its worker starts on an empty vault — same test.
- [x] `sweep_inactive()` removes only marked dirs older than `retention_days`, keeps a younger one and an unmarked one, removes an emptied uid dir, and tolerates a missing `inactive_root` — same test.
- [x] An owner can write `revokeRequestedAt` on its own document and still cannot write `status`, `revokedAt` or `creatorId`, cannot delete the document, and can resubmit the client fields over a revoked document; another uid cannot request a revoke — `make rules-test` → 6/6 pass (2026-09-13).
- [x] Five new portal strings in `en`/`ur`/`roman`; `landing/content/mock.js` carries no activity, entries or quota values — `python3 tests/check_landing.py` (inside smoke) → `landing: ok`; `grep -E 'lastActivity|entriesThisMonth|quotaUsed' landing/content/mock.js` → nothing.
- [x] `landing/` exports both routes — `cd landing && npm run build` → `out/index.html`, `out/portal/index.html` (2026-09-13).
- [?] End to end against the demo agent. The emulator half was run on 2026-09-13 with a tenant seeded as the emulator owner and worker files simulated: the Connected rows went live within 10 s ("12 minutes ago", 2 entries, Urdu, 2 / 1000); Revoke → Revoked in ~5 s with the worker stopped, the document stripped to `agentName`/`createdAt`/`status`/`revokedAt`, and the ledger under `runner-data/inactive/<uid>/<ts>/`; "Connect an agent" → a new key → `pending` with `revokedAt` cleared → (a deliberately bad key) `error` with the `portal_error_auth` banner. Still manual, on the phone: 1) `make landing && make emulators`, then `make runner-up` 2) connect and `verify <nonce>` as in #7, answer setup, post `2500 chai` and `300 coffee` 3) portal shows Entries this month 2 and the chosen language 4) Revoke; the agent no longer answers `500 tea` 5) Connect an agent, paste the real key, send the new code: welcome arrives and setup starts from the language question on a fresh ledger.
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`.

## Conventions

- **Surface.** Six tools unchanged; `hisab/` has no diff. The runner's new file reads (`activity.py`, `lifecycle.py`) are control-plane code on the runner's own disk; no new network surface, no Firebase in the worker.
- **Writes / transport.** No ledger code touched; the activity pass only reads the quarter file. The worker is stopped from outside via SIGTERM with a bounded wait, so the vault is never moved under a live process.
- **Language.** `portal_connected_not_yet`, `portal_connected_revoking`, `portal_lang_en/ur/roman` in three languages. No new `i18n.py` string: the worker says nothing new.
- **Privacy.** Activity fields are a count, a timestamp, a language code and a quota — never a description or an amount. Fixtures use fake uids and `demo-hisab`. The moved vault stays on the runner's disk; nothing from it reaches Firestore. `.env`, `config.yaml`, `runner/config.yaml`, `vault/`, `runner-data/` untouched and ignored.
- **Tests.** Every new unit is in `tests/smoke.py` (`runner: activity ok`, `runner: revoke + retention ok`); the rules gained a sixth case; `FakeProc` grew `wait`/`kill`.
- **Docs.** `runner/config.example.yaml` documents `inactive_root` and `retention_days`; `runner/README.md` lifecycle table, activity/retention paragraph and Layout; `landing/README.md` screen table; `README.md` hosted paragraph; `AGENTS.md` repo map; `Makefile` help line.

## Findings

FINDING-01 · Important · Fixed · `runner/config.py` — a `runner/config.yaml` written before `inactive_root` existed resolved the default `./runner-data/inactive` relative to `runner/`, which inside the container is outside the compose mount: the "retained" ledger would vanish on the next image build. Seen on the emulator run. The default now sits beside the resolved `vault_root`; an explicit value still resolves relative to the config file. Smoke asserts both.

FINDING-02 · Minor · Fixed · `runner/reconcile.py` `admission()` — a client can leave `revokeRequestedAt` on a revoked document (it is a client field); re-admitting without clearing it would revoke the fresh connection on the next tick. Admission now deletes it alongside `revokedAt`; smoke asserts the next `poll_revokes` pass is a no-op.
