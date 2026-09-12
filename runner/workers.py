"""Per-tenant worker process lifecycle, keyed by Firebase uid.

The launcher is injectable so tests never spawn a real interpreter; it defaults to
subprocess.Popen(args, env=env) exec-ing the unchanged hisab.loop entrypoint.
"""
import subprocess


def _default_launcher(args, env):
    return subprocess.Popen(args, env=env)


class WorkerManager:
    def __init__(self, launcher=None):
        self.launcher = launcher or _default_launcher
        self._running = {}  # uid -> {"proc": handle, "hash": state_hash}

    def ensure_running(self, uid, config_path, env, state_hash):
        """No-op if uid is already running with this exact state_hash; otherwise stop-then-start."""
        current = self._running.get(uid)
        if current and current["hash"] == state_hash:
            return
        self.stop(uid)
        proc = self.launcher(["python", "-m", "hisab.loop", "--config", str(config_path)], env)
        self._running[uid] = {"proc": proc, "hash": state_hash}

    def stop(self, uid):
        current = self._running.pop(uid, None)
        if current:
            current["proc"].terminate()

    def reap(self):
        """Workers that exited on their own -> [(uid, returncode)], dropped from the running set so a later
        reconcile pass may start them again. Never reports a worker this manager stopped itself."""
        exited = []
        for uid, current in list(self._running.items()):
            code = current["proc"].poll()
            if code is not None:
                exited.append((uid, code))
                del self._running[uid]
        return exited

    def running_uids(self):
        return set(self._running)
