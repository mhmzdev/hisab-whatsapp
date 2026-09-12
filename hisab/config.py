"""Config: config.yaml (safe to commit) + .env (secrets). Paths resolve relative to the config file."""
import os
from pathlib import Path
import yaml

DEFAULTS = {
    "ledger": {"path": "./vault", "template": "personal", "currency": "PKR"},
    "model": {"id": "openai/gpt-4o-mini", "base_url": None, "api_key_env": None, "provider_pin": None, "agents_sdk": False},
    "transcription": {"provider": "openrouter", "model": "openai/whisper-1", "base_url": None, "api_key_env": None, "language": None, "gemini_model": "gemini-2.5-flash"},
    "memory": {"window_turns": 20, "keep_days": 30},
    "whatsapp": {"poll_timeout": 20, "chunk_chars": 3500},
    "state": {"path": "./data"},
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load(path=None):
    path = Path(path or os.environ.get("HISAB_CONFIG", "config.yaml"))
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    cfg = _merge(DEFAULTS, raw)
    root = path.resolve().parent
    cfg["ledger"]["path"] = str((root / cfg["ledger"]["path"]).resolve())
    cfg["state"]["path"] = str((root / cfg["state"]["path"]).resolve())
    cfg["secrets"] = {
        "whatsapp_token": os.environ.get("WHATSAPP_TOKEN", "").strip(),
        "openrouter_key": os.environ.get("OPENROUTER_API_KEY", "").strip(),
    }
    return cfg


def load_dotenv(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
