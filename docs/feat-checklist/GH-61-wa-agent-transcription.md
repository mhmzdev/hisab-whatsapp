---
type: Checklist
title: GH-61-wa-agent-transcription — acceptance checklist
description: Review of moving voice-note transcription onto wa-agent 0.2.0 through the hisab/wa.py adapter, deleting hisab/transcribe.py and google-genai, against issue #61 and the exec plan.
tags: [checklist, transcription, wa-agent]
timestamp: 2026-09-19T00:00:00Z
---

# GH-61-wa-agent-transcription — acceptance checklist   (10 proven · 4 manual · 0 failing)

Scope: 14 files on `GH-61-wa-agent-transcription`: `requirements.txt`, `hisab/{wa.py,loop.py,config.py}`, `hisab/transcribe.py` (deleted), `runner/config.py`, `tests/{smoke.py,check_endpoint.py}`, `config.example.yaml`, `examples/config.gemini.yaml`, `AGENTS.md`, `ARCHITECTURE.md`, `docs/exec-plans/`. Intent: [#61](https://github.com/mhmzdev/hisab-whatsapp/issues/61) "Done when", plus the plan [GH-61-wa-agent-transcription](../exec-plans/completed/GH-61-wa-agent-transcription.md) and the lead's rulings recorded there.

- [x] `hisab/transcribe.py` is deleted and nothing imports it; the loop and `tests/check_endpoint.py` transcribe through `hisab.wa.transcribe`, which passes `provider`, `model`, `key_env` and `language` explicitly — `test ! -e hisab/transcribe.py`, the import grep is empty, `py_compile tests/check_endpoint.py` passes
- [x] `requirements.txt` pins `wa-agent==0.2.0`; `google-genai` is gone and no Python file imports `genai` — the requirements and `grep -rn genai --include='*.py'` checks
- [x] The system python runs wa-agent 0.2.0 — `python3 -c "import wa_agent; assert wa_agent.__version__ == '0.2.0'"`
- [x] Open point (b) is decided and recorded: `transcription.base_url` is refused at load by the worker and the runner, `api_key_env` is kept (a named key keeps `openrouter` under `auto`), and `base_url` is gone from `DEFAULTS` — `python3 tests/smoke.py` (`config: transcription.base_url refused at load (worker and runner); api_key_env kept`)
- [x] Every wa-agent transcription code (`no_transcription_key`; `transcription_unavailable` from a 503 and from a transport error; `transcription_failed` from a 400 and from an empty body; `bad_usage` from an unreadable file) and an `[inaudible]` transcript map to `transcription_failed`, with `wa-agent <code>` in the detail and no wa-agent text in any reply (en/ur × hosted/self-host) — `python3 tests/smoke.py` (`transcription: every wa-agent code and [inaudible] → transcription_failed; no wa-agent text in any reply`)
- [x] The request shape for both providers is pinned by a fake session: OpenRouter multipart to `/audio/transcriptions`; Gemini inline audio to `models/<gemini_model>:generateContent`. Model, key variable and language come from config — `python3 tests/smoke.py` (`transcription: request shape pinned for openrouter (multipart) and gemini (inline audio); …`)
- [x] An `[inaudible]` voice note sent through the loop and the real adapter replies `transcription_failed`, never calls the model, stores no `[Voice note]: [inaudible]`, and keeps the file for the sweep — `python3 tests/smoke.py` (`errors: an [inaudible] voice note replies transcription_failed and never reaches the model`)
- [x] Docs no longer describe `hisab/transcribe.py` or google-genai as live — the docs grep over `AGENTS.md ARCHITECTURE.md README.md config.example.yaml examples/*.yaml runner/config.example.yaml` is empty; `README.md` ("one key for the model and voice transcription", `check_endpoint.py`) stays true
- [x] wa-agent 0.2.0's new 15th code (`doctor_failed`) still maps to a Hisab chat code at every adapter site — `python3 tests/smoke.py` (`wa-agent: all 15 codes map to Hisab chat codes …`)
- [x] Repo check — `python3 tests/smoke.py` exits 0, `ALL OK`
- [?] The worker image and the runner image build without google-genai. **Not run: the Docker daemon was down at review time.** Owner + lead: `docker build -q -t hisab-whatsapp-gh61 . && docker build -q -f runner/Dockerfile -t hisab-runner-gh61 .`, then `docker image rm hisab-whatsapp-gh61 hisab-runner-gh61`
- [?] Post-merge, phone: on the OpenRouter config, a voice note "five hundred chai cash" on the demo agent replies with a one-line "posted #N"
- [?] Post-merge, phone: the same on the Gemini config
- [?] Post-merge, phone: a voice note with nothing intelligible said (silence or noise) replies with `transcription_failed` and posts nothing

## Conventions
Six tools, untouched. No new network destination: the model, the transcription provider and WhatsApp, as before, with only the client library changed. Ledger writes, dedup, offset and chunking are untouched. No new user-facing string or error code. Nothing personal in the diff; `.env`, `config.yaml` and `vault/` were not touched.

## Findings
None.
