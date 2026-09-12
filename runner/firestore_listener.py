"""One Firestore snapshot listener on `tenants` -> reconcile() on every change.

Not imported by tests/smoke.py (Firestore plumbing isn't no-network testable) and not imported
by runner/__init__.py, so firebase-admin stays optional for everything except actually running
the runner. Profile selection is the SDK's own convention, nothing custom: FIRESTORE_EMULATOR_HOST
set -> local emulator; unset with GOOGLE_APPLICATION_CREDENTIALS -> a real (non-production, per
spec) Firebase project. See runner/README.md.
"""
import firebase_admin
from firebase_admin import firestore

from .reconcile import reconcile


def listen(runner_cfg, manager):
    firebase_admin.initialize_app()
    db = firestore.client()

    def on_snapshot(docs, changes, read_time):
        reconcile({d.id: d.to_dict() for d in docs}, runner_cfg, manager)

    return db.collection("tenants").on_snapshot(on_snapshot)
