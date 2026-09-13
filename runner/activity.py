"""Connected-tenant activity for the portal — computed by the runner from files the worker already
writes, so hisab/ learns nothing about Firebase (the same shape as verify.py).

Every value the Connected screen shows is on disk: the last inbound is the last `"dir": "in"` record
in data/<uid>/messages.jsonl; this month's model calls are data/<uid>/usage.json; the language is
vault/<uid>/settings.json; entries this month are the `n:` lines dated this month in the current
quarter file (undo removes the whole block, so a line count is exact). Nothing here is ledger
content — a count, a timestamp, a language code, a quota — and none of it is ever a description or
an amount.

Reads are gated on file mtimes through `cache`, so an idle tenant costs four stat calls per pass.
"""
import json
import re
import time
from datetime import date
from pathlib import Path

ENTRY_RE = re.compile(r"^(\d{4}-\d{2})-\d{2} .*; n:\d+\b")

ACTIVITY_FIELDS = ("lastSeenAt", "entriesThisMonth", "language", "usedThisMonth", "quotaLimit")


def _cached(cache, uid, name, path, compute, default):
    """compute(path) only when `path`'s mtime moved since the last pass; `default` when it is absent."""
    slot = cache.setdefault(uid, {})
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        slot.pop(name, None)
        return default
    hit = slot.get(name)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        value = compute(path)
    except (OSError, ValueError):
        value = default
    slot[name] = (mtime, value)
    return value


def _last_inbound_ms(path):
    last = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("dir") == "in" and rec.get("ts"):
            last = int(rec["ts"]) * 1000
    return last


def _entries_in_month(path, ym):
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines()
               if (m := ENTRY_RE.match(line)) and m.group(1) == ym)


def _quarter_file(vault, d):
    return vault / f"{d.year}-Q{(d.month - 1) // 3 + 1}.md"


def snapshot(uid, runner_cfg, cache, today=None):
    """The five activity fields for one tenant. A missing state dir or vault yields 0/None, never an error."""
    today = today or date.today()
    ym = today.strftime("%Y-%m")
    state = Path(runner_cfg["data_root"]) / uid
    vault = Path(runner_cfg["vault_root"]) / uid
    usage = _cached(cache, uid, "usage", state / "usage.json",
                    lambda p: json.loads(p.read_text(encoding="utf-8")), {})
    settings = _cached(cache, uid, "settings", vault / "settings.json",
                       lambda p: json.loads(p.read_text(encoding="utf-8")), {})
    return {
        "lastSeenAt": _cached(cache, uid, "messages", state / "messages.jsonl", _last_inbound_ms, None),
        "entriesThisMonth": _cached(cache, uid, "quarter", _quarter_file(vault, today),
                                    lambda p: _entries_in_month(p, ym), 0),
        "language": (settings or {}).get("language") or None,
        "usedThisMonth": int((usage or {}).get("calls", 0)) if (usage or {}).get("month") == ym else 0,
        "quotaLimit": (runner_cfg.get("quota") or {}).get("monthly_limit"),
    }


def poll_activity(tenant_docs, runner_cfg, cache, today=None):
    """snapshot() over connected tenants only -> {uid: fields}, a uid present only when at least one field
    differs from what its document already holds, so an idle collection produces no writes at all."""
    out = {}
    for uid, doc in tenant_docs.items():
        doc = doc or {}
        if doc.get("status") != "connected":
            continue
        fields = snapshot(uid, runner_cfg, cache, today)
        if any(doc.get(k) != v for k, v in fields.items()):
            out[uid] = fields
    return out
