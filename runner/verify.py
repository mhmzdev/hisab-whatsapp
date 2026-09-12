"""Nonce verification — pure and file-based, so it is fully testable without network.

The runner matches the nonce; the worker never learns what Firebase is. A muted (pending) worker
already records every inbound to messages.jsonl and the sender to creator.json (hisab/loop.py's
pending branch). This module reads those two files for ONE tenant and answers: did this tenant's
creator send an exact, case-insensitive `verify <nonce>` for THIS document's own nonce, before that
nonce expired? Tenant A's nonce can never verify tenant B because each check only ever sees A's
own document and A's own state dir.
"""
import json
import time
from pathlib import Path


def _epoch_ms(value):
    """nonceExpiresAt as the portal writes it (ms since the epoch), or as a Firestore timestamp."""
    if value is None:
        return None
    if hasattr(value, "timestamp"):
        return int(value.timestamp() * 1000)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return int(v if v > 1e11 else v * 1000)  # seconds vs milliseconds


def matches(text, nonce):
    """Exact, case-insensitive `verify <nonce>` — whitespace-tolerant, nothing else. A bare number is not valid."""
    return (text or "").strip().lower().split() == ["verify", str(nonce).strip().lower()]


def check_pending(uid, tenant_doc, runner_cfg, now_ms=None):
    """Returns the fields that connect this tenant ({status, creatorId, connectedAt}) or None."""
    nonce = str(tenant_doc.get("nonce") or "").strip()
    if not nonce:
        return None
    expires = _epoch_ms(tenant_doc.get("nonceExpiresAt"))
    state = Path(runner_cfg["data_root"]) / uid
    messages, creator_file = state / "messages.jsonl", state / "creator.json"
    if not messages.exists() or not creator_file.exists():
        return None
    try:
        creator = json.loads(creator_file.read_text(encoding="utf-8")).get("id")
    except (ValueError, OSError):
        return None
    if not creator:
        return None
    for line in messages.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("dir") != "in" or not matches(rec.get("text"), nonce):
            continue
        if expires is not None and int(rec.get("ts", 0)) * 1000 > expires:
            continue  # arrived after the nonce expired; the portal's "New code" issues a fresh one
        return {"status": "connected", "creatorId": creator, "connectedAt": now_ms or int(time.time() * 1000)}
    return None


def poll_pending(tenant_docs, runner_cfg):
    """check_pending over pending tenants only -> {uid: fields}. Connected and revoked tenants are skipped,
    so the runner's 2-second loop touches a handful of small files, never the whole collection."""
    out = {}
    for uid, doc in tenant_docs.items():
        if (doc or {}).get("status") != "pending":
            continue
        fields = check_pending(uid, doc, runner_cfg)
        if fields:
            out[uid] = fields
    return out
