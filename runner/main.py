"""Runner entrypoint: python -m runner.main"""
import signal
import time

from hisab.config import load_dotenv

from . import config as runner_config
from .firestore_listener import listen
from .workers import WorkerManager


def main():
    load_dotenv()
    cfg = runner_config.load()
    manager = WorkerManager()
    watch = listen(cfg, manager)
    print(f"Runner listening on tenants; vault_root={cfg['vault_root']}")

    stop = {"go": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(go=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(go=True))
    while not stop["go"]:
        time.sleep(1)
    watch.unsubscribe()
    for uid in list(manager.running_uids()):
        manager.stop(uid)


if __name__ == "__main__":
    main()
