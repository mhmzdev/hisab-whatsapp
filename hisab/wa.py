"""WhatsApp Agent Platform client. Long-poll only; an agent may message only its creator."""
import json
import re
import time
from pathlib import Path
import requests

BASE = "https://api.whatsapp.com/agent/v1"
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024  # WhatsApp's platform cap for outbound documents


class WhatsApp:
    def __init__(self, token, poll_timeout=20, chunk_chars=3500):
        self.h = {"Authorization": f"Bearer {token}"}
        self.poll_timeout = min(int(poll_timeout), 25)
        self.chunk = int(chunk_chars)

    def poll(self, offset=""):
        """Returns (messages, next_offset). Raises requests exceptions on network failure."""
        params = {"limit": 50, "timeout": self.poll_timeout}
        if offset:
            params["offset"] = offset
        r = requests.get(f"{BASE}/updates", headers=self.h, params=params, timeout=self.poll_timeout + 10)
        if r.status_code == 204:
            return [], offset
        if r.status_code == 429:
            time.sleep(10)
            return [], offset
        r.raise_for_status()
        data = r.json()
        msgs = []
        for entry in data.get("entry", []):
            for ch in entry.get("changes", []):
                msgs.extend(ch.get("value", {}).get("messages", []) or [])
        return msgs, data.get("next_offset", offset)

    def download(self, media_id, dest_dir):
        meta = requests.get(f"{BASE}/media/{media_id}", headers=self.h, timeout=30).json()
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
            requests.post(f"{BASE}/statuses", headers=self.h, json={
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
            r = requests.post(f"{BASE}/messages", headers=self.h, json={
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
            r = requests.post(f"{BASE}/media", headers=self.h,
                               files={"file": (filename, f, "application/zip")},
                               data={"messaging_product": "whatsapp"}, timeout=60)
        if r.status_code // 100 != 2:
            raise RuntimeError(f"media upload failed: HTTP {r.status_code} {r.text[:300]}")
        media_id = r.json().get("id")
        doc = {"id": media_id, "filename": filename}
        if caption:
            doc["caption"] = caption
        r = requests.post(f"{BASE}/messages", headers=self.h, json={
            "messaging_product": "whatsapp", "to": to, "type": "document", "document": doc}, timeout=30)
        if r.status_code // 100 != 2:
            raise RuntimeError(f"send failed: HTTP {r.status_code} {r.text[:300]}")
        d = r.json()
        return (d.get("messages") or [{}])[0].get("id") or d.get("id") or f"out:{int(time.time()*1000)}"


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
