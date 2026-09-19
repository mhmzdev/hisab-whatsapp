"""Config: config.yaml (safe to commit) + .env (secrets). Paths resolve relative to the config file."""
import copy
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import yaml

from .clock import DEFAULT_TZ

OPENROUTER_URL = "https://openrouter.ai/api/v1"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
PROVIDERS = ("auto", "openrouter", "gemini")  # model.provider and transcription.provider

DEFAULTS = {
    "pending": False,  # hosted mode, runner-set: mute all outbound until a tenant is verified (#7)
    "hosted": False,  # hosted mode, runner-set: this tenant came through portal verification — enables the one-time welcome (#7)
    "quota": {"monthly_limit": None},  # hosted mode, runner-set: cap on model calls/month; None = unlimited (self-host)
    "ledger": {"path": "./vault", "template": "personal", "currency": "PKR"},
    # provider auto: OPENROUTER_API_KEY if set, else GEMINI_API_KEY (id → gemini_id). A pinned provider, or an explicit
    # model base_url/api_key_env, or transcription api_key_env, is never second-guessed by which keys happen to be in .env.
    "model": {"provider": "auto", "id": "openai/gpt-4o-mini", "gemini_id": "gemini-3.8-flash", "base_url": None, "api_key_env": None, "provider_pin": None},
    "transcription": {"provider": "auto", "model": "openai/whisper-1", "api_key_env": None, "language": None, "gemini_model": "gemini-2.5-flash"},
    "memory": {"window_turns": 20, "keep_days": 30},
    "whatsapp": {"poll_timeout": 20, "chunk_chars": 3500, "rate_limits": {
        # WhatsApp Agent Platform manual v1 §6: each its own rolling 60s counter, scoped per agent. The *_per_min keys
        # feed wa-agent's limiter; window_seconds is fixed at 60 by wa-agent (hisab/wa.py logs any other value).
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
    cfg = _merge(copy.deepcopy(DEFAULTS), raw)  # load() edits sections in place; DEFAULTS must never see it
    for section in ("model", "transcription"):
        provider = (cfg[section].get("provider") or "auto").lower()
        if provider not in PROVIDERS:
            raise SystemExit(f"{section}.provider must be 'auto', 'openrouter' or 'gemini', got {provider!r}")
        cfg[section]["provider"] = provider
    check_transcription(cfg["transcription"])
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
    resolve_providers(cfg)
    return cfg


def check_transcription(tc):
    """Refuse a transcription key that no longer means anything, rather than quietly sending voice notes elsewhere (#61)."""
    if tc.get("base_url"):
        raise SystemExit("transcription.base_url is no longer supported: voice notes go to OpenRouter or Gemini only "
                         "(transcription.provider). Remove it from the config.")


def _auto(env):
    if env.get("OPENROUTER_API_KEY", "").strip():
        return "openrouter"
    if env.get("GEMINI_API_KEY", "").strip():
        return "gemini"
    return "auto"  # no key at all: stays auto, and the agent names both keys when it refuses to start


def resolve_providers(cfg, env=os.environ):
    """Turn provider auto into openrouter or gemini from the keys present, in place. A custom endpoint (base_url or
    api_key_env set) is left exactly as written. After this, model.provider is openrouter, gemini, custom or auto (no key); it is informational."""
    m = cfg["model"]
    if m.get("base_url") or m.get("api_key_env"):
        m["provider"] = "gemini" if (m.get("base_url") or "").rstrip("/") == GEMINI_URL else "custom"  # a label for logs only
    else:
        m["provider"] = _auto(env) if m["provider"] == "auto" else m["provider"]
        if m["provider"] == "gemini":
            # an OpenRouter id is vendor/model and means nothing to Gemini; a bare id is already a Gemini one
            model_id = m["id"] if m.get("id") and "/" not in m["id"] else (m.get("gemini_id") or DEFAULTS["model"]["gemini_id"])
            m.update(base_url=GEMINI_URL, api_key_env="GEMINI_API_KEY", id=model_id)
    tc = cfg["transcription"]
    if tc["provider"] == "auto":
        # an explicitly named key variable is never second-guessed by which keys are present: it keeps the openrouter
        # default; otherwise Gemini only when it is the one key present
        tc["provider"] = "openrouter" if tc.get("api_key_env") else ("gemini" if _auto(env) == "gemini" else "openrouter")
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
