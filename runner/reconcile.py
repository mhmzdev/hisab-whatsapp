"""Idempotent reconciliation: the whole current Firestore tenant collection -> running/stopped
worker processes. Volatile fields (lastSeenAt, entriesThisMonth, createdAt) are never part of the
state hash, so activity/quota writes never bounce a worker that hasn't actually changed.
"""
import hashlib
import json
import os

from .crypto import CryptoError, decrypt
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


def reconcile(tenant_docs, runner_cfg, manager):
    seen = set()
    for uid, doc in tenant_docs.items():
        seen.add(uid)
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
