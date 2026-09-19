---
slug: GH-61-wa-agent-transcription
issue: 61
status: backlog
open_questions: none
---

# feat: Transcribe voice notes through wa-agent, and delete hisab/transcribe.py          ⬜ BACKLOG

## Problem

[#61](https://github.com/mhmzdev/hisab-whatsapp/issues/61). After #57, Hisab talks to WhatsApp through `wa-agent` but still has its own transcription in `hisab/transcribe.py`: OpenRouter over `requests`, Gemini through the `google-genai` SDK. wa-agent 0.2.0 (whatsapp-agent-cli #33/#34) transcribes through OpenRouter and Gemini over plain HTTP. With it, Hisab can drop its copy and the SDK dependency. That leaves one transcription path, as #57 left one transport.

Blocked by wa-agent 0.2.0 reaching PyPI. This plan is written against the 0.2.0 source (`whatsapp-agent-cli` `origin/develop`, `wa_agent/transcribe.py`, `pyproject.toml` version `0.2.0`). `/implement` starts only once the lead confirms 0.2.0 is on PyPI.

## Approach

**The adapter owns it.** `hisab/wa.py` is already the one place that maps wa-agent to Hisab. It gains `transcribe(path, cfg, session=None)`, which calls `wa_agent.transcribe.transcribe` and maps its codes at the boundary using the existing `_detail()` (`hisab/wa.py:62-64`), as `download`/`send`/`send_document` do. `loop.py` imports `transcribe` from `.wa` instead of `.transcribe`, so it is still one module-level name. The smoke tests that monkeypatch `loop_mod.transcribe` (`tests/smoke.py:647-656`, `:708-726`) keep working unchanged. `hisab/transcribe.py` is deleted.

**Lead rulings (decided, recorded here):**

| Point | Decision |
|---|---|
| Provider | Resolved in Hisab (`hisab/config.py` `resolve_providers`, auto → `openrouter`/`gemini`), always passed explicitly as `provider=`. wa-agent never guesses. |
| Model | Passed explicitly as `model=`: `transcription.model` for openrouter, `transcription.gemini_model` for gemini. An upstream default change can never change Hisab. |
| Language | Passed explicitly: `language=transcription.language` (default `None`, so nothing is sent). OpenRouter receives it as the multipart `language` field, as today. Gemini now receives it as a prompt hint ("The speaker is using ur."). Before, Hisab's Gemini path ignored it. The `config.example.yaml` comment says so. |
| `transcription.api_key_env` | **Kept.** Passed as wa-agent's `key_env=` (`None` → the provider's own variable, `OPENROUTER_API_KEY` / `GEMINI_API_KEY`). It now applies to both providers. Hisab's Gemini path used to ignore it. |
| `transcription.base_url` | **Dropped.** Removed from `DEFAULTS`. A config that sets it fails at load with a `SystemExit` that names the key and says to remove it, in both `hisab/config.py:load` and `runner/config.py:load`, next to the existing provider check (`hisab/config.py:45-49`, `runner/config.py:35-38`). One helper, `check_transcription(tc)`, lives in `hisab/config.py` and the runner imports it (the runner already imports `PROVIDERS` from there). This refuses to start rather than quietly sending voice notes somewhere else. |
| Auto resolution (`hisab/config.py:86-88`) | `base_url` leaves the condition. `transcription.provider: auto` with `api_key_env` set still resolves to `openrouter`, because an explicitly named key is never second-guessed by which keys happen to be in `.env` (the rule in the `DEFAULTS` comment at `:19-20`). Otherwise: Gemini only when `_auto(env)` says gemini, else openrouter. The comment is rewritten to say that. |
| Code mapping | Every `WhatsAppError` that `wa_agent.transcribe.transcribe` can raise (`no_transcription_key`, `transcription_unavailable`, `transcription_failed`, `bad_usage`) → `HisabError("transcription_failed", _detail(e))`. That is the only Hisab chat code for this site, and its reply ("send it as text, or try again") is right for all four. No new code or string. The operator tells them apart by the `wa-agent <code>:` prefix on stderr. |
| `[inaudible]` | A transcript that is exactly `[inaudible]` (after `strip()`, a trailing `.` removed, compared case-insensitively) → `HisabError("transcription_failed", "wa-agent transcript: [inaudible]")`. It never reaches the model as `[Voice note]: [inaudible]`. A transcript that only *contains* `[inaudible]` among real words passes through, because partial speech is still useful. |
| `google-genai` | Dropped from `requirements.txt`. `hisab/transcribe.py:43-44` is its only importer (`grep -rn genai --include='*.py' .` hits nothing else). |
| Pin | `wa-agent==0.1.0` → `wa-agent==0.2.0`. `requests>=2.32` stays: `agent.py` and `tests/check_endpoint.py` use it. |

The adapter code shape (the decision, not a draft to re-decide):

```python
from wa_agent.transcribe import transcribe as _transcribe

def transcribe(path, cfg, session=None):
    """Voice note → text through wa-agent (#61). Provider, model, key variable and language come from Hisab's config,
    always explicitly; every wa-agent failure, and an [inaudible] transcript, is transcription_failed."""
    tc = cfg["transcription"]
    provider = tc["provider"]
    model = tc.get("gemini_model") if provider == "gemini" else tc.get("model")
    try:
        text = _transcribe(path, provider=provider, model=model, key_env=tc.get("api_key_env") or None,
                           language=tc.get("language") or None, session=session)
    except WhatsAppError as e:
        raise errors.HisabError("transcription_failed", _detail(e)) from e
    if text.strip().rstrip(".").lower() == "[inaudible]":
        raise errors.HisabError("transcription_failed", "wa-agent transcript: [inaudible]")
    return text
```

`session=` exists for smoke's fake session only. The loop calls `transcribe(path, self.cfg)`, the same two-argument call as today (`hisab/loop.py:224`). The loop's catch-all `errors.classify(e, default="transcription_failed")` (`:226`) still covers anything that is not a `WhatsAppError`, such as an `OSError`.

**Invariants kept:** six tools (untouched); strict check and entry numbers (untouched); offset-after-batch and dedup (untouched). Failures are codes: no wa-agent text, HTTP body or provider name in a reply, and smoke's `FORBIDDEN_WA` check covers it. No new user-facing string. Privacy: the network surface is the same (the model, the transcription provider, WhatsApp). Only the client library changes.

## Success criteria

- [ ] `hisab/transcribe.py` is deleted, and nothing imports `hisab.transcribe` — `verify: test ! -e hisab/transcribe.py && ! grep -rn "hisab.transcribe\|from .transcribe" --include='*.py' .`
- [ ] `requirements.txt` pins `wa-agent==0.2.0` and no longer lists `google-genai`, and no Python file imports `genai` — `verify: grep -qx 'wa-agent==0.2.0' requirements.txt && ! grep -q genai requirements.txt && ! grep -rn genai --include='*.py' .`
- [ ] The installed wa-agent is 0.2.0 on the system python — `verify: python3 -c "import wa_agent; assert wa_agent.__version__ == '0.2.0', wa_agent.__version__"`
- [ ] `transcription.base_url` in a config fails at load with a message naming it, in both the worker and the runner config. `transcription.api_key_env` with `provider: auto` resolves to openrouter even when only `GEMINI_API_KEY` is set. `base_url` is gone from `DEFAULTS` — `verify: python3 tests/smoke.py` (prints `config: transcription.base_url refused at load (worker and runner); api_key_env kept`)
- [ ] Every wa-agent transcription code (`no_transcription_key`, `transcription_unavailable` from a 503 and from a transport error, `transcription_failed` from a 400 and from an empty body, `bad_usage` from an unreadable file) and an `[inaudible]` transcript map to `transcription_failed`. The detail carries `wa-agent <code>`, and the reply in en/ur × hosted/self-host has none of `FORBIDDEN_WA` or the wa-agent code — `verify: python3 tests/smoke.py` (prints `transcription: every wa-agent code and [inaudible] → transcription_failed; no wa-agent text in any reply`)
- [ ] The request shape for both providers is pinned by a fake session. OpenRouter: one `POST` to `https://openrouter.ai/api/v1/audio/transcriptions` with `Authorization: Bearer <key from api_key_env>`, multipart `data` `{"model": <transcription.model>, "language": "ur"}` and `files["file"] == (name, bytes)`. Gemini: one `POST` to a URL containing `models/<transcription.gemini_model>:generateContent` with `x-goog-api-key`, whose JSON part has `inline_data.mime_type == "audio/ogg"` and base64 of the file bytes — `verify: python3 tests/smoke.py` (prints `transcription: request shape pinned for openrouter (multipart) and gemini (inline audio); model, key variable and language from config`)
- [ ] A voice note whose transcript is `[inaudible]` gets the `transcription_failed` reply through the loop. The agent is never called, the store holds no `[Voice note]: [inaudible]`, and the voice file is kept for the sweep — `verify: python3 tests/smoke.py` (prints `errors: an [inaudible] voice note replies transcription_failed and never reaches the model`)
- [ ] `tests/check_endpoint.py` transcribes through the adapter and still parses — `verify: grep -q "from hisab.wa import transcribe" tests/check_endpoint.py && python3 -m py_compile tests/check_endpoint.py`
- [ ] Docs no longer describe `hisab/transcribe.py` or google-genai as live — `verify: ! grep -n "transcribe\.py\|google-genai" AGENTS.md ARCHITECTURE.md README.md config.example.yaml examples/*.yaml runner/config.example.yaml`
- [ ] The worker image and the runner image build with the new requirements, without google-genai — `verify: docker build -q -t hisab-whatsapp-gh61 . && docker build -q -f runner/Dockerfile -t hisab-runner-gh61 .` (build only, no `compose up`, no container started; every `docker-compose.runner*.yml` builds from `runner/Dockerfile`; if the Docker daemon is down, report it as not run)
- [ ] Repo check passes — `verify: python3 tests/smoke.py`
- [ ] **Post-merge, owner + lead (left unticked by the lane):** (1) on the OpenRouter config, a voice note "five hundred chai cash" round-trips on the demo agent to a one-line "posted #N"; (2) the same on the Gemini config; (3) a voice note with nothing intelligible said (silence or noise) replies with `transcription_failed` and posts nothing — `verify: manual` on the demo agent

## Phases

### Phase 1 — Pin 0.2.0; config drops `transcription.base_url`

**Status:** Not started

- Precondition: the lead has confirmed wa-agent 0.2.0 is on PyPI. `python3 -m pip install --upgrade wa-agent==0.2.0` on the system python (3.11), with no `--break-system-packages`. If pip refuses without that flag, stop and ask the lead.
- Files:
  - `requirements.txt:2` → `wa-agent==0.2.0`. `requirements.txt:4` (`google-genai>=1.0`) is removed in Phase 2, together with its only importer, so every phase's smoke run stands on its own.
  - `hisab/config.py:22`: remove `"base_url": None` from the `transcription` defaults.
  - `hisab/config.py`: add `check_transcription(tc)` beside `load`. If `tc.get("base_url")` is set, raise `SystemExit("transcription.base_url is no longer supported: voice notes go to OpenRouter or Gemini only (transcription.provider). Remove it from the config.")`. Call it in `load` right after the provider loop (`:45-49`).
  - `hisab/config.py:86-88`: the condition becomes `tc.get("api_key_env")` alone. Replace the comment with: "an explicitly named key variable is never second-guessed by which keys are present: it keeps the openrouter default; otherwise Gemini only when it is the one key present".
  - `hisab/config.py:19-20` (the `DEFAULTS` comment): "an explicit base_url/api_key_env" → "an explicit model base_url/api_key_env, or transcription api_key_env".
  - `hisab/config.py:26`: the "fixed at 60 by wa-agent 0.1.0" comment → "by wa-agent" (still true in 0.2.0: `ratelimit.py` is unchanged between the two). Same edit at `hisab/wa.py:73` (the log line), `config.example.yaml:32` and `tests/smoke.py:202`.
  - `runner/config.py:8`: import `check_transcription` as well. Call it after the provider loop (`:35-38`), so a runner config that sets it refuses to start instead of every tenant worker crash-looping at load.
  - `tests/smoke.py:303`, `:823`: drop `"base_url": None` from the two fixture `transcription` dicts, so they match the new shape.
- Test (`tests/smoke.py`, after the `custom` assertion at `:44`):
  - `keyed = _resolved(transcription={"api_key_env": "MY_STT_KEY"}, GEMINI_API_KEY="g")` → `keyed["transcription"]["provider"] == "openrouter"`.
  - Write `transcription:\n  base_url: https://example.test/v1\n` to a temp config. `cfgmod.load` raises `SystemExit` whose text contains `transcription.base_url`. In the runner-config block (`:774-781`), the same yaml through `runner_cfgmod.load` also raises.
  - `"base_url" not in cfgmod.DEFAULTS["transcription"]`.
  - Print `config: transcription.base_url refused at load (worker and runner); api_key_env kept`.
- Verify: `python3 tests/smoke.py`. `hisab/transcribe.py` still exists and still uses `base_url` via `tc.get` (`None` now), so voice behaviour is unchanged in this phase.

### Phase 2 — The adapter transcribes; `hisab/transcribe.py` and google-genai go

**Status:** Not started

- Files:
  - `hisab/wa.py`: add `from wa_agent.transcribe import transcribe as _transcribe` and the `transcribe(path, cfg, session=None)` shown in Approach. Extend the module docstring (`:1-7`): the adapter also turns config into a transcription call and maps its codes.
  - `hisab/loop.py:18` removed. `:19` becomes `from .wa import MAX_DOCUMENT_BYTES, AUTH_EXIT_CODE, AuthError, inbound, transcribe`. `:224-227` unchanged.
  - Delete `hisab/transcribe.py`.
  - `requirements.txt`: remove `google-genai>=1.0`.
  - `tests/check_endpoint.py:13` → `from hisab.wa import transcribe`. `:64` is unchanged (`transcribe(audio, cfg)`). `:67`'s `str(e)[:200]` now prints `transcription_failed: wa-agent <code>: <detail>`. That is operator output, where the detail belongs. Docstring line 5: "one transcription probe through wa-agent".
- Tests (`tests/smoke.py`, a new block after the wa-agent code-map block ending `:236`, reusing `FakeResponse`, `FORBIDDEN_WA`, `wa_mod`; add `base64` to the imports at `:2`):
  - A `RecordingSession`: `transport_errors = (ConnectionError,)`; `request(verb, url, headers=None, **kw)` appends `(verb, url, headers, kw)` and returns a queued response or raises a queued exception.
  - Env: `os.environ["HISAB_SMOKE_STT_KEY"] = "k-smoke"`, popped in a `finally`. Configs: `or_cfg = {"transcription": {"provider": "openrouter", "model": "openai/whisper-1", "gemini_model": "gemini-2.5-flash", "api_key_env": "HISAB_SMOKE_STT_KEY", "language": "ur"}}` and `gem_cfg`, the same with `provider: gemini`. Audio: `tmp / "stt.ogg"` with bytes `b"OggS-smoke"`.
  - Shape, OpenRouter: response `FakeResponse(200, {"text": "500 chai"})` → returns `"500 chai"`. Exactly one call: `verb == "POST"`, `url == wa_agent.transcribe.OPENROUTER_URL`, `headers["Authorization"] == "Bearer k-smoke"`, `kw["data"] == {"model": "openai/whisper-1", "language": "ur"}`, `kw["files"]["file"] == ("stt.ogg", b"OggS-smoke")`.
  - Shape, Gemini: response `FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "500 chai"}]}}]})` → `"500 chai"`. `"models/gemini-2.5-flash:generateContent" in url`, `headers["x-goog-api-key"] == "k-smoke"`, and `kw["json"]["contents"][0]["parts"][0]["inline_data"] == {"mime_type": "audio/ogg", "data": base64.b64encode(b"OggS-smoke").decode()}`.
  - Print `transcription: request shape pinned for openrouter (multipart) and gemini (inline audio); model, key variable and language from config`.
  - Codes. Each case → `HisabError` with `code == "transcription_failed"` and `f"wa-agent {wa_code}" in e.detail`; every `errors.reply("transcription_failed", lang, hosted)` over en/ur × True/False has no `FORBIDDEN_WA + (wa_code,)` token. Cases:
    - `no_transcription_key`: `api_key_env: "HISAB_SMOKE_MISSING_KEY"`; the session is never called.
    - `transcription_unavailable`: a 503, and separately a raised `ConnectionError`.
    - `transcription_failed`: a 400, and separately a 200 `{"text": ""}`.
    - `bad_usage`: a `tmp / "stt.xyz"` file.
    - `[inaudible]`: 200 `{"text": "[inaudible]"}` and 200 `{"text": " [Inaudible]. "}` → `transcription_failed`, `"[inaudible]" in e.detail`.
    - Assert `{"no_transcription_key", "transcription_unavailable", "transcription_failed", "bad_usage"}` are all seen.
    - Print `transcription: every wa-agent code and [inaudible] → transcription_failed; no wa-agent text in any reply`.
  - Loop, `[inaudible]` (beside the voice test at `:641-658`): monkeypatch `wa_mod._transcribe = lambda path, **kw: "[inaudible]"` (restore in `finally`). Leave `loop_mod.transcribe` real, so the call goes through the adapter. Set `voice_app.agent = RaisingAgent(AssertionError("model must not be called"))`. Use a fresh audio file in `voice_app.media_dir`, then `_handle_wa` an audio message → `wa.sent[-1][2] == errors.reply("transcription_failed", "en")`. No store line contains `[inaudible]` (read `messages.jsonl`); the file still exists. Stderr has `error transcription_failed msg=`. Print `errors: an [inaudible] voice note replies transcription_failed and never reaches the model`.
- Verify: `python3 tests/smoke.py`; `test ! -e hisab/transcribe.py`; `! grep -rn genai --include='*.py' .`; `python3 -m py_compile tests/check_endpoint.py`.

### Phase 3 — Docs and the image

**Status:** Not started

- Files:
  - `AGENTS.md:33`: remove the `transcribe.py` row. In the `wa.py` row (`:34-38`), add "and transcription (voice notes → text, OpenRouter or Gemini, provider/model/key/language from config)" to what wa-agent owns, and "maps transcription codes and an `[inaudible]` transcript to `transcription_failed`" to what the adapter does.
  - `ARCHITECTURE.md:32`: `transcribe.py (OpenRouter endpoint | Gemini)` → `wa.py → wa-agent (OpenRouter | Gemini)`. Remove the `:73` row, and add "voice → text" to `wa.py`'s row. The `:113` failure row gains "(also an `[inaudible]` transcript)".
  - `config.example.yaml:18-22`: `model:` comment → "openrouter provider"; add `# api_key_env: null  # env var holding the transcription key; null = the provider's own (OPENROUTER_API_KEY / GEMINI_API_KEY)` (commented out, as it is optional); `language:` comment → "null = auto; a code like 'ur' pins it (OpenRouter's language field, a hint to Gemini)". There is no `base_url` line to remove.
  - `examples/config.gemini.yaml:1`: "with google-genai for voice notes" → "voice notes through the same key". Check `examples/config.openrouter.yaml:16-18`, `examples/runner-config.openrouter.yaml:21-` and `runner/config.example.yaml:29-` for any transcription `base_url` (the scoping found none) and leave them otherwise.
  - `docs/exec-plans/INDEX.md`: `/implement` moves the row.
- Verify: `python3 tests/smoke.py`; the docs grep in Success criteria; both `docker build` lines from Success criteria (build only; `docker image rm hisab-whatsapp-gh61 hisab-runner-gh61` afterwards).

## Major Impact (for /open-pr)

- Gemini voice notes move from the google-genai SDK to wa-agent's plain HTTP, and use wa-agent's prompt. That prompt adds "no preamble" and the `[inaudible]` instruction, and Hisab now turns an `[inaudible]` transcript into `transcription_failed`.
- `transcription.language` now reaches Gemini as a prompt hint. Before, only OpenRouter received it. It defaults to null, so nothing changes unless a config sets it.
- `transcription.api_key_env` now applies to both providers. `transcription.base_url` is refused at load by the worker and by the runner.
- `google-genai` leaves the worker and runner images.

## Risks

- **An audio mime wa-agent cannot name → `bad_usage`.** wa-agent's download names the file from its mime (`media.py` `EXTENSIONS`: ogg, m4a, aac, mp3, amr), and every one of those is in `transcribe.MIME_BY_EXT`. An unlisted audio mime gets no extension and now fails as `transcription_failed`, where Hisab's Gemini path used to guess `audio/ogg`. WhatsApp voice notes are `audio/ogg; codecs=opus`, so this is theoretical. The stderr detail names it if it happens.
- **`api_key_env` set to an empty variable no longer falls back to `OPENROUTER_API_KEY`** (the old `hisab/transcribe.py:19` fell back). The named variable is what's read. No shipped config sets it.
- **Gemini transcripts change prompt.** wa-agent's prompt adds "no preamble" and the `[inaudible]` line. The first is the behaviour we want. The second is handled here. The post-merge Gemini round-trip is the check.
- **pip on the system python.** If `pip install --upgrade wa-agent==0.2.0` needs `--break-system-packages`, stop and ask. Do not add the flag.

## Out of scope

- A custom transcription endpoint (`base_url`). Dropped by ruling. Bringing it back needs a wa-agent base-URL option first.
- New chat codes for a missing transcription key (a separate "operator has been told" reply). It stays `transcription_failed`, which is honest for all four causes. Split it later if the post-merge checks show a need.
- Offline transcription (whatsapp-agent-cli #20).
- Any live run: `docker compose up`, `make up`, `python -m hisab.loop` polling, or a real OpenRouter/Gemini call. These are post-merge checks for the owner and the lead.
