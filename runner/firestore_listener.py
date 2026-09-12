"""One Firestore snapshot listener on `tenants` -> reconcile() on every change, plus the runner's
only write path back to Firestore.

Not imported by tests/smoke.py (Firestore plumbing isn't no-network testable) and not imported
by runner/__init__.py, so firebase-admin stays optional for everything except actually running
the runner. Profile selection is the SDK's own convention, nothing custom: FIRESTORE_EMULATOR_HOST
set -> local emulator (no credentials at all; the project id comes from GCLOUD_PROJECT);
unset with GOOGLE_APPLICATION_CREDENTIALS -> a real (non-production, per spec) Firebase project.
See runner/README.md.
"""
import os
import threading

from google.cloud import firestore as gcf

from .reconcile import reconcile


def _client():
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        # firebase-admin insists on Application Default Credentials even against the emulator, which
        # has none; the underlying client takes anonymous credentials and the same emulator env var.
        from google.auth.credentials import AnonymousCredentials
        project = os.environ.get("GCLOUD_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "demo-hisab"
        return gcf.Client(project=project, credentials=AnonymousCredentials())
    import firebase_admin
    from firebase_admin import firestore
    firebase_admin.initialize_app()
    return firestore.client()


class TenantFeed:
    """`docs` is the latest snapshot of the whole collection (main.py's 2-second loop reads it);
    `update` pushes runner-owned fields (None deletes a field); `lock` serialises reconcile() between
    the listener thread and the main loop."""

    def __init__(self, runner_cfg, manager):
        self.cfg, self.manager = runner_cfg, manager
        self.docs = {}
        self.lock = threading.RLock()
        self.db = _client()
        self._watch = self.db.collection("tenants").on_snapshot(self._on_snapshot)

    def _on_snapshot(self, docs, changes, read_time):
        self.docs = {d.id: d.to_dict() for d in docs}
        self.reconcile()

    def reconcile(self):
        with self.lock:
            reconcile(self.docs, self.cfg, self.manager, update=self.update)

    def update(self, uid, fields):
        data = {k: (gcf.DELETE_FIELD if v is None else v) for k, v in fields.items()}
        self.db.collection("tenants").document(uid).update(data)
        print(f"tenant {uid}: {', '.join(f'{k}={v!r}' for k, v in fields.items())}", flush=True)

    def unsubscribe(self):
        self._watch.unsubscribe()


def listen(runner_cfg, manager):
    return TenantFeed(runner_cfg, manager)
