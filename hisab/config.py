"""Config: config.yaml (safe to commit) + .env (secrets). Paths resolve relative to the config file."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import yaml

from .clock import DEFAULT_TZ

DEFAULTS = {
    "pending": False,  # hosted mode, runner-set: mute all outbound until a tenant is verified (#7)
    "hosted": False,  # hosted mode, runner-set: this tenant came through portal verification — enables the one-time welcome (#7)
    "quota": {"monthly_limit": None},  # hosted mode, runner-set: cap on model calls/month; None = unlimited (self-host)
    "ledger": {"path": "./vault", "template": "personal", "currency": "PKR"},
    "model": {"id": "openai/gpt-4o-mini", "base_url": None, "api_key_env": None, "provider_pin": None},
    "transcription": {"provider": "openrouter", "model": "openai/whisper-1", "base_url": None, "api_key_env": None, "language": None, "gemini_model": "gemini-2.5-flash"},
    "memory": {"window_turns": 20, "keep_days": 30},
    "whatsapp": {"poll_timeout": 20, "chunk_chars": 3500, "rate_limits": {
        # WhatsApp Agent Platform manual v1 §6: each its own rolling 60s counter, scoped per agent.
        "window_seconds": 60, "messages_per_min": 12, "statuses_per_min": 12, "updates_per_min": 15, "media_per_min": 12,
    }},
    "state": {"path": "./data"},
    "timezone": DEFAULT_TZ,  # IANA name; every ledger date, quota month and export name reads the clock in it (#36, #40)
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
    provider = (cfg["transcription"].get("provider") or "openrouter").lower()
    if provider not in ("openrouter", "gemini"):
        raise SystemExit(f"transcription.provider must be 'openrouter' or 'gemini', got {provider!r}")
    try:
        ZoneInfo(str(cfg["timezone"]))
    except (ZoneInfoNotFoundError, ValueError):
        raise SystemExit(f"timezone must be an IANA name like 'Asia/Karachi', got {cfg['timezone']!r}")
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
