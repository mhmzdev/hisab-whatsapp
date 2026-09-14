"""Revoke and retention — the two runner-owned transitions that end a tenant (#5).

Revoke is a client REQUEST (`revokeRequestedAt`, the one client field that starts a transition —
firestore.rules) and a runner ACTION: stop the worker and wait for it to exit, move the vault and
state dir under inactive_root/<uid>/<revokedAt>/ with a revoked.json marker, delete the per-tenant
config, then write `status: "revoked"` and delete the ciphertext, the creator, the nonce and every
activity field. In that order, so a crash between steps is safe: the request is still on the
document at the next tick, a move whose source is gone is skipped, and the write is repeated.

Retention is a sweep, not a job: an inactive dir whose marker is older than retention_days is
removed. Only a directory carrying the marker, directly under inactive_root, is ever touched.

Reconnecting after a revoke is a NEW tenant on the same uid (reconcile.admission re-admits a revoked
document that carries a decryptable ciphertext); vault/<uid> no longer exists, so setup runs from
zero. The retained copy is for the operator to hand back on request during the retention window.
"""
import json
import shutil
import time
from pathlib import Path

from .activity import ACTIVITY_FIELDS

REVOKE_STATUSES = ("pending", "connected", "error")
MARKER = "revoked.json"


def revoke_fields(now_ms):
    fields = {"status": "revoked", "revokedAt": now_ms, "keyCiphertext": None, "creatorId": None, "nonce": None,
              "nonceExpiresAt": None, "connectedAt": None, "revokeRequestedAt": None, "lastError": None, "lastErrorKey": None}
    fields.update({k: None for k in ACTIVITY_FIELDS})
    return fields


def revoke(uid, runner_cfg, manager, update=None, now_ms=None):
    """Stop, move aside, forget. Returns the fields written to the tenant document."""
    now_ms = now_ms or int(time.time() * 1000)
    manager.stop(uid)
    dest = Path(runner_cfg["inactive_root"]) / uid / str(now_ms)
    # media is processed, never stored (#33): nothing of a leaving user's voice or photos is retained
    shutil.rmtree(Path(runner_cfg["data_root"]) / uid / "media", ignore_errors=True)
    for name, root in (("vault", runner_cfg["vault_root"]), ("data", runner_cfg["data_root"])):
        src = Path(root) / uid
        if src.exists():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest / name))
    if dest.exists():
        (dest / MARKER).write_text(json.dumps({"revokedAt": now_ms}), encoding="utf-8")
    shutil.rmtree(Path(runner_cfg["tenants_dir"]) / uid, ignore_errors=True)
    fields = revoke_fields(now_ms)
    if update:
        update(uid, fields)
    print(f"tenant {uid}: revoked, ledger retained under {dest}", flush=True)
    return fields


def poll_revokes(tenant_docs, runner_cfg, manager, update=None, now_ms=None):
    """revoke() for every document carrying a revoke request in a status that can still be revoked.
    A `revoked` document with a stale request is ignored — the write that clears it may be in flight."""
    out = {}
    for uid, doc in tenant_docs.items():
        doc = doc or {}
        if doc.get("revokeRequestedAt") and doc.get("status") in REVOKE_STATUSES:
            out[uid] = revoke(uid, runner_cfg, manager, update, now_ms)
    return out


def sweep_inactive(runner_cfg, now_ms=None):
    """Delete inactive_root/<uid>/<ts>/ dirs whose marker is older than retention_days -> [deleted paths]."""
    now_ms = now_ms or int(time.time() * 1000)
    root = Path(runner_cfg["inactive_root"])
    cutoff = now_ms - int(runner_cfg.get("retention_days", 30)) * 86_400_000
    deleted = []
    if not root.is_dir():
        return deleted
    for uid_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for snap in sorted(p for p in uid_dir.iterdir() if p.is_dir()):
            marker = snap / MARKER
            if not marker.is_file():
                continue
            try:
                revoked_at = int(json.loads(marker.read_text(encoding="utf-8")).get("revokedAt", 0))
            except (ValueError, OSError):
                continue
            if revoked_at and revoked_at < cutoff:
                shutil.rmtree(snap, ignore_errors=True)
                deleted.append(snap)
        if not any(uid_dir.iterdir()):
            uid_dir.rmdir()
    if deleted:
        print(f"retention: removed {len(deleted)} inactive ledger(s) older than {runner_cfg.get('retention_days', 30)} days", flush=True)
    return deleted
