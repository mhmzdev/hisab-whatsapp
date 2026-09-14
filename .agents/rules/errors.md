---
description: How a failure becomes something a user or the portal sees — error codes in hisab/errors.py, never exception text.
paths:
  - "hisab/**"
  - "runner/**"
  - "landing/**"
  - "tests/**"
---

# Errors are codes

Every failure a user reads in WhatsApp, and every `lastError` the portal renders, is a **code** registered in [`hisab/errors.py`](../../hisab/errors.py). The detail goes to the operator's log; the user gets a fixed sentence in their language that says what happened and what to do next.

## Never

- Format an exception, an HTTP body, hledger stderr or a provider name into user-facing text (`f"… {e}"`, `s(key, err=str(e))`). An expired key once reached a phone as `HTTP 401 {"error":…`. That was #27.
- Call `s("err_…")` directly. Failure text renders only through `errors.reply(code, lang, hosted, **kw)`.
- Write a sentence into Firestore. `lastError` is a portal code; the portal renders it in English and Urdu.

## Always

- **At the source**, when you know what failed, raise `HisabError("<code>", detail)`. `detail` is for the log and can be as raw as you like.
- **At the reply site**, catch broadly, then classify, log and reply:
  ```python
  except Exception as e:
      code = errors.classify(e, default="<this site's code>")
      errors.log(code, e, msg_id)
      wa.send(frm, errors.reply(code, lang, self.cfg.get("hosted")))
  ```
  The `default` means an exception type nobody foresaw still gets a sensible code and never leaks.
- **Unclassified is `internal`**. It logs a traceback and tells the user nothing was posted.

## Adding a failure

1. Add a row to `CODES` in `hisab/errors.py`: `Error("chat", None)` for a WhatsApp reply, or `Error("portal", <exit status>)` for a worker exit the runner should surface.
2. **chat:** add `err_<code>` to `hisab/i18n.py` in `en` and `ur`, with the same `{placeholders}` in both. Add `err_<code>_selfhost` only when a self-hoster's next step differs (their own `.env`, their own `config.yaml`). The hosted text says the operator has been told.
3. **portal:** add `portal_error_<code>` to `landing/content/strings.json` in `en` and `ur`. The runner's `on_worker_exit` picks the code up from the exit status with no runner change. Exit statuses must be unique.
4. Run `python3 tests/smoke.py`. It fails and names the problem when a code has no strings, an `err_*` string has no code, en and ur placeholders differ, an `{err}` placeholder is back, or a rendering contains `HTTP`, `{"error"`, `Traceback` or a provider name. `tests/check_landing.py`, which smoke runs, fails when a portal code has no portal string.

Keep existing code names stable. `auth` is already stored in Firestore documents.
