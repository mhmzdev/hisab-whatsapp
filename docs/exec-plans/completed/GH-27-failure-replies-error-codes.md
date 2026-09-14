---
slug: GH-27-failure-replies-error-codes
issue: 27
status: completed
open_questions: none
---

# fix: Failure replies tell the user what happened and what to do next, never the raw error — one error-code registry          ✅ COMPLETED — 2026-09-14

## Problem

[#27](https://github.com/mhmzdev/hisab-whatsapp/issues/27): four reply sites interpolate `{err}` straight from an exception, so an expired OpenRouter key reached the phone as `HTTP 401 {"error":{"message":"API key expired."…`. A shop owner cannot act on that, and in hosted mode it exposes the operator's provider and key state to a stranger.

- `hisab/loop.py:110` → `not_posted` (`hisab/i18n.py:34`) — hledger stderr, which `_short_err` (`hisab/ledger.py:297`) cuts to the last three lines: for an undeclared commodity that is `Consider adding a commodity directive. Examples: commodity XYZ1000.00…`, the useless half.
- `hisab/loop.py:112` → `failed` (`i18n.py:35`) — any model/network exception, 200 chars.
- `hisab/loop.py:204` → `voice_fail` (`i18n.py:27`) — transcription exception, 120 chars.
- `hisab/loop.py:223` → `export_fail` (`i18n.py:43`) — document send exception, 120 chars.

Owner addendum (this session): not a patch on four sites but **one central error-code registry** that every failure reply and every runner `lastError` goes through, so a future failure folds in as one new code and the tests force its strings. Plus the convention as a harness rule in `.agents/rules/` (with `.claude/rules` symlinked to it) and `AGENTS.md` updated. GH-22 removed `roman`, so the issue's "en, ur and roman" is now **en and ur**.

## Approach

**`hisab/errors.py` — the registry, stdlib-only** (the runner and `tests/check_landing.py` import it; neither may pull `requests`).

```python
class HisabError(Exception):
    """A failure with a registry code. `detail` is for the log only — it never reaches a reply."""
    def __init__(self, code, detail=""):
        if code not in CODES: raise KeyError(f"unregistered error code {code!r}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail

Error = namedtuple("Error", "surface exit_status")   # surface: "chat" (a WhatsApp reply) or "portal" (a lastError)

CODES = {
    # chat — rendered from i18n S["err_<code>"]; S["err_<code>_selfhost"] overrides it when cfg["hosted"] is false
    "model_auth":           Error("chat", None),  # model endpoint rejected the key (401/403)
    "model_unavailable":    Error("chat", None),  # connection/timeout/408/409/425/429/5xx after retries
    "model_rejected":       Error("chat", None),  # any other non-2xx (bad model id, bad request)
    "transcription_failed": Error("chat", None),
    "media_fetch_failed":   Error("chat", None),  # was fetch_fail
    "ledger_rejected":      Error("chat", None),  # takes {reason}: the cleaned hledger sentence
    "too_many_steps":       Error("chat", None),  # was too_many
    "export_failed":        Error("chat", None),
    "export_too_large":     Error("chat", None),  # takes {mb}
    "internal":             Error("chat", None),  # anything unclassified — the fallback, never a leak
    # portal — stored in tenants/{uid}.lastError, rendered from landing strings.json "portal_error_<code>"
    "auth":                 Error("portal", 3),   # worker exit status: WhatsApp rejected the token (kept "auth": stored in Firestore)
}

def classify(exc, default="internal"):   # HisabError -> its code; LedgerError (by class name, no import cycle) -> ledger_rejected; else default
def reply(code, lang, hosted, **kw):      # the one way a failure becomes user text
def log(code, exc, msg_id=None):          # stderr: "error <code> msg=<id>: <Type>: <full detail>"; traceback for "internal"
def exit_status(code) / code_for_exit(status)
PORTAL_CODES = tuple(c for c, e in CODES.items() if e.surface == "portal")
```

`classify` recognises `LedgerError` by `type(exc).__name__ == "LedgerError"` so `errors.py` imports nothing from `hisab` except `i18n` (lazily inside `reply`, keeping the runner/landing import light).

**Sources raise codes, sites supply a default.** `Agent._chat` (`hisab/agent.py:88`) raises `HisabError("model_auth"|"model_unavailable"|"model_rejected", detail=last)` instead of `RuntimeError`; `Agent.run`'s `too_many` (`agent.py:72`) returns `errors.reply("too_many_steps", …)`. Transcription and the document send keep raising whatever they raise — the site's default (`transcription_failed`, `export_failed`) is the classification, so a new google-genai exception type can never leak. Each site becomes:

```python
except Exception as e:
    code = errors.classify(e, default="transcription_failed")
    errors.log(code, e, mid)
    wa.send(frm, errors.reply(code, lang, self.cfg.get("hosted")))
```

**The ledger reason.** `_short_err` (`ledger.py:297`) is replaced by `_clean_err(stderr)`: drop the `hledger: Error: <path>:<line>:` banner (the path leaks the operator's filesystem), take the excerpt line hledger points at (the line above a `^^^` marker, else the numbered `NNN |` line) stripped of the gutter, plus the explanation paragraph with `Strict … checking is enabled, and` and everything from `Consider adding` onward removed. `rejected, nothing written: ` stays as the prefix the model already reads (tools.call, `hisab/tools.py:58`). Shapes, verified against hledger this session:
- undeclared account → `account "expenses:nope" has not been declared. (expenses:nope      PKR 300.00)`
- unbalanced → `This transaction is unbalanced. The real postings' sum should be 0 but is: PKR 100.00`
- undeclared commodity → `commodity "XYZ" has not been declared. (expenses:food      XYZ 300.00)`
Capped at 200 chars. The loop's `LedgerError` branch replies `err_ledger_rejected` with `{reason}` = the message minus the prefix, plus "reply with the corrected entry". This path is the non-tool one (e.g. `Agent.system()` → `account_names()`); inside a tool call the model gets the same cleaner text.

**Hosted vs self-host next step.** `reply` picks `err_<code>_selfhost` when `hosted` is falsy and that key exists, else `err_<code>`. Only `model_auth` and `model_rejected` carry a self-host override ("check the model key in .env" / "check model settings in config.yaml"); hosted says "if it keeps happening, the operator has been told" — true because `errors.log` writes stderr, which the runner forwards.

**Runner fold-in.** `runner/errors.py` is deleted; `runner/reconcile.py:15,105-109` becomes `code = errors.code_for_exit(returncode)`; `if not code: return None`; `lastError: code`. `hisab/wa.py:25` becomes `AUTH_EXIT_CODE = errors.exit_status("auth")`. `tests/check_landing.py:86-94` iterates `hisab.errors.PORTAL_CODES`. A new portal code with an exit status is then surfaced by the runner with no runner edit, and the landing check fails until its `portal_error_<code>` exists.

**Guards that make it dynamic (smoke).** For every code in `CODES`: chat codes have `err_<code>` (and any `_selfhost`) with non-empty `en` and `ur`, the same `{placeholders}` in both; portal codes have an exit status that is unique; every `err_*` key in `i18n.S` belongs to a registered code (no orphans). No `{err}` placeholder remains in `i18n.S`. No file under `hisab/` other than `errors.py` calls `s("err_…")`. Every chat rendering, in both languages and both modes, contains none of `HTTP`, `{"error"`, `Traceback`, `OpenRouter`, `Gemini`, `OpenAI`, `Google`.

**Convention.** `.agents/rules/errors.md` (frontmatter `paths:` over `hisab/**`, `runner/**`, `landing/**`, `tests/**` so Claude Code loads it when those files are touched): never interpolate an exception into user text; add a code to `CODES`, the strings, and let smoke tell you what is missing; log detail with `errors.log`. `.claude/rules -> ../.agents/rules` symlink, same as skills. `AGENTS.md` gains a Rules line in "Read in this order", the `errors.py` line in the repo map, a non-negotiable, and the hosted-mode bullet points at `hisab/errors.py`.

Invariants kept: six tools (no tool change), strict check and rollback untouched (only the message text changes), entry numbering and offset untouched, every new string `en` + `ur`, privacy improved (no path, provider or key state in replies).

## Success criteria

- [x] No reply sent to WhatsApp contains `HTTP`, `{"error"`, a traceback line or a provider name when the model (401, 503, connection error), transcription or export fails; each says what happened and what to do next; stderr carries the code, the message id and the raw detail — `verify: python3 tests/smoke.py`
- [x] A rejected ledger block names the wrong line or the reason in one short sentence, without the hledger banner or file path, and invites a corrected entry (real hledger output for undeclared account, unbalanced, undeclared commodity) — `verify: python3 tests/smoke.py`
- [x] Every registered code has its strings in `en` and `ur` (chat) or `portal_error_<code>` (portal); no orphan `err_*` key; no `{err}` placeholder; hosted and self-host renderings differ for `model_auth` — `verify: python3 tests/smoke.py`
- [x] The runner maps a worker exit status to a `lastError` code through the registry (`auth` still written for status 3, nothing for status 1) — `verify: python3 tests/smoke.py`
- [x] `tests/check_landing.py` reads portal codes from `hisab/errors.py`; `runner/errors.py` is gone and nothing references it — `verify: python3 tests/check_landing.py && ! grep -rn "runner/errors\|runner.errors\|from .errors" hisab runner tests landing/app landing/README.md AGENTS.md ARCHITECTURE.md runner/README.md`
- [x] `.claude/rules` is a symlink to `.agents/rules` and `.agents/rules/errors.md` exists — `verify: test "$(readlink .claude/rules)" = "../.agents/rules" && test -f .claude/rules/errors.md`
- [ ] Phone: with a wrong model key in `.env`, `500 car fuel` gets the friendly self-host reply and `docker compose logs` shows `error model_auth msg=wamid…` with the 401 — `verify: manual 1. put a bogus OPENROUTER_API_KEY/GEMINI key in .env against ./vault 2. docker compose up -d --build 3. send "500 car fuel" to the demo agent 4. expect one line saying the AI service rejected the key and to check the model key in .env 5. docker compose logs shows the 401 detail 6. restore the key`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — The registry and the chat reply sites
**Status:** Done — `hisab/errors.py` registry; `err_*` strings replace the four `{err}` strings plus `fetch_fail`/`too_many`/`export_too_large`; `_chat` raises coded `HisabError`; `_clean_err` replaces `_short_err`; loop sites classify → log → reply; smoke `errors:` block
- Files: new `hisab/errors.py`; `hisab/i18n.py:27-45`; `hisab/loop.py:17,62-66,87-112,115-126,195-226`; `hisab/agent.py:4-8,72,88-107`; `hisab/ledger.py:112,297-299`; `tests/smoke.py` (after the export/quota block ~line 285)
- Change:
  - Write `hisab/errors.py` as in Approach.
  - `i18n.py`: remove `voice_fail`, `fetch_fail`, `not_posted`, `failed`, `too_many`, `export_too_large`, `export_fail`; add `err_<code>` for every chat code and `err_model_auth_selfhost`, `err_model_rejected_selfhost`. Texts (en; ur is the faithful Urdu-script equivalent, Latin kept for `.env`, `config.yaml`, `export-ledger`):
    - `model_auth`: "The AI service isn't accepting requests right now. Your message is saved; try again in a few minutes — if it keeps happening, the operator has been told." · selfhost: "The AI service rejected the model key. Check the model key in .env, then send your message again."
    - `model_unavailable`: "The AI service isn't reachable right now. Your message is saved; try again in a few minutes."
    - `model_rejected`: hosted as `model_auth` · selfhost: "The AI service refused the request. Check the model settings in config.yaml, then send your message again."
    - `transcription_failed`: "Couldn't understand that voice note. Send it as text, or try the voice note again."
    - `media_fetch_failed`: "Couldn't download that file. Send it again in a moment."
    - `ledger_rejected`: "Not posted — {reason}. Reply with the corrected entry."
    - `too_many_steps`: keep today's text.
    - `export_failed`: "Couldn't send the ledger export. Send *export-ledger* again in a bit."
    - `export_too_large`: keep today's text (`{mb}`).
    - `internal`: "Something went wrong on my side and nothing was posted. Try again in a moment."
  - `agent.py._chat`: 401/403 → `HisabError("model_auth", last)`; the retryable set exhausted or a `ConnectionError`/`Timeout` → `model_unavailable`; any other non-2xx (break today) → `model_rejected`. `run` returns `errors.reply("too_many_steps", lang, self.cfg.get("hosted"))`.
  - `ledger.py`: `_short_err` → `_clean_err` as in Approach.
  - `loop.py`: `handle`/`_agent` carry `msg_id` (the parked call at `loop.py:62-66` passes it too); the `_agent` `except` pair becomes one `except Exception` through `classify(e)` (LedgerError → `ledger_rejected` with `reason=str(e).removeprefix("rejected, nothing written: ")[:200]`), `log`, `reply`. Voice site default `transcription_failed`; both `fetch_fail` sites `media_fetch_failed` (logged with no exception detail); export send default `export_failed`; `export_too_large` via `errors.reply`. `run_stdin` unchanged beyond passing `mid`.
  - `reply(code, lang, hosted, **kw)` raises `KeyError` for a portal code — portal codes never render in chat.
- Test (smoke, new block "errors:"):
  - registry completeness, placeholders, orphans, no `{err}`, no `s("err_` outside `errors.py` (read `hisab/*.py` source) — as in Approach.
  - fake agents raising `HisabError("model_auth", 'HTTP 401 {"error":{"message":"API key expired."}}')`, `HisabError("model_unavailable", "ConnectionError")`, a bare `KeyError("boom")` → through `_handle_wa` with `ExportFakeWA`, under `redirect_stderr`: reply has no forbidden token, equals `errors.reply(<code>, "en", False)`; stderr has the code, the message id and `API key expired`. Repeat `model_auth` with `hosted=True` → the hosted text.
  - `_chat` status mapping with a monkeypatched `requests.post` (401 → `model_auth`, 400 → `model_rejected`, 503 ×4 → `model_unavailable`) and `time.sleep` stubbed.
  - voice: `loop_mod.transcribe` patched to raise `RuntimeError('transcription failed: HTTP 500 {"error"…')`, `wa.download` returns a temp path → `err_transcription_failed` text, detail in stderr.
  - export: `ExportFakeWA.send_document` raising `RuntimeError("send failed: HTTP 500 …")` → `err_export_failed` text.
  - ledger: `Ledger.append` on a scratch copy of `sample-vault` with an undeclared account, an unbalanced pair and commodity `XYZ` → each `LedgerError` message has no `hledger: Error`, no `/`-path, no `Consider adding`, and contains `expenses:nope` / `unbalanced` / `XYZ` respectively; a fake agent raising one of them → reply starts `Not posted — ` and ends `Reply with the corrected entry.`
  - the existing `"MB" in` export-cap assertion (`smoke.py:233`) still passes.

### Phase 2 — Runner and landing fold-in
**Status:** Done — `runner/errors.py` deleted; `AUTH_EXIT_CODE` and `on_worker_exit` read the registry; `check_landing.py` iterates `PORTAL_CODES`; runner/landing READMEs point at `hisab/errors.py`
- Files: `hisab/wa.py:25`; `runner/reconcile.py:1-18,101-112`; delete `runner/errors.py`; `tests/check_landing.py:1,86-94`; `tests/smoke.py:396,428,571-592`; `landing/app/portal/page.jsx:28` (comment only); `landing/README.md:33`; `runner/README.md:19,87`
- Change: `AUTH_EXIT_CODE = errors.exit_status("auth")`; `on_worker_exit` uses `errors.code_for_exit(returncode)`; `check_landing.py` imports `from hisab.errors import PORTAL_CODES`; smoke's `LAST_ERROR_CODES == {"auth"}` assertion becomes `PORTAL_CODES == ("auth",)` plus `code_for_exit(3) == "auth"`, `code_for_exit(1) is None`; docs name `hisab/errors.py`.
- Test: existing `runner: admission + lastError ok` block passes unchanged in behaviour; `python3 tests/check_landing.py` passes.

### Phase 3 — Convention, harness rule, docs
**Status:** Done — `.agents/rules/errors.md` + `.claude/rules` symlink; AGENTS.md (read order, repo map, non-negotiable, hosted bullet, lifecycle paragraph), skills README, ARCHITECTURE failure table
- Files: new `.agents/rules/errors.md`; new symlink `.claude/rules -> ../.agents/rules`; `AGENTS.md` (Read in this order, Repo map, Non-negotiables, hosted-mode bullet line 54, How we work paragraph mentioning rules); `ARCHITECTURE.md:93-95`; `.agents/skills/README.md` first paragraph (rules live beside skills, same symlink pattern)
- Change: the rule file states: every failure a user or the portal sees is a code in `hisab/errors.py`; never format an exception into user text; raise `HisabError(code, detail)` at the source when the class is known, pass a site `default=` otherwise; log with `errors.log`; a new chat code needs `err_<code>` in `en` and `ur` (and `_selfhost` only when the next step differs); a new portal code needs an exit status (if a worker exit surfaces it) and `portal_error_<code>` in `landing/content/strings.json`; smoke and `check_landing.py` name what is missing. `ARCHITECTURE.md` failure rows say "a code from `hisab/errors.py`, rendered in the user's language; detail to the log".
- Test: the symlink criterion command; `python3 tests/smoke.py`.

### Phase 4 — Phone
**Status:** Handed to the owner — manual criterion below
- The manual criterion above, against `./vault` and the demo agent.

## Risks

- `_clean_err` depends on hledger's error layout; a future hledger could change it. Mitigation: it falls back to the last non-banner, non-`Consider` line, and smoke runs real hledger so a layout change fails loudly.
- Replacing `RuntimeError` in `_chat` with `HisabError`: `tests/check_endpoint.py` may match on the message. Implement checks its `except` and keeps `str(e)` informative (`HisabError.__str__` includes the detail).
- Firestore already holds `lastError: "auth"` in emulator/dev data — the code name is kept, so nothing migrates.

## Out of scope

- Poll/welcome/reminder failures (`loop.py:163-166,247,269`) — log lines, not replies.
- `unsupported` and `quota_exceeded` — expected-behaviour notices, not failures.
- Portal-side client errors (`portal_error_unknown` set by the page itself) — not written by the runner.
- Alerting the operator beyond stderr.
