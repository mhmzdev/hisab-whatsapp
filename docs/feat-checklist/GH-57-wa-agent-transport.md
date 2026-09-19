---
type: Checklist
title: GH-57-wa-agent-transport — acceptance checklist
description: Review of moving the WhatsApp transport onto the pinned wa-agent 0.1.0 package (Option 1, transcription unchanged) against issue #57 and the exec plan.
tags: [checklist, transport, wa-agent]
timestamp: 2026-09-19T00:00:00Z
---

# GH-57-wa-agent-transport — acceptance checklist   (11 proven · 3 manual · 0 failing)

Scope: 11 files on `GH-57-wa-agent-transport` (branched from `main` at 5611329): `requirements.txt`, `hisab/{wa.py,loop.py,config.py}`, `tests/smoke.py`, `config.example.yaml`, `AGENTS.md`, `ARCHITECTURE.md`, `runner/README.md`, `docs/exec-plans/`. Intent: [#57](https://github.com/mhmzdev/hisab-whatsapp/issues/57) "Done when", plus the plan [GH-57-wa-agent-transport](../exec-plans/completed/GH-57-wa-agent-transport.md) and the lead's rulings on its findings.

## Proven this run

- [x] `requirements.txt` pins `wa-agent==0.1.0` and a clean venv installs it — fresh venv from `pip install -r requirements.txt` imports `wa_agent` 0.1.0, and `python3 tests/smoke.py` passes **inside that venv** too
- [x] `hisab/wa.py` is a thin adapter (122 lines, previously 239) — `grep -nE "import requests|requests\.|class RateLimiter|def _chunks|api.whatsapp.com" hisab/wa.py` finds nothing
- [x] Every wa-agent failure maps to a Hisab code, and no wa-agent text reaches a reply — `python3 tests/smoke.py` (test: "wa-agent: all 14 codes map to Hisab chat codes at download/send_document/send; no wa-agent text in any reply", en/ur × hosted/self-host), plus the existing "errors: 12 codes registered … no raw detail renders"
- [x] Per-method rate limits from config reach wa-agent; 429 backoff, 409 log and auth vs transient behave as before — smoke ("rate limit: 30 instant polls paced to 60s", "429 backs off ~60s", "409/1752041 logged", "runner: auth failure exits, transient errors retry ok")
- [x] `window_seconds` ≠ 60 is logged, not obeyed; `media_per_min` feeds upload and download — smoke ("rate limit: per-method config limits reach wa-agent; a window other than 60 is logged, not obeyed")
- [x] The export still delivers its ZIP as a document (#36): octet-stream upload, `type: document` with the zip filename and caption, 400/131053 → `export_rejected`, 500 → `export_failed`, detail kept — smoke ("export: octet-stream upload, 131053 -> export_rejected …", "export: whatsapp document send ok")
- [x] Replies still flatten wikilinks and split under `chunk_chars` (3,500) with `(i/N)` — smoke (`parts_for` assertions)
- [x] A failed download replies `media_fetch_failed` with the detail on stderr and leaves no `.part` behind — smoke ("wa-agent: expired media url → media_fetch_failed, no .part left", "errors: media miss …")
- [x] Transcription behaves exactly as before for both providers — `git diff --exit-code main -- hisab/transcribe.py` is empty, and smoke's transcription/voice tests pass
- [x] The loop reads the platform dict only through `inbound()`; dedup by message id and offset-after-batch are unchanged — `grep -nE '\bm\.get\(|\bm\[' hisab/loop.py` finds only the config print at `loop.py:174`; smoke's replay and pending tests pass
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`

## Needs a human

- [?] Terminal mode end to end — **not run**. Smoke already exercises the import graph; the worktree has no `.env`/`config.yaml`, and no key goes into a scratch config.

### Post-merge — owner + lead, left unticked by the lane
- [?] `docker build` with the pinned dependency — **not run: daemon down; owner + lead run it post-merge together with the phone round trip**
- [?] `docker compose up -d --build` on the demo agent, then round-trip: (1) a text (`chai 150 cash` → one-line "posted #N"); (2) a voice note on the OpenRouter config (transcribed and posted); (3) `export-ledger` (the ZIP arrives as a **document** named `hisab-YYYY-MM-DD-HHMM.zip` with its caption); (4) reply-to-undo on the posted entry (undone by number). Lanes never poll the demo agent.

## Conventions

- Surface: six tools unchanged. The only new network path is wa-agent calling the same WhatsApp endpoints. ✓
- Writes: no ledger code touched. ✓
- Transport: dedup, offset-after-batch, chunking under 3,500 and the typing indicator are all kept (`loop.py:188-199, 212`). ✓
- Language: no new user-facing strings; every mapping lands on an existing en/ur code. ✓
- Privacy: the diff has no author paths, tokens or real numbers (only the existing fake `923001234567`); `.env`/`config.yaml`/`vault/` untouched. ✓
- Tests: every new unit is exercised in smoke. ✓
- Docs: `config.example.yaml` comment updated. README — see FINDING-01.

## Findings

FINDING-01 · Minor · README.md:78 — says Hisab "moves onto it next (#57)". That stops being true when this merges (AGENTS.md: README must stay true). The plan's "no README change" missed it. **Fixed** in the review commit: the line now says Hisab runs on it.
FINDING-02 · Minor · tests/smoke.py (rate-limit block) — the `media_per_min` check reads wa-agent internals (`_client.limits._limits`). Safe under the exact pin; a wa-agent limiter refactor would need this assertion updated. The lead accepted it as is.
