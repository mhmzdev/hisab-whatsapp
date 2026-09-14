"""Every failure a user or the portal is told about, by code. The one place a failure becomes words.

A failure is a code, never an exception's text: the detail goes to stderr (the runner forwards a worker's
log to the operator), the user gets a fixed string in their language that says what happened and what to
do next. Surfaces:
  chat    a WhatsApp reply, rendered from hisab/i18n.py S["err_<code>"]; S["err_<code>_selfhost"] overrides
          it when the next step differs for a self-hoster (cfg["hosted"] false)
  portal  a tenants/{uid}.lastError the runner writes, rendered from landing/content/strings.json
          "portal_error_<code>"; exit_status is the worker's exit status that surfaces it

A new failure is one CODES row plus its strings; tests/smoke.py and tests/check_landing.py name what is
missing. Stdlib-only: the runner and tests/check_landing.py import this. See .agents/rules/errors.md.
"""
import sys
import traceback
from collections import namedtuple

Error = namedtuple("Error", "surface exit_status")

CODES = {
    # chat
    "model_auth": Error("chat", None),            # the model endpoint rejected the key (401/403)
    "model_unavailable": Error("chat", None),     # connection, timeout, 408/409/425/429/5xx after retries
    "model_rejected": Error("chat", None),        # any other non-2xx: bad model id, bad request
    "transcription_failed": Error("chat", None),
    "media_fetch_failed": Error("chat", None),
    "ledger_rejected": Error("chat", None),       # {reason}: the cleaned hledger sentence
    "too_many_steps": Error("chat", None),
    "export_failed": Error("chat", None),         # transient: retry can succeed
    "export_rejected": Error("chat", None),       # WhatsApp refused the file (400/131053): a retry never helps
    "export_too_large": Error("chat", None),      # {mb}
    "internal": Error("chat", None),              # anything unclassified — the fallback, never a leak
    # portal
    "auth": Error("portal", 3),                   # WhatsApp rejected the worker's token (401/190, 400/100)
}

PORTAL_CODES = tuple(c for c, e in CODES.items() if e.surface == "portal")


class HisabError(Exception):
    """A failure with a registry code. `detail` is for the log only — it never reaches a reply."""

    def __init__(self, code, detail=""):
        if code not in CODES:
            raise KeyError(f"unregistered error code {code!r}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


def classify(exc, default="internal"):
    """An exception -> a code. A HisabError carries its own; a LedgerError (matched by name, so this module
    imports nothing that shells out) is a rejected block; anything else is the calling site's default."""
    if isinstance(exc, HisabError):
        return exc.code
    if type(exc).__name__ == "LedgerError":
        return "ledger_rejected"
    if default not in CODES:
        raise KeyError(f"unregistered error code {default!r}")
    return default


def reply(code, lang, hosted=False, **kw):
    """The user-facing text for a chat code, in `lang`. Portal codes never render in chat."""
    if CODES[code].surface != "chat":
        raise KeyError(f"{code!r} is a {CODES[code].surface} code, not a chat reply")
    from .i18n import S, s
    key = f"err_{code}"
    if not hosted and f"{key}_selfhost" in S:
        key = f"{key}_selfhost"
    return s(key, lang, **kw)


def log(code, exc=None, msg_id=None):
    """The detail, for the operator: stderr, never WhatsApp. An unclassified failure gets its traceback."""
    detail = f": {type(exc).__name__}: {exc}" if exc is not None else ""
    print(f"error {code} msg={msg_id or '-'}{detail}", file=sys.stderr, flush=True)
    if code == "internal" and exc is not None and exc.__traceback__ is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)


def exit_status(code):
    return CODES[code].exit_status


def code_for_exit(status):
    """A worker's exit status -> the portal code it surfaces, or None for an ordinary exit or crash."""
    for code, e in CODES.items():
        if e.exit_status is not None and e.exit_status == status:
            return code
    return None
