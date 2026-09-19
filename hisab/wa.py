"""WhatsApp transport: a thin adapter over the `wa-agent` package (#57). Long-poll only; an agent may message only its creator.

wa-agent owns the HTTP client, the per-method rate limiter (#17), chunking, markdown → WhatsApp, media and the
document send (#36), and transcription (#61). This file owns only what is Hisab's: config → client, config →
transcription call, wa-agent failure codes → Hisab codes at the boundary (no wa-agent message ever reaches a chat,
.agents/rules/errors.md), Obsidian wikilink flattening, and `inbound()` — the one place that reads the platform's
message dict, so wa-agent#31's typed models are a small diff.
"""
import re
import sys
import time
from collections import namedtuple

from wa_agent import AuthError, WhatsAppError
from wa_agent import WhatsApp as _Client
from wa_agent.transcribe import transcribe as _transcribe

from . import errors

MAX_DOCUMENT_BYTES = 16 * 1024 * 1024  # WhatsApp's platform cap for outbound documents
# The platform accepts only its listed document types plus application/octet-stream "for a generic binary file"
# (manual, POST /agent/v1/media → Accepted media types); application/zip is refused with 400/131053 (#36).
DOCUMENT_MIME = "application/octet-stream"

AUTH_EXIT_CODE = errors.exit_status("auth")  # hisab.loop's exit status on AuthError; the runner maps it back through hisab/errors.py

# config whatsapp.rate_limits → wa-agent's per-method limits. media is per HTTP method on the platform, so one
# budget feeds both upload (POST) and download (GET). The window is wa-agent's fixed 60s — the platform manual's.
_LIMIT_KEYS = {"messages_per_min": ("messages",), "statuses_per_min": ("statuses",), "updates_per_min": ("updates",),
               "media_per_min": ("media_post", "media_get")}

# wa-agent code → Hisab chat code for the export's upload + send. Refused is permanent (a retry never helps);
# anything else, unreachable included, is export_failed, which invites a retry. media_too_large can't happen here —
# the loop checks MAX_DOCUMENT_BYTES first — and must not be export_too_large, whose reply needs {mb}.
EXPORT_CODES = {"platform_rejected": "export_rejected", "media_too_large": "export_rejected"}
# An AuthError raised by download or send_document maps like any other code there (media_fetch_failed,
# export_failed): the user still gets a reply for this message, and the next poll raises AuthError and the
# loop exits AUTH_EXIT_CODE. Deliberate — do not special-case auth at these two sites.

Inbound = namedtuple("Inbound", "id frm type text media_id caption quoted")


def inbound(m):
    """The platform's message dict → the fields Hisab reads. The only reader of the dict (wa-agent#31)."""
    typ = m.get("type")
    body = m.get(typ) if isinstance(m.get(typ), dict) else {}
    return Inbound(
        id=m.get("id"),
        frm=m.get("from"),
        type=typ,
        text=body.get("body") if typ == "text" else None,
        media_id=body.get("id") if typ in ("audio", "image") else None,
        caption=(body.get("caption") or "").strip() if typ == "image" else None,
        quoted=(m.get("context") or {}).get("id"),
    )


def _unlink(text):
    """Obsidian wikilinks → their label: Hisab's vault is Obsidian, the transport knows nothing of it."""
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    return re.sub(r"\[\[([^\]#|]*)(#[^\]|]*)?\]\]", r"\1", text)


def _detail(e):
    """The log detail for a wa-agent failure: its code and raw detail. str(e) is only the generic message."""
    return f"wa-agent {e.code}: {e.detail}"


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


class WhatsApp:
    def __init__(self, token, poll_timeout=20, chunk_chars=3500, rate_limits=None, session=None,
                 now=time.time, sleep=time.sleep):
        rl = rate_limits or {}
        window = rl.get("window_seconds", 60)
        if window != 60:
            print(f"rate_limits.window_seconds is fixed at 60 by wa-agent; ignoring {window}", file=sys.stderr)
        limits = {method: rl[key] for key, methods in _LIMIT_KEYS.items() if key in rl for method in methods}
        self.poll_timeout = int(poll_timeout)
        self._client = _Client(token, session=session, limits=limits, chunk_chars=chunk_chars, now=now, sleep=sleep)

    def poll(self, offset=""):
        """Returns (messages, next_offset). AuthError propagates (the loop exits); so does any other failure (the loop
        retries). A 409 — another poller replaced this one's cursor, the two-pollers-on-one-agent footgun AGENTS.md
        warns about — is logged and returns an empty batch with the offset kept."""
        try:
            return self._client.poll(offset or None, timeout=self.poll_timeout)
        except AuthError:
            raise
        except WhatsAppError as e:
            if e.code != "another_poller":
                raise
            code = re.search(r"error\.code (\d+)", e.detail)
            print(f"[{time.strftime('%H:%M:%S')}] poll: another poller is using this agent "
                  f"(HTTP 409{f', error.code {code.group(1)}' if code else ''})", file=sys.stderr)
            return [], offset

    def typing(self, message_id):
        self._client.typing(message_id)  # never raises: a receipt is cosmetic

    def download(self, media_id, dest_dir):
        """Returns (path, mime). Any failure is media_fetch_failed — "send it again" is the right advice for each."""
        try:
            return self._client.download(media_id, dest_dir)
        except WhatsAppError as e:
            raise errors.HisabError("media_fetch_failed", _detail(e)) from e

    def send(self, to, text):
        """Send text, split under chunk_chars on paragraph boundaries. Returns the list of message ids. A failure has
        no chat to reply in; it raises `internal` so the log line carries wa-agent's code and detail."""
        try:
            return [sent.id for sent in self._client.send(to, _unlink(text))]
        except WhatsAppError as e:
            raise errors.HisabError("internal", _detail(e)) from e

    def send_document(self, to, path, filename, caption=None):
        """Upload a local file as a generic binary and send it as a WhatsApp document. Returns the sent message id."""
        try:
            media_id = self._client.upload(path, DOCUMENT_MIME)
            return self._client.send_media(to, media_id, caption=caption, filename=filename, mime=DOCUMENT_MIME).id
        except WhatsAppError as e:
            raise errors.HisabError(EXPORT_CODES.get(e.code, "export_failed"), _detail(e)) from e

    def parts_for(self, text):
        """What `send` puts on the wire: wikilinks flattened, markdown converted, split, numbered."""
        return self._client.parts_for(_unlink(text))
