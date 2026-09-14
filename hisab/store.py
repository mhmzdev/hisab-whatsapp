"""Runtime state: poll offset, message store (JSONL keyed by WhatsApp id), entry-number map, setup state.

The store is independent of any model context: a quoted reply resolves here even after /clear.
"""
import json
import time
from pathlib import Path

from . import clock


class Store:
    def __init__(self, path, keep_days=30, timezone=clock.DEFAULT_TZ):
        self.dir = Path(path)
        self.tz = timezone or clock.DEFAULT_TZ
        self.dir.mkdir(parents=True, exist_ok=True)
        self.messages = self.dir / "messages.jsonl"
        self.keep_days = keep_days
        self.prune()

    # --- poll offset ---
    def offset(self):
        f = self.dir / "offset"
        return f.read_text().strip() if f.exists() else ""

    def set_offset(self, v):
        (self.dir / "offset").write_text(str(v))

    # --- small json files ---
    def _json(self, name, default):
        f = self.dir / name
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default

    def _put(self, name, data):
        (self.dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def creator(self):
        return self._json("creator.json", {}).get("id")

    def set_creator(self, user_id):
        self._put("creator.json", {"id": user_id})

    # --- hosted-mode markers (runner tenants only; self-host never writes these) ---
    def welcomed(self):
        """True once the one-time welcome went out. A marker file, not a Firestore field: exactly-once
        across worker restarts and crashes with no network involved."""
        return bool(self._json("welcomed.json", {}).get("ts"))

    def set_welcomed(self):
        self._put("welcomed.json", {"ts": int(time.time())})

    def last_reminder(self):
        """Epoch seconds of the last pending-tenant reminder, 0 if none."""
        return int(self._json("reminder.json", {}).get("ts", 0))

    def set_last_reminder(self, ts):
        self._put("reminder.json", {"ts": int(ts)})

    def setup_state(self):
        return self._json("setup.json", None)

    def set_setup_state(self, state):
        if state is None:
            f = self.dir / "setup.json"
            f.unlink(missing_ok=True)
        else:
            self._put("setup.json", state)

    # --- monthly model-call quota (hosted mode; self-host never reads this) ---
    def usage(self):
        """This calendar month's model-call count. Rolls over to 0 on a new month without a write,
        so a month boundary needs no cron — the next call just persists the reset."""
        data = self._json("usage.json", {})
        month = clock.today(self.tz).strftime("%Y-%m")  # the tenant's month, matching runner/activity.py
        return {"month": month, "calls": data.get("calls", 0) if data.get("month") == month else 0}

    def record_model_call(self):
        """Increment and persist this month's counter. Call once per model dispatch — never on
        retries within one dispatch, so a network blip inside one turn is not double-billed."""
        usage = self.usage()
        usage["calls"] += 1
        self._put("usage.json", usage)
        return usage["calls"]

    # --- messages ---
    def add(self, msg_id, direction, text, entry=None, extra=None):
        rec = {"id": msg_id, "dir": direction, "ts": int(time.time()), "text": text}
        if entry is not None:
            rec["entry"] = entry
        if extra:
            rec.update(extra)
        with self.messages.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _all(self):
        if not self.messages.exists():
            return []
        out = []
        for line in self.messages.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def lookup(self, msg_id):
        for rec in reversed(self._all()):
            if rec.get("id") == msg_id:
                return rec
        return None

    def entry_for_message(self, msg_id):  # noqa
        """Entry number posted in response to a message (searching both the inbound and its reply)."""
        for rec in reversed(self._all()):
            if rec.get("id") == msg_id and rec.get("entry") is not None:
                return rec["entry"]
        return None

    def window(self, turns):
        """Last N in/out messages as chat turns, oldest first, with a boundary at the last /clear."""
        recs = self._all()
        cut = 0
        for i, r in enumerate(recs):
            if r.get("clear"):
                cut = i + 1
        recs = recs[cut:]
        recs = [r for r in recs if r["dir"] in ("in", "out") and r.get("text")]
        recs = recs[-turns:]
        return [{"role": "user" if r["dir"] == "in" else "assistant", "content": r["text"]} for r in recs]

    def mark_clear(self):
        self.add("clear:%d" % int(time.time()), "sys", "", extra={"clear": True})

    def prune(self):
        if not self.messages.exists():
            return
        cutoff = int(time.time()) - self.keep_days * 86400
        keep = [json.dumps(r, ensure_ascii=False) for r in self._all() if r.get("ts", 0) >= cutoff]
        self.messages.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
