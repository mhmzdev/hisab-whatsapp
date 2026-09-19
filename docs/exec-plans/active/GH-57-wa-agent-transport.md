---
slug: GH-57-wa-agent-transport
issue: 57
status: active
open_questions: none
---

# refactor: Move the WhatsApp transport onto the wa-agent package          🚧 ACTIVE — started 2026-09-19

## Problem

[#57](https://github.com/mhmzdev/hisab-whatsapp/issues/57): `hisab/wa.py` (239 lines) is a second copy of the transport that was extracted into [`whatsapp-agent-cli`](https://github.com/mhmzdev/whatsapp-agent-cli) and published as `wa-agent`. The package has since fixed things this copy lacks. A media download now writes through a `.part` file, so a failure leaves nothing behind. A multi-part send yields each part as it leaves. Every failure is a registered code. Two copies of one transport drift apart, and `wa-agent` can only reach 1.0 once Hisab runs on it unchanged.

The owner chose **Option 1**: move the transport now and keep `hisab/transcribe.py` exactly as it is, for both OpenRouter and Gemini. GitHub still shows #57 as blocked by whatsapp-agent-cli#33 (OpenRouter transcription). That edge only applies to Option 2 and does not block this plan.

## Approach

`hisab/wa.py` shrinks to a **thin adapter** over `wa_agent.WhatsApp` 0.1.0. It keeps the method surface `loop.py` already calls: `poll`, `typing`, `download`, `send`, `send_document`, plus `MAX_DOCUMENT_BYTES`, `AUTH_EXIT_CODE` and `AuthError`. Most of `loop.py` and every smoke fake (`ExportFakeWA`, `FakeWA`, `ExitingWA`) therefore stay as they are. The adapter owns four Hisab-specific jobs and nothing else:

1. **Config → client.** It maps `whatsapp.rate_limits` onto wa-agent's per-method keys: `messages_per_min`→`messages`, `statuses_per_min`→`statuses`, `updates_per_min`→`updates`, and `media_per_min`→both `media_post` and `media_get`. It also passes `poll_timeout` to `poll()` and `chunk_chars` to the client. `session`, `now` and `sleep` pass through so smoke can drive a fake session. Smoke no longer monkeypatches `requests.request`.
2. **Failures → Hisab codes, at the boundary.** Every `wa_agent.WhatsAppError` raised at a site that ends in a chat reply is re-raised as `HisabError(<hisab code>, f"wa-agent {e.code}: {e.detail}")`. A WhatsAppError's `str()` is only its generic message, so the detail has to be carried explicitly or the log loses it. `loop.py` then keeps its existing `errors.classify(e, default=…)` → `errors.log` → `errors.reply` path, as `.agents/rules/errors.md` requires. **No new Hisab codes are needed.** Every wa-agent code lands on an existing one (table below), so there are no new `i18n.py` strings and no new portal strings.
3. **Hisab-only formatting.** wa-agent 0.1.0's `to_whatsapp` does not flatten Obsidian wikilinks (`[[page|label]]` → `label`, `[[page#h]]` → `page`). Hisab's vault is Obsidian and the old copy did flatten them. The adapter strips wikilinks with the same two regexes (`hisab/wa.py:214-215` today) **before** calling `send`/`parts_for`. That keeps the current smoke assertion (`tests/smoke.py:127`) true.
4. **The one place that reads the platform's message dict.** `inbound(m)` returns a namedtuple `Inbound(id, frm, type, text, media_id, caption, quoted)`. `loop.py` reads fields and never keys. When wa-agent#31 replaces the 0.1.0 dicts with typed models, only `inbound()` changes.

### Failure mapping (every code in `wa_agent.CODES` 0.1.0)

| wa-agent code | `poll` (loop) | `download` → | `send_document` → | `send` / `typing` |
|---|---|---|---|---|
| `auth` | re-raised as `wa_agent.AuthError`; the loop exits `AUTH_EXIT_CODE` (Hisab's `auth`, 3, **not** wa-agent's 4) | `media_fetch_failed` | `export_failed` | raises; see below |
| `another_poller` | logged with the same stderr line as today (`another poller … HTTP 409, error.code …`), returns `[], offset` | `media_fetch_failed` | `export_failed` | ″ |
| `platform_unavailable` | propagates; the loop logs `poll failed: <code>: <detail>`, sleeps 5s and retries (today's path) | `media_fetch_failed` | `export_failed` (a retry can work) | ″ |
| `platform_rejected` | propagates, same as above | `media_fetch_failed` | `export_rejected`, a superset of today's 400/131053 check: every 4xx is permanent | ″ |
| `media_url_expired` | — | `media_fetch_failed` ("send it again" is the right advice) | — | — |
| `media_too_large` | — | — | `export_rejected`. It can't actually happen, because the loop's own 16 MB check (`loop.py:137`) runs first. It must not be `export_too_large`, which needs `{mb}` at reply time | — |
| `bad_usage`, `no_recipient`, `no_token`, `internal`, `not_implemented` | propagate → retry path | `media_fetch_failed` | `export_failed` | ″ |
| `no_transcription_key`, `transcription_*` | not raised by this path. Hisab does not call wa-agent transcription | | | |

`send`: `_handle_wa` has no reply channel when the reply itself fails. Today a failed send raises `RuntimeError` into the poll loop's `traceback.print_exc()` (`loop.py:194-195`), and that does not change. The adapter re-raises the send failure as `HisabError("internal", "wa-agent <code>: <detail>")` so the log line carries the detail. It never reaches a chat, because no chat is reachable. `typing` never raises in wa-agent 0.1.0.

### Behaviour changes, stated rather than hidden

- **`whatsapp.rate_limits.window_seconds` is no longer honoured (finding for the lead).** `wa_agent.WhatsApp(limits=…)` takes per-method counts. Its `RateLimiter` window is the module constant `WINDOW_SECONDS = 60`, and the constructor has no `window=` argument. The four `*_per_min` keys still work. The adapter prints one stderr line when a config sets `window_seconds` to anything other than 60 (`rate_limits.window_seconds is fixed at 60 by wa-agent 0.1.0; ignoring <n>`). The platform manual's window is 60s and every shipped config uses 60, so no deployed behaviour changes. The key stays in `config.py` defaults and `config.example.yaml` with its comment amended, so an old config still loads. No workaround swaps wa-agent's internal limiter. Follow-up: a `window=` constructor argument in wa-agent. The lead routes that to lane.cli.
- **The 1s sleep between parts is gone** (`hisab/wa.py:162-163` today). wa-agent paces parts with the rate limiter. This is intended upstream.
- **A download failure now replies `media_fetch_failed`.** Before, an HTTP error on the download escaped `_handle_wa` as a traceback and the user heard nothing. Only the "no url" case replied.
- **A poll that is still 429 after the retry** raises `platform_unavailable`, so the loop sleeps 5s. Before, it returned `[]` and re-polled at once. Either way the limiter's penalty keeps the loop off the platform.
- **The export caption** now goes through `to_whatsapp` inside wa-agent's `send_media`. The caption is `Ledger backup · <date, time>` with no markdown, so it renders the same.
- **`upload` also checks the file locally.** It must be a file with a known mime (Hisab always passes `application/octet-stream`) under `cap_for(mime)` = 16 MB.

### Invariants kept

Six tools, the strict check and entry numbers are not touched. **Offset after batch:** `run_whatsapp`'s loop (`loop.py:176-199`) is unchanged except that it reads the id through `inbound()`, and an empty `next_offset` keeps the old one in both implementations. **Dedup by message id:** unchanged. **Chunk under 3,500:** `chunk_chars` passes through, and wa-agent's `DEFAULT_CHUNK` is 3500 as well. **en/ur fixed strings:** no new strings. **Privacy:** nothing personal. The smoke fakes use the existing fake numbers.

## Success criteria

- [ ] `requirements.txt` pins `wa-agent==0.1.0`, and a clean venv installs the file without conflict — `verify: python3 -m venv "$TMPDIR/gh57v" && "$TMPDIR/gh57v/bin/pip" install -q -r requirements.txt && "$TMPDIR/gh57v/bin/python" -c "import wa_agent; assert wa_agent.__version__ == '0.1.0'"`
- [ ] `hisab/wa.py` is a thin adapter: no `requests` import, no HTTP, no limiter or chunker of its own — `verify: ! grep -nE "import requests|requests\.|class RateLimiter|def _chunks|api.whatsapp.com" hisab/wa.py`
- [ ] Every code in `wa_agent.CODES` maps, at every adapter site that can raise it, to a chat code registered in `hisab/errors.py`, and the rendered en/ur reply contains none of smoke's `FORBIDDEN` markers or the wa-agent code name — `verify: python3 tests/smoke.py` (new block: "wa-agent: every code maps to a Hisab chat code, no leak")
- [ ] The config's per-method limits pace the client (30 instant polls at `updates_per_min: 15` span ≥ 60s on a fake clock), a 429 backs off ≥ 55s and succeeds, a 409 logs `another poller` and keeps the offset, 401/190 and 400/100 raise `AuthError`, and 500/503 do not — `verify: python3 tests/smoke.py`
- [ ] A `window_seconds` other than 60 prints the "fixed at 60" line and does not crash — `verify: python3 tests/smoke.py`
- [ ] The export still uploads as `application/octet-stream`, sends as a `document` with the zip filename, maps 400/131053 → `export_rejected` and 500 → `export_failed`, and keeps the wa-agent detail in `HisabError.detail` (#36) — `verify: python3 tests/smoke.py`
- [ ] Replies still flatten wikilinks and split under `chunk_chars` — `verify: python3 tests/smoke.py`
- [ ] A download failure replies `media_fetch_failed` with the detail on stderr — `verify: python3 tests/smoke.py`
- [ ] Transcription is byte-for-byte unchanged — `verify: git diff --exit-code main -- hisab/transcribe.py`
- [ ] The image builds with the pinned dependency (a build, not a run: nothing polls) — `verify: docker build -q -t hisab-whatsapp-gh57 .`
- [ ] Terminal mode still works end to end on a copy of the sample (it never touches the transport, so this proves the import graph) — `verify: manual` 1. `cp -r sample-vault "$TMPDIR/gh57-vault"` 2. `HISAB_VAULT` is not used by `--stdin`, so run `python3 -m hisab.loop --stdin --config <scratch config pointing ledger.path at the copy>` 3. type `chai 150 cash` → expect a one-line "posted #N" shape 4. type `quit`. Needs a model key in `.env`. If there is none, skip this and say so at /review.
- [ ] **Post-merge, owner + lead only, left unticked by the lane:** `docker compose up -d --build` on the demo agent, then a text, a voice note (OpenRouter config), `export-ledger` (a ZIP arrives as a document), and a reply-to-undo all round-trip. Lanes never poll the demo agent. — `verify: manual (post-merge)`
- [ ] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — The adapter, the pin and its transport tests
**Status:** Done — `hisab/wa.py` is a 122-line adapter (no HTTP of its own); `wa-agent==0.1.0` pinned; smoke drives a `FakeSession`, adds the window line, the all-codes × all-sites × en/ur × hosted leak check (14 codes), and the expired-url/no-`.part` check. `AuthError` at download/send_document mapping comment added per the lead.
- Prerequisite: install the pin into the environment that runs smoke (`python3 -m pip install -r requirements.txt`).
- Files: `requirements.txt`, `hisab/wa.py` (rewrite of all 239 lines), `tests/smoke.py:11-13, 127-198, 290-318, 815-832`.
- Change:
  - `requirements.txt`: add `wa-agent==0.1.0`. Keep `requests>=2.32`, because `agent.py:88` and `transcribe.py:30` still use it.
  - `hisab/wa.py`, top to bottom:
    - the docstring
    - `from wa_agent import AuthError, WhatsAppError, WhatsApp as _Client` and `from . import errors`
    - `MAX_DOCUMENT_BYTES = 16 * 1024 * 1024` (kept: `loop.py:137` and smoke `:271` read it) and `DOCUMENT_MIME = "application/octet-stream"`, keeping the #36 comment about `application/zip` being refused
    - `AUTH_EXIT_CODE = errors.exit_status("auth")`
    - `EXPORT_CODES = {"platform_rejected": "export_rejected", "media_too_large": "export_rejected"}` (anything else → `export_failed`)
    - `_LIMIT_KEYS` mapping config → wa-agent method names
    - `_unlink(text)` with the two wikilink regexes
    - `Inbound` + `inbound(m)`
    - `class WhatsApp`:
      - `__init__(token, poll_timeout=20, chunk_chars=3500, rate_limits=None, session=None, now=time.time, sleep=time.sleep)` builds `_Client(token, session=session, limits=…, chunk_chars=…, now=…, sleep=…)` and prints the window line when `rate_limits.get("window_seconds", 60) != 60`
      - `poll(offset)` catches `WhatsAppError` with `code == "another_poller"` → prints today's line (with `error.code` read from the detail) → `return [], offset`, and lets `AuthError` and every other code propagate
      - `typing(mid)`
      - `download(media_id, dest)` → `HisabError("media_fetch_failed", …)` on any `WhatsAppError`
      - `send(to, text)` → `[s.id for s in client.send(to, _unlink(text))]`; a WhatsAppError → `HisabError("internal", …)`
      - `send_document(to, path, filename, caption=None)` → `client.upload(path, DOCUMENT_MIME)` then `client.send_media(to, media_id, caption, filename, DOCUMENT_MIME).id`, mapped through `EXPORT_CODES`
      - `parts_for(text)` → `client.parts_for(_unlink(text))`, for smoke
  - `tests/smoke.py`:
    - replace `FakeResponse`-over-`requests.request` monkeypatching with a `FakeSession` that has a `request(verb, url, headers=None, **kw)` handler and `transport_errors = (ConnectionError,)`
    - keep every existing assertion's intent: pacing, 429 backoff, 409 log, octet-stream upload, 131053 → `export_rejected`, 500 → `export_failed` (it is a `HisabError` now, not a `RuntimeError`), auth 401/190 and 400/100 vs 500/503 not auth
    - `:127-128` become `parts_for` assertions (wikilink + bold + heading + bullet; 8000 chars → 3 parts, each `≤ 3500 + len("\n\n(i/3)")`)
- Tests to add:
  - (a) a window-60 config prints nothing, a window-30 config prints the "fixed at 60" line
  - (b) for every `code in wa_agent.CODES`, a `FakeClient` raising `WhatsAppError(code, 'HTTP 500 {"error":{"message":"x"}}')` at `download` and `send_document` yields a `HisabError` whose code is a chat code in `hisab.errors.CODES`. `errors.reply(code, lang, hosted)` for en/ur × hosted/self-host contains no `FORBIDDEN` marker and not the wa-agent code name, and `.detail` contains the wa-agent code
  - (c) a 404 on the media URL → `HisabError("media_fetch_failed")` with `media_url_expired` in the detail, and no `.part` file left in `dest`
- Verify: `python3 tests/smoke.py`

### Phase 2 — Loop wiring through `inbound()` and the download failure path
**Status:** Not started
- Files: `hisab/loop.py:19, 166-199, 201-233`, `tests/smoke.py:626-633`.
- Change:
  - `run_whatsapp` `:190` reads the id as `inbound(m).id`.
  - The generic poll `except` at `:184-185` prints `poll failed: {getattr(e, 'code', type(e).__name__)}: {getattr(e, 'detail', '') or e}; retrying in 5s`, so a WhatsAppError's detail reaches the log.
  - `_handle_wa` `:202-231` starts with `msg = inbound(m)` and uses `msg.frm/.type/.id/.quoted/.text/.media_id/.caption`.
  - `download` for audio and image is wrapped in a `try/except Exception as e: self._fail(wa, frm, errors.classify(e, default="media_fetch_failed"), e, mid); return`, and the dead `if not path` branches go.
  - `run_whatsapp` keeps constructing `WhatsApp(tok, poll_timeout, chunk_chars, rate_limits)`, the same signature.
- Test: `MissingMediaWA.download` (`smoke.py:627-628`) raises `HisabError("media_fetch_failed", "wa-agent media_url_expired: HTTP 404")` instead of returning `(None, None)`. It asserts the reply equals `errors.reply("media_fetch_failed", "en")` and that stderr carries `media_url_expired`. The existing voice, export, pending, welcome and auth-exit blocks (`:596-624`, `:775-850`) pass unchanged.
- Verify: `python3 tests/smoke.py` and `git diff --exit-code main -- hisab/transcribe.py`

### Phase 3 — Docs, config comment, image build
**Status:** Not started
- Files: `AGENTS.md:29-31` (repo-map `wa.py` lines), `ARCHITECTURE.md:49, 63`, `runner/README.md:33`, `config.example.yaml:31-32`, `hisab/config.py:24-26` (comment only).
- Change:
  - `wa.py` is described as the adapter over `wa-agent==0.1.0`: config → client, wa-agent codes → Hisab codes, wikilink flattening, `inbound()`. The rate limiter, chunking, media and 429/409 handling are now credited to wa-agent.
  - `window_seconds` is commented as fixed at 60 by wa-agent 0.1.0.
  - No README change: #58 already says Hisab is migrating onto wa-agent. Change "migrates onto it in #57" in `AGENTS.md` "Origin" to "runs on it since #57".
- Verify: `docker build -q -t hisab-whatsapp-gh57 .` and `python3 tests/smoke.py`

## Risks

- **wa-agent#31 (typed message models) before 1.0.** The dict shape can change. Mitigation: `inbound()` is the only reader, and the pin is exact, so nothing changes until someone bumps it on purpose.
- **Exact pin `==0.1.0`.** No upstream fixes arrive automatically. That is intended: bumping the pin is a deliberate PR that re-runs smoke.
- **Only public names are used** (`WhatsApp`, `WhatsAppError`, `AuthError`, `CODES`; client methods `poll`, `typing`, `download`, `upload`, `send_media`, `send`, `parts_for`, all in wa-agent's `__all__` or on its client). Nothing is imported from `wa_agent.text`, `.media` or `.ratelimit`, so a refactor of those modules can't break Hisab.
- **The runner exit status.** Hisab keeps exit 3 for `auth` (Firestore `lastError` depends on it). wa-agent's own `auth` exit status 4 is never used as the process status.
- **Docker daemon unavailable locally** → the build criterion is reported as not run at /review, not ticked.

## Out of scope

- Transcription: `hisab/transcribe.py` stays, and removing it after whatsapp-agent-cli#33 is a separate follow-up.
- `hisab/store.py` and wa-agent's `Store`/`state_dir`/`resolve_token`: Hisab keeps its own store and token from `.env`.
- Recording partial deliveries from `send_iter` (storing the ids of parts that arrived before a failure). The adapter uses the eager `send`, which matches today's all-or-nothing store write.
- Surfacing `another_poller` on the portal as a `lastError`.
- landing/, ledger/agent/tools logic.
- Any live run against the demo agent (post-merge, owner and lead).
