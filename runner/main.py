"""Runner entrypoint: python -m runner.main"""
import signal
import time

from hisab.config import load_dotenv

from . import config as runner_config
from .firestore_listener import listen
from .reconcile import on_worker_exit
from .verify import poll_pending
from .workers import WorkerManager

POLL_SECONDS = 2  # the floor on verification latency: pending tenants' state dirs are re-read this often


def tick(feed, runner_cfg, manager):
    """One pass of the idle loop: surface worker exits, then look for verify messages. Both go through
    Firestore, whereupon the snapshot listener re-runs reconcile() and the `pending` flag in the state
    hash restarts a freshly connected tenant's worker unmuted."""
    with feed.lock:
        exited = manager.reap()
        for uid, code in exited:
            print(f"worker {uid} exited with code {code}", flush=True)
            if on_worker_exit(uid, code, feed.docs, update=feed.update) is None:
                feed.reconcile()  # an ordinary crash: start it again
        for uid, fields in poll_pending(feed.docs, runner_cfg).items():
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
    while not stop["go"]:
        time.sleep(POLL_SECONDS)
        try:
            tick(feed, cfg, manager)
        except Exception as e:  # a Firestore hiccup must not kill the runner
            print(f"tick failed: {e}", flush=True)
    feed.unsubscribe()
    for uid in list(manager.running_uids()):
        manager.stop(uid)


if __name__ == "__main__":
    main()
