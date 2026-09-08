"""Regenerate sample-vault/: a kiryana store, two weeks, fake numbers, through the real code path."""
import sys, tempfile, shutil, random
from pathlib import Path
from datetime import date, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hisab.ledger import Ledger
from hisab.store import Store
from hisab.setup import Setup

random.seed(7)
out = Path(__file__).resolve().parent.parent / "sample-vault"
readme = (out / "README.md").read_text(encoding="utf-8") if (out / "README.md").exists() else None
shutil.rmtree(out, ignore_errors=True)
led = Ledger(out); tmp = Path(tempfile.mkdtemp())
su = Setup(led, Store(tmp)); su.start()
for a in ["shop", "PKR", "cash, Meezan bank", "Metro, Ali traders", "Bilal", "none", "rent 40000, salaries 60000"]:
    su.answer(a)
shutil.rmtree(tmp)
A = lambda d, desc, posts, tags=None: led.append(d, desc, posts, tags)
d0 = date(2026, 8, 24)
A(d0, "opening cash", [("assets:cash", 35000, None), ("equity:opening", None, None)], ["opening:"])
A(d0, "opening meezan", [("assets:bank:meezan", 210000, None), ("equity:opening", None, None)], ["opening:"])
A(d0, "opening owed to Metro", [("liabilities:payable:metro", -48000, None), ("equity:opening", None, None)], ["opening:"])
for i in range(15):
    d = d0 + timedelta(days=i + 1)
    sale = random.randint(18000, 26000) if d.weekday() == 4 else random.randint(36000, 58000)
    A(d, "aaj ki sale", [("assets:cash", sale, None), ("income:sales", None, None)])
    if i in (1, 5, 9, 13):
        A(d, "stock from Metro (udhaar)", [("expenses:stock", random.choice([22000, 31000, 27500]), None), ("liabilities:payable:metro", None, None)])
    if i in (3, 11):
        A(d, "stock from Ali traders cash", [("expenses:stock", random.choice([9500, 14000]), None), ("assets:cash", None, None)])
    if i in (2, 8, 12):
        A(d, "cash to bank", [("assets:bank:meezan", 40000, None), ("assets:cash", -40000, None), ("equity:transfer", None, None)])
    if i == 4:
        A(d, "Bilal advance", [("assets:staff:advance:bilal", 5000, None), ("assets:cash", None, None)])
    if i == 6:
        A(d, "paid Metro", [("liabilities:payable:metro", 40000, None), ("assets:bank:meezan", None, None)])
    if i == 7:
        A(d, "bijli bill", [("expenses:utilities:electricity", 11800, None), ("assets:bank:meezan", None, None)])
    if i == 8:
        A(d, "kiraya September", [("expenses:rent", 40000, None), ("assets:bank:meezan", None, None)])
    if i == 10:
        A(d, "shopper bags", [("expenses:supplies", 1800, None), ("assets:cash", None, None)])
    if i == 12:
        A(d, "loader rickshaw", [("expenses:transport", 600, None), ("assets:cash", None, None)])
    if i == 14:
        A(d, "Bilal salary (advance adjusted)", [("expenses:salaries", 30000, None), ("assets:staff:advance:bilal", -5000, None), ("assets:cash", None, None)])
led.check()
if readme:
    (out / "README.md").write_text(readme, encoding="utf-8")
print("sample-vault regenerated:", led.next_entry_number() - 1, "entries")
