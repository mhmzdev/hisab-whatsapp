"""No-network smoke test: setup conversation → files, append/undo/report, store window, chunking. Needs hledger."""
import io, json, os, sys, tempfile, shutil, time, zipfile
import contextlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hisab.archive import build_export_zip
from hisab.ledger import Ledger, LedgerError
from hisab.store import Store
from hisab.setup import Setup
from hisab.wa import to_whatsapp, _chunks
import hisab.wa as wa_mod
from hisab.wa import WhatsApp

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

    # rate limits: a fake clock proves pacing and backoff without any real waiting
    class FakeClock:
        def __init__(self, t=1_000_000.0):
            self.t = t
        def now(self):
            return self.t
        def sleep(self, secs):
            assert secs > 0, secs
            self.t += secs

    class FakeResponse:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.text = json.dumps(self._payload)
        def json(self):
            return self._payload
        def raise_for_status(self):
            if self.status_code // 100 != 2:
                raise RuntimeError(f"HTTP {self.status_code}")

    real_request = wa_mod.requests.request
    clock = FakeClock()
    rl_wa = WhatsApp("tok", rate_limits={"updates_per_min": 15, "window_seconds": 60},
                      now=clock.now, sleep=clock.sleep)
    wa_mod.requests.request = lambda verb, url, **kw: FakeResponse(200, {"entry": [], "next_offset": "off"})
    try:
        offset = ""
        for _ in range(30):  # a backlog drain: every long-poll returns instantly
            _, offset = rl_wa.poll(offset)
    finally:
        wa_mod.requests.request = real_request
    elapsed = clock.t - 1_000_000.0
    assert 60 <= elapsed < 120, elapsed  # 30 instant polls at 15/min must span at least one full window
    print(f"rate limit: 30 instant polls paced to {elapsed:.0f}s (limit 15/min) — poll loop can't exceed the window")

    calls = {"n": 0}
    def fake_429_then_ok(verb, url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(429, {"error": {"code": 130429, "message": "Too many requests"}})
        return FakeResponse(200, {"entry": [], "next_offset": "off2"})
    clock2 = FakeClock()
    rl_wa2 = WhatsApp("tok", rate_limits={"updates_per_min": 15, "window_seconds": 60},
                       now=clock2.now, sleep=clock2.sleep)
    wa_mod.requests.request = fake_429_then_ok
    try:
        # a single poll() absorbs the 429 internally: acquire() on the retry backs off until the
        # window can plausibly have reset, so the caller sees one slow success, not a fast failure
        msgs2, off2 = rl_wa2.poll("start")
        assert off2 == "off2", off2
    finally:
        wa_mod.requests.request = real_request
    elapsed2 = clock2.t - 1_000_000.0
    assert elapsed2 >= 55, elapsed2  # backs off toward a full window reset, not a flat 10s
    print(f"rate limit: 429 backs off ~{elapsed2:.0f}s toward a window reset, retry succeeds without re-entering the limit")

    def fake_409(verb, url, **kw):
        return FakeResponse(409, {"error": {"code": 1752041, "message": "conflict"}})
    clock3 = FakeClock()
    rl_wa3 = WhatsApp("tok", now=clock3.now, sleep=clock3.sleep)
    wa_mod.requests.request = fake_409
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            msgs3, off3 = rl_wa3.poll("keep")
    finally:
        wa_mod.requests.request = real_request
    assert msgs3 == [] and off3 == "keep", (msgs3, off3)
    logged = buf.getvalue()
    assert "409" in logged and "1752041" in logged and "another poller" in logged, logged
    print("rate limit: 409/1752041 logged as another-poller conflict, not a generic failure")
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

    # quota: model calls only (never raw messages), warn at 80%, hard-stop at the limit, free commands exempt,
    # and the count survives a fresh Hisab instance pointed at the same state dir (a runner restart/replay)
    class FakeAgent:
        def __init__(self):
            self.calls = 0
        def run(self, history, content, hint=None, max_rounds=6):
            self.calls += 1
            tools = type("FakeTools", (), {"last_block": None, "last_entry": self.calls})()
            return f"posted #{self.calls} — test", tools

    sample_vault = Path(__file__).resolve().parent.parent / "sample-vault"
    quota_state = tmp / "quota-state"
    quota_app = make_app(sample_vault, quota_state)
    quota_app.cfg["quota"] = {"monthly_limit": 5}
    fake_agent = FakeAgent()
    quota_app.agent = fake_agent
    wa_q = ExportFakeWA()
    for i in range(5):
        quota_app._handle_wa(wa_q, {"from": frm, "type": "text", "id": f"q{i}", "text": {"body": f"{100 + i} chai"}})
    replies = [m[2] for m in wa_q.sent if m[0] == "send"]
    assert fake_agent.calls == 5, fake_agent.calls
    assert not any("used this month" in r for r in replies[:3]), replies[:3]  # below 80% (calls 1-3): no warning
    assert all("used this month" in r for r in replies[3:5]), replies[3:5]  # at/above 80% (calls 4-5): warned
    quota_app._handle_wa(wa_q, {"from": frm, "type": "text", "id": "q-over", "text": {"body": "200 chai"}})
    assert fake_agent.calls == 5, "a blocked turn must never reach the model"
    assert "resumes next month" in wa_q.sent[-1][2], wa_q.sent[-1]
    wa_q2 = ExportFakeWA()
    quota_app._handle_wa(wa_q2, {"from": frm, "type": "text", "id": "q-help", "text": {"body": "/help"}})
    quota_app._handle_wa(wa_q2, {"from": frm, "type": "text", "id": "q-export", "text": {"body": "export-ledger"}})
    assert fake_agent.calls == 5 and len(wa_q2.documents) == 1, (fake_agent.calls, wa_q2.documents)
    print("quota: warn at 80%, hard-stop at limit, free commands exempt — ok")

    quota_app_restarted = make_app(sample_vault, quota_state)  # a fresh process, same state dir
    quota_app_restarted.cfg["quota"] = {"monthly_limit": 5}
    assert quota_app_restarted.store.usage() == {"month": time.strftime("%Y-%m"), "calls": 5}
    print("quota: usage persists across a restart — ok")

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
            "quota": {"monthly_limit": 1000},
        }
        tenant_doc = {"agentName": "kiryana-demo-agent", "creatorId": "923001234567", "status": "pending"}
        tcfg = build_tenant_config(uid, tenant_doc, runner_cfg)
        assert tcfg["ledger"]["path"].endswith(f"vault/{uid}"), tcfg
        assert tcfg["state"]["path"].endswith(f"data/{uid}"), tcfg
        assert "kiryana-demo-agent" not in tcfg["ledger"]["path"] and "923001234567" not in tcfg["state"]["path"]
        assert tcfg["quota"] == {"monthly_limit": 1000}, tcfg["quota"]
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
        assert fake_wa.sent == [], fake_wa.sent  # a verify-shaped message gets no nag: the runner is about to check it
        pending_app._handle_wa(fake_wa, {"from": "923001234567", "type": "audio", "id": "m2", "audio": {"id": "media1"}})
        for i in range(3, 7):
            pending_app._handle_wa(fake_wa, {"from": "923001234567", "type": "text", "id": f"m{i}", "text": {"body": f"{i}00 chai"}})
        sends = [x for x in fake_wa.sent if x[0] == "send"]
        assert len(sends) == 1 and "verify" in sends[0][2] and "اردو" in sends[0][2] and "Roman" in sends[0][2], fake_wa.sent
        assert not any(x[0] == "typing" for x in fake_wa.sent) and fake_wa.downloaded == [], (fake_wa.sent, fake_wa.downloaded)
        assert pending_app.store.lookup("m1") and pending_app.store.lookup("m2") and pending_app.store.lookup("m6")
        assert not pending_app.ledger.exists() and pending_app.store.usage()["calls"] == 0
        assert pending_app.store.creator() == "923001234567"
        from hisab.i18n import S as I18N
        for key in ("pending_reminder", "welcome"):
            assert all(I18N[key].get(lg) for lg in ("en", "ur", "roman")), key
        print("runner: pending mute + one reminder per window ok")

        # the welcome: exactly once across two worker instances on one state dir (a runner restart)
        hosted_cfg = dict(pending_cfg, pending=False, hosted=True, state={"path": str(tmp / "welcome-state")}, ledger={"path": str(tmp / "welcome-vault"), "template": "personal", "currency": "PKR"})
        Store(hosted_cfg["state"]["path"]).set_creator("923001234567")
        wa_w1, wa_w2 = FakeWA(), FakeWA()
        app_w1 = Hisab(hosted_cfg); app_w1._welcome_if_due(wa_w1)
        app_w2 = Hisab(hosted_cfg); app_w2._welcome_if_due(wa_w2)
        assert len(wa_w1.sent) == 1 and wa_w1.sent[0][1] == "923001234567" and "Connected" in wa_w1.sent[0][2] and "اردو" in wa_w1.sent[0][2], wa_w1.sent
        assert wa_w2.sent == [], wa_w2.sent
        assert app_w2.setup.active(), "the welcome opens setup so the next reply is the language answer"
        reply, done, _ = app_w2.setup.answer("اردو"); assert not done and "کھاتہ" in reply, reply  # first question, in Urdu
        selfhost_cfg = dict(hosted_cfg, hosted=False, state={"path": str(tmp / "selfhost-state")})
        Store(selfhost_cfg["state"]["path"]).set_creator("923001234567")
        wa_sh = FakeWA(); Hisab(selfhost_cfg)._welcome_if_due(wa_sh)
        assert wa_sh.sent == [], "self-host never greets on startup"
        print("runner: welcome exactly once ok")

        # auth failures stop the worker; everything else keeps the existing retry
        from hisab.wa import AuthError, AUTH_EXIT_CODE
        auth_wa = WhatsApp("tok", now=clock.now, sleep=clock.sleep)
        for status, payload in ((401, {"error": {"code": 190}}), (400, {"error": {"code": 100}})):
            wa_mod.requests.request = lambda verb, url, **kw: FakeResponse(status, payload)
            try:
                auth_wa.poll(""); raise SystemExit(f"HTTP {status} did not raise AuthError")
            except AuthError:
                pass
        for status in (503, 500):
            wa_mod.requests.request = lambda verb, url, **kw: FakeResponse(status, {})
            try:
                auth_wa.poll(""); raise SystemExit(f"HTTP {status} did not raise")
            except AuthError:
                raise SystemExit(f"HTTP {status} must not be an AuthError")
            except RuntimeError:
                pass
        wa_mod.requests.request = real_request

        class ExitingWA:
            def __init__(self, exc): self.exc = exc
            def poll(self, offset): raise self.exc
            def send(self, *a): return []
        class Retried(Exception): pass
        def no_sleep(_): raise Retried()
        real_sleep, loop_mod.time.sleep = loop_mod.time.sleep, no_sleep
        real_wa_cls = wa_mod.WhatsApp
        exit_app = Hisab(dict(hosted_cfg, state={"path": str(tmp / "exit-state")}, secrets={"whatsapp_token": "tok", "openrouter_key": "fake-not-used"}, whatsapp={"poll_timeout": 20, "chunk_chars": 3500}))
        try:
            wa_mod.WhatsApp = lambda *a, **kw: ExitingWA(AuthError("401"))
            try:
                exit_app.run_whatsapp(); raise SystemExit("auth failure did not exit")
            except SystemExit as e:
                assert e.code == AUTH_EXIT_CODE, e.code
            wa_mod.WhatsApp = lambda *a, **kw: ExitingWA(ConnectionError("reset"))
            try:
                exit_app.run_whatsapp(); raise SystemExit("connection error did not retry")
            except Retried:
                pass
        finally:
            wa_mod.WhatsApp, loop_mod.time.sleep = real_wa_cls, real_sleep
        print("runner: auth failure exits, transient errors retry ok")

        from runner.workers import WorkerManager
        from runner.reconcile import reconcile

        class FakeProc:
            def __init__(self, code=None):
                self.code = code
            def terminate(self):
                pass
            def poll(self):
                return self.code

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

        # verification: pure, file-based, per tenant — see runner/verify.py
        from runner.verify import check_pending, poll_pending
        def tenant_state(uid, texts, creator="923001234567", ts=1_700_000_000):
            st = Store(Path(runner_cfg["data_root"]) / uid)
            st.set_creator(creator)
            for i, text in enumerate(texts):
                st.add(f"{uid}-{i}", "in", text)
            recs = [json.loads(l) for l in st.messages.read_text(encoding="utf-8").splitlines()]
            for r in recs: r["ts"] = ts
            st.messages.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
        live = {"status": "pending", "nonce": "482913", "nonceExpiresAt": 1_700_000_000_000 + 600_000}
        tenant_state("t-ok", ["hello", "482913", "VERIFY 482913"])
        got = check_pending("t-ok", live, runner_cfg, now_ms=1)
        assert got == {"status": "connected", "creatorId": "923001234567", "connectedAt": 1}, got
        tenant_state("t-bare", ["482913", "verify", "verify 482913 please"])
        assert check_pending("t-bare", live, runner_cfg) is None
        tenant_state("t-wrong", ["verify 111111"])
        assert check_pending("t-wrong", live, runner_cfg) is None
        tenant_state("t-late", ["verify 482913"], ts=1_700_000_000 + 601)
        assert check_pending("t-late", live, runner_cfg) is None, "a verify after nonceExpiresAt must not connect"
        assert check_pending("t-late", dict(live, nonceExpiresAt=None), runner_cfg) is not None  # no expiry recorded = no expiry check
        tenant_state("t-other", ["verify 482913"])  # tenant A's nonce sent to tenant B's agent
        assert check_pending("t-other", dict(live, nonce="999999"), runner_cfg) is None
        assert check_pending("t-nostate-at-all", live, runner_cfg) is None
        assert check_pending("t-ok", dict(live, nonce=""), runner_cfg) is None
        transitions = poll_pending({"t-ok": live, "t-other": dict(live, nonce="999999"), "t-done": dict(live, status="connected"), "t-wrong": live}, runner_cfg)
        assert list(transitions) == ["t-ok"] and transitions["t-ok"]["creatorId"] == "923001234567", transitions
        print("runner: verify ok")

        # admission and error surfacing: status is runner-owned, so both transitions live in reconcile.py
        from runner.reconcile import admission, on_worker_exit, key_fingerprint
        writes = []
        def fake_update(uid, fields): writes.append((uid, dict(fields)))
        os.environ["RUNNER_PRIVATE_KEY"] = priv
        try:
            launcher2 = FakeLauncher(); manager2 = WorkerManager(launcher=launcher2)
            reconcile({"t-new": {"keyCiphertext": ciphertext, "nonce": "482913"},
                       "t-junk": {"keyCiphertext": "not-a-ciphertext", "nonce": "482913"}}, runner_cfg, manager2, update=fake_update)
            assert writes == [("t-new", {"status": "pending", "lastError": None, "lastErrorKey": None})], writes
            assert manager2.running_uids() == {"t-new"} and launcher2.calls == 1, (manager2.running_uids(), launcher2.calls)
            reconcile({"t-new": {"keyCiphertext": ciphertext, "nonce": "482913", "status": "pending"}}, runner_cfg, manager2, update=fake_update)
            assert len(writes) == 1 and launcher2.calls == 1, "the echoed snapshot is a no-op"
            # the worker exits on a rejected token -> error + lastError code, and it is NOT restarted
            manager2._running["t-new"]["proc"].code = 3
            exited = manager2.reap(); assert exited == [("t-new", 3)] and manager2.running_uids() == set()
            doc_err = {"keyCiphertext": ciphertext, "nonce": "482913", "status": "pending"}
            fields = on_worker_exit("t-new", 3, {"t-new": doc_err}, update=fake_update)
            assert fields == {"status": "error", "lastError": "auth", "lastErrorKey": key_fingerprint(ciphertext)}, fields
            assert on_worker_exit("t-new", 1, {"t-new": doc_err}, update=fake_update) is None  # an ordinary crash is not a lastError
            doc_err = {**doc_err, **fields}
            reconcile({"t-new": doc_err}, runner_cfg, manager2, update=fake_update)
            assert manager2.running_uids() == set() and launcher2.calls == 1, "parked in error: no restart loop"
            # the user pastes a new key from the Connect screen: a different ciphertext re-admits the tenant
            ciphertext2 = seal("fake-wa-token-2", pub)
            assert admission({**doc_err, "keyCiphertext": ciphertext2}, runner_cfg) == {"status": "pending", "lastError": None, "lastErrorKey": None}
            assert admission(doc_err, runner_cfg) is None
            assert admission({**doc_err, "keyCiphertext": "garbage"}, runner_cfg) is None
            reconcile({"t-new": {**doc_err, "keyCiphertext": ciphertext2}}, runner_cfg, manager2, update=fake_update)
            assert manager2.running_uids() == {"t-new"} and writes[-1][1]["status"] == "pending", writes[-1]
            from runner.errors import LAST_ERROR_CODES
            assert set(LAST_ERROR_CODES) == {"auth"}, LAST_ERROR_CODES
        finally:
            del os.environ["RUNNER_PRIVATE_KEY"]
        print("runner: admission + lastError ok")

        # the browser's own sealing code (landing/app/portal/crypto.js) must open in the runner's PyNaCl
        import subprocess
        crypto_js = Path(__file__).resolve().parent.parent / "landing" / "app" / "portal" / "crypto.js"
        sodium_dir = crypto_js.parent.parent.parent / "node_modules" / "libsodium-wrappers"
        if shutil.which("node") and crypto_js.exists() and sodium_dir.exists():
            secret = "WAA-fake-token-اردو-✓"
            js = f"import({json.dumps(str(crypto_js))}).then(async m => process.stdout.write(await m.sealKey(process.argv[1], process.argv[2])))"
            out = subprocess.run(["node", "-e", js, secret, pub], capture_output=True, text=True, timeout=60)
            assert out.returncode == 0, out.stderr[-500:]
            assert decrypt(out.stdout.strip(), priv) == secret
            try:
                decrypt(out.stdout.strip(), wrong_priv); raise SystemExit("JS ciphertext opened with the wrong key")
            except CryptoError:
                pass
            print("runner: JS (libsodium) -> Python (PyNaCl) sealed-box round trip ok")
        else:
            print("runner: JS -> Python round trip skipped (needs node and landing/node_modules/libsodium-wrappers)")
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
