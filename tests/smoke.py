"""No-network smoke test: setup conversation → files, append/undo/report, store window, chunking. Needs hledger."""
import os, sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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
    print("ALL OK")
finally:
    shutil.rmtree(tmp)
