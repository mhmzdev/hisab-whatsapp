"""No-network smoke test: setup conversation → files, append/undo/report, store window, chunking. Needs hledger."""
import os, sys, tempfile, shutil, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hisab.archive import build_export_zip
from hisab.ledger import Ledger, LedgerError
from hisab.store import Store
from hisab.setup import Setup
from hisab.wa import to_whatsapp, _chunks

tmp = Path(tempfile.mkdtemp())
try:
    for mode, answers in (("personal", ["English", "personal", "PKR", "Alfalah bank, cash, Easypaisa wallet", "Alfalah 15", "salary, freelance", "Meezan fund", "yes"]),
                          ("shop", ["English", "shop", "PKR", "cash, Meezan bank", "Metro, Ali traders", "Bilal, Ahmed", "none", "rent 40000, salaries 60000"])):
        led = Ledger(tmp / mode); st = Store(tmp / f"state-{mode}"); su = Setup(led, st)
        q = su.start(parked="2500 coffee"); assert "اردو" in q
        for ans in answers:
            q, done, parked = su.answer(ans)
        assert done and parked == "2500 coffee", (mode, done, parked)
        assert led.exists() and led.check()
        names = led.account_names()
        assert any(a.startswith("assets:") for a in names), names
        print(f"[{mode}] setup ok — {len(names)} accounts, default {names[0] if names else None}")
        if mode == "shop":
            assert "~ monthly" in (led.dir / "accounts.md").read_text()
            print("[shop] periodic rules written; budget rows:", led.hledger("bal", "expenses", "--budget", "-p", "this month").stdout.count("["))
    led = Ledger(tmp / "personal")
    n1, _ = led.append("2026-09-08", "coffee", [("expenses:food:snacks", 2500, None), ("assets:bank:alfalah", None, None)])
    n2, _ = led.append("2026-09-08", "atm", [("assets:cash", 5000, None), ("assets:bank:alfalah", -5000, None), ("equity:transfer", None, None)])
    n3, _ = led.append("2026-09-08", "opening alfalah", [("assets:bank:alfalah", 100000, None), ("equity:opening", None, None)], tags=["opening:"])
    assert (n1, n2, n3) == (1, 2, 3)
    try:
        led.append("2026-09-08", "bad", [("expenses:nope", 1, None), ("assets:cash", None, None)]); raise SystemExit("bad account accepted")
    except LedgerError as e:
        print("rejected as expected:", str(e)[:60])
    try:
        led.append("2099-01-01", "future", [("expenses:other", 1, None), ("assets:cash", None, None)]); raise SystemExit("future accepted")
    except LedgerError:
        pass
    m = led.month_summary("2026-09"); assert m["out"] == "2,500" and m["entries"] == 2, m
    print("month:", m)
    print("owed:", led.report("owed")); print("balances:", led.report("balances"))
    removed = led.undo(1); assert "coffee" in removed
    assert led.month_summary("2026-09")["out"] == "0"
    assert led.next_entry_number() == 4, led.next_entry_number()
    assert led.add_account("assets:receivable:sadia") and "assets:receivable:sadia" in led.account_names()
    assert led.match_rule("chai 300 easypaisa se") == "expenses:food:snacks"
    led.learn_rule(["bykea"], "expenses:transport"); assert led.match_rule("bykea 200") == "expenses:transport"
    # export-ledger: prove inclusion AND exclusion — a leaked key is the worst bug this repo could ship
    (led.dir / ".env").write_text("WHATSAPP_TOKEN=secret\n", encoding="utf-8")
    (led.dir / "worker-state.json").write_text("{}", encoding="utf-8")
    (led.dir / "messages.jsonl").write_text('{"id":"1"}\n', encoding="utf-8")
    (led.dir / "receipt.jpg").write_bytes(b"\xff\xd8\xff\xe0")
    zpath = build_export_zip(led, tmp / "export.zip")
    with zipfile.ZipFile(zpath) as zf:
        names = set(zf.namelist())
    assert {"hisab.md", "accounts.md", "rules.md", "settings.json"} <= names, names
    assert any(n.startswith("2026-Q") and n.endswith(".md") for n in names), names
    leaked = names & {".env", "worker-state.json", "messages.jsonl", "receipt.jpg"}
    assert not leaked, f"export leaked: {leaked}"
    print("export: zip ok —", sorted(names))
    st = Store(tmp / "s"); st.add("a", "in", "hi"); st.add("b", "out", "posted #1", entry=1); st.add("a", "note", "", entry=1)
    assert st.entry_for_message("a") == 1 and st.entry_for_message("b") == 1 and len(st.window(20)) == 2
    st.mark_clear(); st.add("c", "in", "after"); assert len(st.window(20)) == 1
    assert to_whatsapp("**bold** and [[page|label]]\n# Head\n- item") == "*bold* and label\n*Head*\n• item"
    assert len(_chunks("a" * 8000, 3500)) == 3 and _chunks("p1\n\np2", 3500) == ["p1\n\np2"]
    sample = Ledger(Path(__file__).resolve().parent.parent / "sample-vault")
    af = sample.afford("2026-09"); assert len(sample.periodic_rules()) == 2, sample.periodic_rules()
    assert [d for d, _ in af["not_yet_paid_this_month"]] == [], af  # rent and salaries both have September postings
    af8 = sample.afford("2026-08"); assert len(af8["not_yet_paid_this_month"]) == 2, af8
    print("afford:", af["can_afford"], "| August pending:", af8["not_yet_paid_this_month"])
    # urdu flow: questions come back in urdu script, settings persisted
    led = Ledger(tmp / "ur"); st = Store(tmp / "state-ur"); su = Setup(led, st); su.start()
    r, _, _ = su.answer("اردو"); assert "ذاتی" in r, r
    r, _, _ = su.answer("ذاتی"); assert "کرنسی" in r, r
    for a in ["PKR", "cash", "نہیں", "salary", "نہیں", "نہیں"]:
        r, done, _ = su.answer(a)
    assert done and led.language() == "ur" and "سیٹ اپ مکمل" in r, (done, r)
    print("urdu setup ok")

    # export-ledger over the WhatsApp transport: exact command, intercepted before the model loop,
    # ships a document (not chat text), respects the 16 MB cap, and never needs a model key to run
    import hisab.loop as loop_mod
    from hisab.loop import Hisab

    class ExportFakeWA:
        def __init__(self):
            self.sent, self.documents = [], []
        def typing(self, mid):
            self.sent.append(("typing", mid))
        def send(self, frm, text):
            self.sent.append(("send", frm, text)); return []
        def send_document(self, to, path, filename, caption=None):
            self.documents.append((to, str(path), filename, caption)); return "wamid.doc1"

    def make_app(ledger_path, state_path):
        return Hisab({
            "pending": False,
            "ledger": {"path": str(ledger_path), "template": "personal", "currency": "PKR"},
            "model": {"id": "openai/gpt-4o-mini", "base_url": None, "api_key_env": None, "provider_pin": None, "agents_sdk": False},
            "transcription": {"provider": "openrouter", "model": "openai/whisper-1", "base_url": None, "api_key_env": None, "language": None, "gemini_model": "gemini-2.5-flash"},
            "memory": {"window_turns": 20, "keep_days": 30},
            "whatsapp": {"poll_timeout": 20, "chunk_chars": 3500},
            "state": {"path": str(state_path)},
            "secrets": {"whatsapp_token": "", "openrouter_key": "fake-not-used"},
        })

    frm = "923001234567"
    connected_app = make_app(tmp / "personal", tmp / "connected-state")  # has the planted .env etc. from the archive test above
    wa1 = ExportFakeWA()
    connected_app._handle_wa(wa1, {"from": frm, "type": "text", "id": "exp1", "text": {"body": "export-ledger"}})
    assert len(wa1.documents) == 1 and wa1.sent == [("typing", "exp1")], (wa1.documents, wa1.sent)
    to, path, filename, caption = wa1.documents[0]
    assert to == frm and filename.startswith("hisab-export-") and filename.endswith(".zip") and caption
    assert not Path(path).exists(), "sent export must be cleaned up locally"
    print("export: whatsapp document send ok —", filename)

    old_max = loop_mod.MAX_DOCUMENT_BYTES
    loop_mod.MAX_DOCUMENT_BYTES = 10  # force the size-cap branch without a real 16 MB fixture
    try:
        wa2 = ExportFakeWA()
        connected_app._handle_wa(wa2, {"from": frm, "type": "text", "id": "exp2", "text": {"body": "export-ledger"}})
    finally:
        loop_mod.MAX_DOCUMENT_BYTES = old_max
    assert wa2.documents == [] and wa2.sent[-1][0] == "send" and "MB" in wa2.sent[-1][2], (wa2.documents, wa2.sent)
    print("export: over-cap reply ok")

    empty_app = make_app(tmp / "no-ledger-yet", tmp / "empty-state")
    wa3 = ExportFakeWA()
    empty_app._handle_wa(wa3, {"from": frm, "type": "text", "id": "exp3", "text": {"body": "Export-Ledger"}})
    assert wa3.documents == [] and wa3.sent[-1][0] == "send", wa3.sent
    print("export: no-ledger reply ok")

    runner_dir = Path(__file__).resolve().parent.parent / "runner"
    if runner_dir.exists():
        from runner.crypto import CryptoError, decrypt, generate_keypair, seal
        pub, priv = generate_keypair()
        ciphertext = seal("fake-whatsapp-token", pub)
        assert decrypt(ciphertext, priv) == "fake-whatsapp-token"
        _, wrong_priv = generate_keypair()
        try:
            decrypt(ciphertext, wrong_priv); raise SystemExit("decrypt with wrong key accepted")
        except CryptoError:
            pass
        print("runner: crypto ok")
        from hisab.config import load as hisab_load
        from runner.tenant_config import build_tenant_config, write_tenant_config
        uid = "abc123uid"
        runner_cfg = {
            "vault_root": str(tmp / "vault"), "data_root": str(tmp / "data"),
            "tenants_dir": str(tmp / "tenants-elsewhere"),  # deliberately not under vault_root/data_root
            "ledger": {"template": "shop", "currency": "PKR"},
            "model": {"id": "fake-model-id"}, "transcription": {"provider": "fake-provider"},
        }
        tenant_doc = {"agentName": "kiryana-demo-agent", "creatorId": "923001234567", "status": "pending"}
        tcfg = build_tenant_config(uid, tenant_doc, runner_cfg)
        assert tcfg["ledger"]["path"].endswith(f"vault/{uid}"), tcfg
        assert tcfg["state"]["path"].endswith(f"data/{uid}"), tcfg
        assert "kiryana-demo-agent" not in tcfg["ledger"]["path"] and "923001234567" not in tcfg["state"]["path"]
        tenant_doc_bogus = dict(tenant_doc, model={"id": "should-be-ignored"})
        assert build_tenant_config(uid, tenant_doc_bogus, runner_cfg)["model"] == runner_cfg["model"]
        written = write_tenant_config(uid, tcfg, runner_cfg)
        loaded = hisab_load(written)
        vault_root_resolved, data_root_resolved = str(Path(runner_cfg["vault_root"]).resolve()), str(Path(runner_cfg["data_root"]).resolve())
        assert loaded["ledger"]["path"].startswith(vault_root_resolved) and uid in loaded["ledger"]["path"], loaded["ledger"]["path"]
        assert loaded["state"]["path"].startswith(data_root_resolved) and uid in loaded["state"]["path"], loaded["state"]["path"]
        print("runner: tenant_config ok")

        from hisab.loop import Hisab

        class FakeWA:
            def __init__(self):
                self.sent, self.downloaded = [], []
            def typing(self, mid):
                self.sent.append(("typing", mid))
            def send(self, frm, text):
                self.sent.append(("send", frm, text)); return []
            def download(self, media_id, media_dir):
                self.downloaded.append(media_id); return None, None

        pending_cfg = {
            "pending": True,
            "ledger": {"path": str(tmp / "pending-vault"), "template": "personal", "currency": "PKR"},
            "model": {"id": "openai/gpt-4o-mini", "base_url": None, "api_key_env": None, "provider_pin": None, "agents_sdk": False},
            "transcription": {"provider": "openrouter", "model": "openai/whisper-1", "base_url": None, "api_key_env": None, "language": None, "gemini_model": "gemini-2.5-flash"},
            "memory": {"window_turns": 20, "keep_days": 30},
            "whatsapp": {"poll_timeout": 20, "chunk_chars": 3500},
            "state": {"path": str(tmp / "pending-state")},
            "secrets": {"whatsapp_token": "", "openrouter_key": "fake-not-used"},
        }
        pending_app = Hisab(pending_cfg)
        fake_wa = FakeWA()
        pending_app._handle_wa(fake_wa, {"from": "923001234567", "type": "text", "id": "m1", "text": {"body": "verify 482913"}})
        pending_app._handle_wa(fake_wa, {"from": "923001234567", "type": "audio", "id": "m2", "audio": {"id": "media1"}})
        assert fake_wa.sent == [] and fake_wa.downloaded == [], (fake_wa.sent, fake_wa.downloaded)
        assert pending_app.store.lookup("m1") and pending_app.store.lookup("m2")
        assert not pending_app.ledger.exists()
        print("runner: pending mute ok")

        from runner.workers import WorkerManager
        from runner.reconcile import reconcile

        class FakeProc:
            def terminate(self):
                pass

        class FakeLauncher:
            def __init__(self):
                self.calls = 0
                self.last_env = None
            def __call__(self, args, env):
                self.calls += 1
                self.last_env = env
                return FakeProc()

        runner_cfg["secrets"] = {"runner_private_key": priv}
        ciphertext = seal("fake-wa-token", pub)
        rtenant, launcher = "tenant-xyz", FakeLauncher()
        manager = WorkerManager(launcher=launcher)
        os.environ["RUNNER_PRIVATE_KEY"] = priv  # simulate the runner's own env; must never reach a tenant subprocess
        try:
            reconcile({rtenant: {"status": "pending", "keyCiphertext": ciphertext, "lastSeenAt": "2026-09-01"}}, runner_cfg, manager)
            reconcile({rtenant: {"status": "pending", "keyCiphertext": ciphertext, "lastSeenAt": "2026-09-02", "entriesThisMonth": 5}}, runner_cfg, manager)
            assert launcher.calls == 1, launcher.calls  # idempotent: volatile-only changes don't restart
            assert "RUNNER_PRIVATE_KEY" not in launcher.last_env, "tenant subprocess must not inherit the runner's decryption key"
            reconcile({rtenant: {"status": "connected", "keyCiphertext": ciphertext, "lastSeenAt": "2026-09-03"}}, runner_cfg, manager)
            assert launcher.calls == 2, launcher.calls  # status flip -> exactly one restart
            assert manager.running_uids() == {rtenant}
            reconcile({rtenant: {"status": "revoked", "keyCiphertext": ciphertext}}, runner_cfg, manager)  # explicit revoke, doc still present
            assert manager.running_uids() == set()
            reconcile({rtenant: {"status": "connected", "keyCiphertext": ciphertext, "lastSeenAt": "2026-09-04"}}, runner_cfg, manager)
            assert launcher.calls == 3 and manager.running_uids() == {rtenant}
            reconcile({}, runner_cfg, manager)  # tenant document removed entirely
            assert manager.running_uids() == set()
            # a corrupt tenant must not stall reconciliation for a healthy one in the same batch
            good, bad = "tenant-good", "tenant-bad"
            reconcile({
                good: {"status": "pending", "keyCiphertext": ciphertext, "lastSeenAt": "2026-09-01"},
                bad: {"status": "pending", "keyCiphertext": "not-valid-base64-ciphertext", "lastSeenAt": "2026-09-01"},
            }, runner_cfg, manager)
            assert manager.running_uids() == {good}, manager.running_uids()
        finally:
            del os.environ["RUNNER_PRIVATE_KEY"]
        print("runner: reconcile ok")
    else:
        print("runner: skipped (no runner/)")
    landing_strings = Path(__file__).resolve().parent.parent / "landing" / "content" / "strings.json"
    if landing_strings.exists():
        from check_landing import run as check_landing_run
        landing_failures = check_landing_run(Path(__file__).resolve().parent.parent)
        assert not landing_failures, landing_failures
        print("landing: ok")
    else:
        print("landing: skipped (no landing/)")
    print("ALL OK")
finally:
    shutil.rmtree(tmp)
