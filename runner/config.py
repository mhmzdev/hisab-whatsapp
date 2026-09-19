"""Runner config: runner/config.yaml (safe to commit, gitignored anyway) + RUNNER_PRIVATE_KEY from
the environment. vault_root/data_root/tenants_dir resolve to ABSOLUTE paths here, once, at load
time — see tenant_config.py for why that matters."""
import os
from pathlib import Path
import yaml

from hisab.config import DEFAULTS as WORKER_DEFAULTS, PROVIDERS, check_transcription

DEFAULTS = {
    "vault_root": "./runner-data/vault",
    "data_root": "./runner-data/data",
    "tenants_dir": "./runner-data/tenants",
    "inactive_root": "./runner-data/inactive",  # revoked tenants' ledgers, <uid>/<revokedAt>/, swept after retention_days
    "retention_days": 30,
    "ledger": {"template": "shop", "currency": "PKR"},
    "quota": {"monthly_limit": 1000},
    # the worker's own defaults: provider auto resolves in each worker from the runner's .env (hisab/config.py)
    "model": dict(WORKER_DEFAULTS["model"]),
    "transcription": dict(WORKER_DEFAULTS["transcription"]),
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load(path=None):
    path = Path(path or os.environ.get("RUNNER_CONFIG", "runner/config.yaml"))
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    cfg = _merge(DEFAULTS, raw)
    for section in ("model", "transcription"):
        provider = (cfg[section].get("provider") or "auto").lower()
        if provider not in PROVIDERS:
            raise SystemExit(f"{section}.provider must be 'auto', 'openrouter' or 'gemini', got {provider!r}")
    check_transcription(cfg["transcription"])  # refused here, not by every tenant worker crash-looping at load
    root = path.resolve().parent
    for key in ("vault_root", "data_root", "tenants_dir"):
        cfg[key] = str((root / cfg[key]).resolve())
    # A config written before inactive_root existed must not park revoked ledgers under runner/ (outside the
    # compose mount, lost on the next image build): unless set explicitly, inactive/ sits beside vault_root.
    if (raw or {}).get("inactive_root"):
        cfg["inactive_root"] = str((root / cfg["inactive_root"]).resolve())
    else:
        cfg["inactive_root"] = str(Path(cfg["vault_root"]).parent / "inactive")
    cfg["secrets"] = {"runner_private_key": os.environ.get("RUNNER_PRIVATE_KEY", "").strip()}
    return cfg
