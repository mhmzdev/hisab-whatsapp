"""Idempotent reconciliation: the whole current Firestore tenant collection -> running/stopped
worker processes. Volatile fields (lastSeenAt, entriesThisMonth, createdAt) are never part of the
state hash, so activity/quota writes never bounce a worker that hasn't actually changed.

Status is runner-owned (firestore.rules lets no client write it). Two transitions live here:
  no status, `revoked`, or `error` with a new ciphertext, + decryptable keyCiphertext -> pending   (admission)
  worker exited with hisab.wa.AUTH_EXIT_CODE                                          -> error + lastError "auth"
pending -> connected is runner/verify.py's and any status -> revoked is runner/lifecycle.py's, both
driven by main.py's 2-second loop.
"""
import hashlib
import json
import os

from hisab.wa import AUTH_EXIT_CODE

from .crypto import CryptoError, decrypt
from .errors import LAST_ERROR_CODES
from .tenant_config import build_tenant_config, write_tenant_config

RUNNING_STATUSES = ("pending", "connected")

# The runner's own secret(s) — never handed to a tenant subprocess, which has no use for them and
# should not carry the key that decrypts every other tenant's WhatsApp token in its environment.
RUNNER_ONLY_ENV_KEYS = {"RUNNER_PRIVATE_KEY"}


def _tenant_env(token):
    env = {k: v for k, v in os.environ.items() if k not in RUNNER_ONLY_ENV_KEYS}
    env["WHATSAPP_TOKEN"] = token
    return env


def state_hash(env, cfg):
    payload = {
        "token": env.get("WHATSAPP_TOKEN"),
        "pending": cfg["pending"],
        "model": cfg["model"],
        "transcription": cfg["transcription"],
        "template": cfg["ledger"]["template"],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def key_fingerprint(ciphertext):
    """Identifies WHICH ciphertext failed, without storing it twice: a tenant parked in `error` is
    re-admitted only once the portal writes a different one."""
    return hashlib.sha256(str(ciphertext or "").encode()).hexdigest()[:16]


def admission(doc, runner_cfg):
    """Fields that accept a document into the runner (`pending`), or None. "pending" means "the runner
    decrypted this", never "the client asserted it" — a client cannot write status at all."""
    status = doc.get("status")
    resubmitted = status == "error" and doc.get("lastErrorKey") != key_fingerprint(doc.get("keyCiphertext"))
    # a revoked document's ciphertext was deleted by the runner, so any ciphertext on it is a new connection
    if status is not None and not resubmitted and status != "revoked":
        return None
    try:
        decrypt(doc["keyCiphertext"], runner_cfg["secrets"]["runner_private_key"])
    except (CryptoError, KeyError):
        return None
    # revokeRequestedAt is cleared too: a stale request left on a revoked document (client-writable) must
    # not revoke the fresh connection on the very next tick
    return {"status": "pending", "lastError": None, "lastErrorKey": None, "revokedAt": None, "revokeRequestedAt": None}


def reconcile(tenant_docs, runner_cfg, manager, update=None):
    """`update(uid, fields)` pushes runner-owned fields to Firestore (a None value deletes the field);
    main.py passes the listener's writer, tests pass a dict-collecting fake, and None means read-only."""
    seen = set()
    for uid, doc in tenant_docs.items():
        seen.add(uid)
        doc = dict(doc or {})
        fields = admission(doc, runner_cfg)
        if fields:
            if update:
                update(uid, fields)
            for k, v in fields.items():   # act on the accepted state now; the echoed snapshot is a no-op
                if v is None:
                    doc.pop(k, None)
                else:
                    doc[k] = v
        if doc.get("status") not in RUNNING_STATUSES:
            manager.stop(uid)
            continue
        try:
            cfg = build_tenant_config(uid, doc, runner_cfg)
            token = decrypt(doc["keyCiphertext"], runner_cfg["secrets"]["runner_private_key"])
            env = _tenant_env(token)
            config_path = write_tenant_config(uid, cfg, runner_cfg)
            manager.ensure_running(uid, config_path, env, state_hash(env, cfg))
        except (CryptoError, KeyError) as e:
            # one tenant's bad/missing ciphertext must not stall reconciliation for everyone else
            print(f"reconcile: skipping tenant {uid}: {e}")
            continue
    for uid in manager.running_uids() - seen:
        manager.stop(uid)


def on_worker_exit(uid, returncode, tenant_docs, update=None):
    """A worker exit -> the tenant-document write it deserves, or None. Only the auth failure is surfaced:
    it never becomes valid on retry, so the tenant parks in `error` (not a running status — no restart
    loop) with a lastError CODE the portal renders in three languages, until a new ciphertext arrives."""
    if returncode != AUTH_EXIT_CODE:
        return None
    assert "auth" in LAST_ERROR_CODES
    doc = tenant_docs.get(uid) or {}
    fields = {"status": "error", "lastError": "auth", "lastErrorKey": key_fingerprint(doc.get("keyCiphertext"))}
    if update:
        update(uid, fields)
    return fields
