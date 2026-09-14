"""The one clock. Every ledger date, quota month and export name is "now" in the configured timezone, never
the process clock: both images run in UTC, which dated a Pakistani user's after-midnight entries yesterday (#40).
Stdlib only; the runner imports it too. Tests patch _utcnow."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Asia/Karachi"


def _utcnow():
    return datetime.now(timezone.utc)


def now(tz=DEFAULT_TZ):
    return _utcnow().astimezone(ZoneInfo(tz or DEFAULT_TZ))


def today(tz=DEFAULT_TZ):
    return now(tz).date()
