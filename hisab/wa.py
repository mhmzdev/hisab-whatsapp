"""WhatsApp Agent Platform client. Long-poll only; an agent may message only its creator."""
import json
import re
import sys
import time
from pathlib import Path
import requests

from . import errors

BASE = "https://api.whatsapp.com/agent/v1"
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024  # WhatsApp's platform cap for outbound documents

# Platform manual v1 §6 "Rate limits": each is its own rolling 60s counter, scoped per agent.
# media is per HTTP method (POST/GET/DELETE each get their own 12/min budget); only POST (upload)
# and GET (download) are exercised today. HTTP 429 carries error.code 130429.
DEFAULT_RATE_LIMITS = {
    "window_seconds": 60,
    "messages_per_min": 12,
    "statuses_per_min": 12,
    "updates_per_min": 15,
    "media_per_min": 12,
}
# HTTP 409 on /updates: another poller replaced this one's cursor — the two-pollers-on-one-agent
# footgun AGENTS.md warns about, named by the platform as error.code 1752041.

AUTH_EXIT_CODE = errors.exit_status("auth")  # hisab.loop's exit status on AuthError; the runner maps it back through hisab/errors.py


class AuthError(Exception):
    """The platform rejected the token itself — HTTP 401 (error.code 190) or an invalid-token 400
    (error.code 100). Unlike a 429, 503 or a dropped connection this never becomes valid on retry, so
    the poll loop lets it escape and exits with AUTH_EXIT_CODE instead of burning 12 polls a minute."""


class RateLimiter:
    """One rolling window per method, scoped exactly like the platform's own counters. `acquire`
    blocks (via the injected `sleep`) until a call would not exceed the limit; `penalize` marks a
    method's window as fully spent right now, so the next `acquire` backs off until it can
    plausibly have reset instead of guessing a flat delay."""

    def __init__(self, limits, window=60, now=time.time, sleep=time.sleep):
        self._limits = dict(limits)
        self._window = window
        self._now = now
        self._sleep = sleep
        self._calls = {method: [] for method in self._limits}

    def _drop_expired(self, method, t):
        q = self._calls[method]
        cutoff = t - self._window
        while q and q[0] <= cutoff:
            q.pop(0)

    def acquire(self, method):
        limit = self._limits.get(method)
        if not limit:
            return
        q = self._calls[method]
        while True:
            t = self._now()
            self._drop_expired(method, t)
            if len(q) < limit:
                q.append(t)
                return
            self._sleep(q[0] + self._window - t)

    def penalize(self, method):
        limit = self._limits.get(method)
        if not limit:
            return
        self._calls[method] = [self._now()] * limit


class WhatsApp:
    def __init__(self, token, poll_timeout=20, chunk_chars=3500, rate_limits=None, now=time.time, sleep=time.sleep):
        self.h = {"Authorization": f"Bearer {token}"}
        self.poll_timeout = min(int(poll_timeout), 25)
        self.chunk = int(chunk_chars)
        rl = {**DEFAULT_RATE_LIMITS, **(rate_limits or {})}
        self.limits = RateLimiter({
            "messages": rl["messages_per_min"],
            "statuses": rl["statuses_per_min"],
            "updates": rl["updates_per_min"],
            "media_post": rl["media_per_min"],
            "media_get": rl["media_per_min"],
        }, window=rl["window_seconds"], now=now, sleep=sleep)

    def _request(self, method, verb, url, **kwargs):
        """One rate-limited HTTP call. Retries once past a 429 — `acquire` on the retry backs off
        until the window can plausibly have reset, since `penalize` marked it fully spent."""
        for attempt in (1, 2):
            self.limits.acquire(method)
            r = requests.request(verb, url, **kwargs)
            if r.status_code == 429 and attempt == 1:
                self.limits.penalize(method)
                continue
            return r
        return r

    def poll(self, offset=""):
        """Returns (messages, next_offset). Raises requests exceptions on network failure."""
        params = {"limit": 50, "timeout": self.poll_timeout}
        if offset:
            params["offset"] = offset
        r = self._request("updates", "GET", f"{BASE}/updates", headers=self.h, params=params,
                           timeout=self.poll_timeout + 10)
        if r.status_code == 204:
            return [], offset
        if r.status_code == 429:
            return [], offset  # still throttled after backing off; try again next turn rather than crash the loop
        if r.status_code == 409:
            code = _error_code(r)
            print(f"[{time.strftime('%H:%M:%S')}] poll: another poller is using this agent "
                  f"(HTTP 409{f', error.code {code}' if code else ''})", file=sys.stderr)
            return [], offset
        if r.status_code == 401 or (r.status_code == 400 and _error_code(r) == 100):
            raise AuthError(f"WhatsApp rejected the token (HTTP {r.status_code}, error.code {_error_code(r)})")
        r.raise_for_status()
        data = r.json()
        msgs = []
        for entry in data.get("entry", []):
            for ch in entry.get("changes", []):
                msgs.extend(ch.get("value", {}).get("messages", []) or [])
        return msgs, data.get("next_offset", offset)

    def download(self, media_id, dest_dir):
        meta = self._request("media_get", "GET", f"{BASE}/media/{media_id}", headers=self.h, timeout=30).json()
        url = meta.get("url")
        if not url:
            return None, None
        mime = meta.get("mime_type", "")
        ext = _ext(mime)
        path = Path(dest_dir) / f"{media_id}{ext}"
        with requests.get(url, headers=self.h, timeout=60, stream=True) as r:
            r.raise_for_status()
            path.write_bytes(r.content)
        return path, mime

    def typing(self, message_id):
        try:
            self._request("statuses", "POST", f"{BASE}/statuses", headers=self.h, json={
                "messaging_product": "whatsapp", "status": "read", "message_id": message_id,
                "typing_indicator": {"type": "text"}}, timeout=10)
        except requests.RequestException:
            pass

    def send(self, to, text):
        """Send text, split under the 4096 cap on paragraph boundaries. Returns list of message ids."""
        body = to_whatsapp(text)
        parts = _chunks(body, self.chunk)
        ids = []
        for i, p in enumerate(parts, 1):
            if len(parts) > 1:
                p = f"{p}\n\n({i}/{len(parts)})"
            r = self._request("messages", "POST", f"{BASE}/messages", headers=self.h, json={
                "messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": p}}, timeout=30)
            if r.status_code // 100 != 2:
                raise RuntimeError(f"send failed: HTTP {r.status_code} {r.text[:300]}")
            d = r.json()
            ids.append((d.get("messages") or [{}])[0].get("id") or d.get("id") or f"out:{int(time.time()*1000)}")
            if i < len(parts):
                time.sleep(1)
        return ids

    def send_document(self, to, path, filename, caption=None):
        """Upload a local file and send it as a WhatsApp document. Returns the sent message id."""
        path = Path(path)
        with path.open("rb") as f:
            r = self._request("media_post", "POST", f"{BASE}/media", headers=self.h,
                               files={"file": (filename, f, "application/zip")},
                               data={"messaging_product": "whatsapp"}, timeout=60)
        if r.status_code // 100 != 2:
            raise RuntimeError(f"media upload failed: HTTP {r.status_code} {r.text[:300]}")
        media_id = r.json().get("id")
        doc = {"id": media_id, "filename": filename}
        if caption:
            doc["caption"] = caption
        r = self._request("messages", "POST", f"{BASE}/messages", headers=self.h, json={
            "messaging_product": "whatsapp", "to": to, "type": "document", "document": doc}, timeout=30)
        if r.status_code // 100 != 2:
            raise RuntimeError(f"send failed: HTTP {r.status_code} {r.text[:300]}")
        d = r.json()
        return (d.get("messages") or [{}])[0].get("id") or d.get("id") or f"out:{int(time.time()*1000)}"


def _error_code(r):
    try:
        return (r.json() or {}).get("error", {}).get("code")
    except ValueError:
        return None


def _ext(mime):
    m = (mime or "").lower()
    for k, v in (("image/jpeg", ".jpg"), ("image/png", ".png"), ("audio/ogg", ".ogg"), ("audio/mp4", ".m4a"),
                 ("audio/aac", ".aac"), ("audio/mpeg", ".mp3"), ("audio/amr", ".amr"), ("application/pdf", ".pdf")):
        if m.startswith(k):
            return v
    return ""


def to_whatsapp(text):
    """Markdown → WhatsApp formatting. Code fences are kept (WhatsApp renders ``` as monospace)."""
    out = []
    for line in text.splitlines():
        line = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", line)
        line = re.sub(r"\[\[([^\]#|]*)(#[^\]|]*)?\]\]", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", line)
        line = re.sub(r"^#{1,6} +(.*)$", r"*\1*", line)
        line = re.sub(r"^\s*[-*] ", "• ", line)
        out.append(line.rstrip())
    return "\n".join(out).strip()


def _chunks(text, max_len):
    paras = text.split("\n\n")
    parts, buf = [], ""
    for p in paras:
        while len(p) > max_len:
            if buf:
                parts.append(buf); buf = ""
            parts.append(p[:max_len]); p = p[max_len:]
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= max_len:
            buf = buf + "\n\n" + p
        else:
            parts.append(buf); buf = p
    if buf:
        parts.append(buf)
    return parts or [""]
