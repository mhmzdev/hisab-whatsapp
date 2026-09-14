---
type: Checklist
title: GH-27-failure-replies-error-codes
description: Acceptance checklist for failure replies that say what happened and what to do next, never the raw error — one error-code registry for chat replies and runner lastError codes, plus the .agents/rules convention.
tags: [checklist, errors, i18n, runner, privacy, rules]
timestamp: 2026-09-14T00:00:00Z
---

# GH-27-failure-replies-error-codes — acceptance checklist   (20 proven · 2 manual · 0 failing)

Plan: [GH-27-failure-replies-error-codes](../exec-plans/completed/GH-27-failure-replies-error-codes.md) · Issue: [#27](https://github.com/mhmzdev/hisab-whatsapp/issues/27) · The owner added the central registry and `.agents/rules` to the scope on 2026-09-14. The issue's `roman` strings are dropped because GH-22 removed that language.

## Replies (issue Done-when)
- [x] A model 401 (the real leaked body), a 503/connection failure and an unforeseen `KeyError` each reply with the code's fixed text. No `HTTP`, `{"error"`, `Traceback` or provider name appears; stderr has `error <code> msg=<wamid>` and the raw detail — `python3 tests/smoke.py` ("errors: model/internal failures reply with the code's text…")
- [x] Hosted and self-host differ: self-host `model_auth` names `.env`, hosted says the operator has been told — `python3 tests/smoke.py` ("errors: N codes registered…")
- [x] The model endpoint maps statuses to codes: 401/403 → `model_auth` after 1 try, 400 → `model_rejected` after 1 try, 503 → `model_unavailable` after 4 tries, `ConnectionError` → `model_unavailable` — `python3 tests/smoke.py`
- [x] A voice note whose transcription raises `HTTP 500 {"error"…` gets `err_transcription_failed`, with the detail on stderr only — `python3 tests/smoke.py` ("errors: voice and export failures…")
- [x] A failed export document send gets `err_export_failed`, with the detail on stderr only — same test
- [x] A rejected block names the reason and the offending line, with no `hledger: Error` banner, no file path and no "Consider adding". Tested against the real strict check: undeclared account, unbalanced entry, undeclared commodity. The loop reply reads `Not posted — account "expenses:nope" has not been declared. (expenses:nope PKR 300.00). Reply with the corrected entry.` — `python3 tests/smoke.py` ("errors: rejected block ->")
- [x] Phone (owner, 2026-09-14, hosted `make up` stack, demo agent): connect → `verify` → setup → `500 car fuel` posted #1. With the runner restarted on a bogus `GEMINI_API_KEY`, `500 car fuel` got the hosted `model_auth` reply and a voice note got `err_transcription_failed`, both matched in the runner log by `error <code> msg=wamid…` with the Gemini detail. `export-ledger` got `err_export_failed`; the log shows WhatsApp rejecting `application/zip` (#131053), a separate bug filed as a follow-up

## Registry (owner addendum)
- [x] Every chat code has `err_<code>` in `en` and `ur` with the same placeholders; no orphan `err_*` key; no `{err}` placeholder; nothing in `hisab/` except `errors.py` renders `s("err_…")`; unregistered codes raise — `python3 tests/smoke.py`. Mutation: adding an unstringed `mutant_chat` code fails smoke with `err_mutant_chat: needs en and ur`
- [x] Portal codes come from the registry: `PORTAL_CODES == ("auth",)`, `code_for_exit(3) == "auth"`, exits 1 and 0 map to nothing, and the runner's admission + lastError block is unchanged in behaviour — `python3 tests/smoke.py` ("runner: admission + lastError ok"). Mutation: adding `mutant_portal` (exit 9) makes `tests/check_landing.py` report `no portal_error_mutant_portal`
- [x] `runner/errors.py` is gone and nothing references it — `python3 tests/check_landing.py && ! grep -rn "runner/errors\|runner.errors" …` exits 0
- [x] Worker stderr reaches the operator in hosted mode: `runner/workers.py:10` starts `subprocess.Popen(args, env=env)` with inherited stdio — read, and `errors.log` writes to stderr, proven by the smoke stderr assertions
- [x] `.claude/rules` → `../.agents/rules` and `errors.md` resolves through it — `test "$(readlink .claude/rules)" = "../.agents/rules" && test -f .claude/rules/errors.md`
- [?] Claude Code loads `.agents/rules/errors.md` through the symlink when a matching file is touched — open a fresh Claude Code session, run `/memory` (or ask "which rules are loaded?") after reading `hisab/loop.py`, and expect `.claude/rules/errors.md` to be listed
- [?] Codex/other agents find the rule — open `AGENTS.md`: "Read in this order" item 4 links `.agents/rules/errors.md`
- [x] A tool error on an already-invalid ledger reaches the model cleaned: a broken sample copy's `report month` has `unbalanced` but no banner and no path — `python3 tests/smoke.py` ("errors: media miss, too many steps, and a broken ledger's tool error…") (FINDING-01)
- [x] A 2xx response without `choices` is retried 4 times and then becomes `model_unavailable`, not `internal` — `python3 tests/smoke.py` (FINDING-02)
- [x] A media download miss replies `err_media_fetch_failed` and logs the message id; a tool loop that never ends replies `err_too_many_steps` — `python3 tests/smoke.py` (FINDING-03)
- [x] A 400 whose body names the API key counts as `model_auth` and is not retried. Gemini sends a bad key as `HTTP 400 "Please pass a valid API key"`, not 401. This was found live (see below) — `python3 tests/smoke.py`
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`

## Live, on the `make up` stack (2026-09-14)
- [x] Hosted worker in the runner image, real Gemini endpoint, bogus `GEMINI_API_KEY`: `500 car fuel` → "The AI service isn't accepting requests right now… the operator has been told."; stderr `error model_auth msg=stdin:1: HisabError: model_auth: HTTP 400 …`. The same run in Urdu gives the Urdu text. Before the fix above, this was classified `model_rejected`.
- [x] Self-host config, same bogus key → "The AI service rejected the model key. Check the model key in .env…"; with a real key and an unknown model id → HTTP 404 → `model_rejected` → "…Check the model settings in config.yaml…"; with a real key and a real entry → `posted #37 — car fuel 500 — month out 142,700`
- [x] Voice note, real google-genai client, bogus key → Urdu `err_transcription_failed`; stderr `error transcription_failed msg=wamid.voicetest: ClientError: 400 INVALID_ARGUMENT…`
- [x] Portal end to end: sign in on the emulator with a fake number, paste an invalid WhatsApp key → the runner admits it (`pending`) → the worker gets `HTTP 400, error.code 100` and exits 3 → the runner writes `status='error', lastError='auth'` through `code_for_exit` → the portal shows the `portal_error_auth` banner in Urdu and in English


## Conventions
- Surface: still six tools; no new network call; no tool schema change.
- Writes: `Ledger.append` still rolls back under the strict check; only the message text changed (`hisab/ledger.py:112`).
- Transport: dedup, offset-after-batch, chunking and the typing indicator are untouched. The failed-export reply is now what gets stored as the outbound text, which is more accurate than before, when the caption was stored.
- Language: 12 new `err_*` strings in `en` + `ur`, none in Roman Urdu; replies are one sentence or two.
- Privacy: replies no longer carry hledger paths, HTTP bodies or provider names; tests use the existing fake number; `.env`, `config.yaml` and `vault/` are untouched and ignored.
- Docs: AGENTS.md, ARCHITECTURE.md failure table, runner/landing READMEs and the skills README are updated; no config keys added.

## Findings
FINDING-04 · Important · FIXED · hisab/agent.py:95 — found live: Gemini's OpenAI-compatible endpoint rejects a bad key with HTTP 400 INVALID_ARGUMENT, so it was classified `model_rejected`, and a self-hoster was sent to `config.yaml` instead of `.env`. A 400 whose body matches `api[ _-]?key` is now `model_auth`.
FINDING-05 · Minor · not in this PR · Makefile:106 — `make runner-up` refuses to rebuild while the runner is running. The self-host guard runs `docker compose -f docker-compose.yml ps`, which shares the project name `hisab-whatsapp` with the runner file, so it finds the runner container. Workaround: `make runner-down` first. Worth a separate issue.
FINDING-01 · Important · FIXED · hisab/ledger.py:35 — `Ledger.hledger()` still raises `LedgerError(r.stderr.strip())`, the raw stderr with the `hledger: Error: /abs/path/2026-Q3.md:155-157:` banner. It reaches the model through `tools.call` (`hisab/tools.py:58`) for `report` and similar calls whenever the ledger file is already invalid, e.g. after a hand edit in Obsidian. The model can then repeat the operator's filesystem path to the user, which is the privacy leak #27 closes. Reproduced this run: a broken sample copy's `report month` returned the full path. Fix: route it through `_clean_err` as well.
FINDING-02 · Minor · FIXED · hisab/agent.py:88 — a 2xx response without `choices` (some providers put an error object in a 200 body) raises `KeyError` and replies `internal` ("something went wrong on my side") instead of `model_unavailable`. Nothing leaks, but the next step shown is less accurate. Fix: treat a missing `choices` as `model_rejected`/`model_unavailable` with the body as the detail.
FINDING-03 · Minor · FIXED · tests/smoke.py — `media_fetch_failed` (download returns no path) and `too_many_steps` have no loop-level test; only their strings are checked. Fix: one fake-WA download miss and one `Agent.run` with `max_rounds=0`.
