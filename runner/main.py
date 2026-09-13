"""Runner entrypoint: python -m runner.main"""
import signal
import time

from hisab.config import load_dotenv

from . import config as runner_config
from .firestore_listener import listen
from .activity import poll_activity
from .lifecycle import poll_revokes, sweep_inactive
from .reconcile import on_worker_exit
from .verify import poll_pending
from .workers import WorkerManager

POLL_SECONDS = 2  # the floor on verification latency: pending tenants' state dirs are re-read this often
ACTIVITY_SECONDS = 10  # how often connected tenants' activity fields are recomputed (a write only on change)
SWEEP_SECONDS = 3600  # how often inactive (revoked) ledgers past retention_days are removed


def tick(feed, runner_cfg, manager, clock=None):
    """One pass of the idle loop: surface worker exits, look for verify messages, then refresh activity.
    Every transition goes through Firestore, whereupon the snapshot listener re-runs reconcile() and
    the `pending` flag in the state hash restarts a freshly connected tenant's worker unmuted.
    `clock` holds the pass timestamps and the activity mtime cache across ticks."""
    clock = clock if clock is not None else {}
    with feed.lock:
        exited = manager.reap()
        for uid, code in exited:
            print(f"worker {uid} exited with code {code}", flush=True)
            if on_worker_exit(uid, code, feed.docs, update=feed.update) is None:
                feed.reconcile()  # an ordinary crash: start it again
        for uid, fields in poll_pending(feed.docs, runner_cfg).items():
            feed.update(uid, fields)
        # revokes before activity: a tenant whose fields were just deleted must not get them written back
        revoked = poll_revokes(feed.docs, runner_cfg, manager, update=feed.update)
        for uid in revoked:
            feed.docs[uid] = {**(feed.docs.get(uid) or {}), **revoked[uid]}  # act on the new state before the echo
        now = time.time()
        if now - clock.get("sweep", 0) >= SWEEP_SECONDS:
            clock["sweep"] = now
            sweep_inactive(runner_cfg)
        if now - clock.get("activity", 0) >= ACTIVITY_SECONDS:
            clock["activity"] = now
            for uid, fields in poll_activity(feed.docs, runner_cfg, clock.setdefault("cache", {})).items():
                feed.update(uid, fields)


def main():
    load_dotenv()
    cfg = runner_config.load()
    manager = WorkerManager()
    feed = listen(cfg, manager)
    print(f"Runner listening on tenants; vault_root={cfg['vault_root']}", flush=True)

    stop = {"go": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(go=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(go=True))
    clock = {}
    while not stop["go"]:
        time.sleep(POLL_SECONDS)
        try:
            tick(feed, cfg, manager, clock)
        except Exception as e:  # a Firestore hiccup must not kill the runner
            print(f"tick failed: {e}", flush=True)
    feed.unsubscribe()
    for uid in list(manager.running_uids()):
        manager.stop(uid)


if __name__ == "__main__":
    main()
