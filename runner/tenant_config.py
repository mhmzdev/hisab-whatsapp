"""Per-tenant config: UID-scoped paths, global model/transcription — never tenant-supplied.

hisab/config.py:26-28 re-resolves ledger.path/state.path relative to the CONFIG FILE'S OWN
DIRECTORY when hisab.loop loads it. A relative string here (e.g. "vault/<uid>") would silently
land under runner_cfg["tenants_dir"]/<uid>/ instead of the intended vault root. runner/config.py
already resolves vault_root/data_root to absolute paths, so building on those keeps the result
absolute all the way through hisab.config.load's own join.
"""
from pathlib import Path

import yaml


def build_tenant_config(uid, tenant_doc, runner_cfg):
    return {
        "ledger": {
            "path": str(Path(runner_cfg["vault_root"]) / uid),
            "template": runner_cfg["ledger"]["template"],
            "currency": runner_cfg["ledger"]["currency"],
        },
        "model": dict(runner_cfg["model"]),
        "transcription": dict(runner_cfg["transcription"]),
        "state": {"path": str(Path(runner_cfg["data_root"]) / uid)},
        "pending": tenant_doc.get("status") != "connected",
        "quota": dict(runner_cfg["quota"]),
    }


def write_tenant_config(uid, cfg_dict, runner_cfg):
    tenant_dir = Path(runner_cfg["tenants_dir"]) / uid
    tenant_dir.mkdir(parents=True, exist_ok=True)
    path = tenant_dir / "config.yaml"
    path.write_text(yaml.safe_dump(cfg_dict, sort_keys=False), encoding="utf-8")
    return path
