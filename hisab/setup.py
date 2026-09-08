"""Setup as a conversation: at most eight questions, then the ledger files exist. State lives in the store."""
import re
from datetime import date
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

QUESTIONS = {
    "mode": "Welcome to Hisab. Is this ledger *personal* or for a *shop*?",
    "currency": "Currency? (reply PKR, USD, …)",
    "money": "Your money accounts, comma-separated, first one is the default. e.g. *Alfalah bank, cash, Easypaisa wallet*",
    "cards": "Any credit cards? Name and statement day, e.g. *Alfalah 15*. Or *none*.",
    "income": "Where does money come in? e.g. *salary, freelance*. Or *none*.",
    "income_shop": "Besides sales, any other income? e.g. *commission*. Or *none*.",
    "investments": "Do you want to track investments? Names, e.g. *Meezan fund, plot*. Or *no*.",
    "donations": "Track donations as a category? *yes* or *no*.",
    "suppliers": "Suppliers the shop buys from, comma-separated, e.g. *Metro, Ali traders*. Or *none*.",
    "staff": "Staff names, for advances and salaries, e.g. *Bilal, Ahmed*. Or *none*.",
    "fixed": "Monthly fixed costs for the budget: rent and salaries, e.g. *rent 40000, salaries 60000*. Or *skip*.",
}
PERSONAL = ["mode", "currency", "money", "cards", "income", "investments", "donations"]
SHOP = ["mode", "currency", "money", "suppliers", "staff", "income_shop", "fixed"]


def slug(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip().replace(" ", " ")


def _split(s):
    return [x.strip() for x in re.split(r"[,،]|\band\b|\baur\b", s) if x.strip()]


def _none(s):
    return s.strip().lower() in ("none", "no", "nahi", "nahin", "skip", "-", "n")


class Setup:
    def __init__(self, ledger, store):
        self.ledger = ledger
        self.store = store

    def active(self):
        return self.store.setup_state() is not None

    def start(self, parked=None):
        state = {"step": 0, "answers": {}, "parked": parked, "flow": PERSONAL}
        self.store.set_setup_state(state)
        return QUESTIONS["mode"]

    def answer(self, text):
        """Feed one answer. Returns (reply, done, parked_message)."""
        st = self.store.setup_state()
        key = st["flow"][st["step"]]
        t = text.strip()
        if key == "mode":
            mode = "shop" if re.search(r"shop|dukan|dukaan|store|business|kiryana|karyana", t, re.I) else "personal"
            st["answers"]["mode"] = mode
            st["flow"] = SHOP if mode == "shop" else PERSONAL
        elif key == "currency":
            st["answers"]["currency"] = (re.sub(r"[^A-Za-z]", "", t).upper() or "PKR")[:4]
        else:
            st["answers"][key] = t
        st["step"] += 1
        if st["step"] >= len(st["flow"]):
            self.write(st["answers"])
            parked = st.get("parked")
            self.store.set_setup_state(None)
            return ("Setup done. The ledger is at " + self.ledger.dir.name + "/. Send an entry any time, e.g. *2500 coffee*, a voice note, or a receipt photo. *balance <account> <amount>* sets a starting balance."
                    + (" Now posting what you sent first." if parked else ""), True, parked)
        self.store.set_setup_state(st)
        return QUESTIONS[st["flow"][st["step"]]], False, None

    # ---------- file generation ----------
    def write(self, a):
        mode = a.get("mode", "personal")
        cur = a.get("currency", "PKR")
        self.ledger.currency = cur
        d = self.ledger.dir
        d.mkdir(parents=True, exist_ok=True)
        base = (TEMPLATES / f"{mode}.md").read_text(encoding="utf-8")
        money_lines, first = [], None
        for i, m in enumerate(_split(a.get("money", "cash"))):
            name = money_account(m)
            first = first or name
            money_lines.append(f"account {name}" + ("    ; DEFAULT" if i == 0 else ""))
        base = base.replace("## Assets — money accounts (setup adds yours below)\n",
                            "## Assets — money accounts (setup adds yours below)\n" + "\n".join(money_lines) + "\n")
        extra = []
        if not _none(a.get("cards", "none")):
            for c in _split(a["cards"]):
                nm = re.sub(r"\s*\d+\s*$", "", c).strip()
                day = re.search(r"(\d+)\s*$", c)
                extra.append(f"account liabilities:card:{slug(nm)}" + (f"    ; statement day {day.group(1)}" if day else ""))
        for inc in _split(a.get("income", "")) if not _none(a.get("income", "none")) else []:
            extra.append(f"account income:{slug(inc)}")
        for inc in _split(a.get("income_shop", "")) if not _none(a.get("income_shop", "none")) else []:
            extra.append(f"account income:{slug(inc)}")
        if not _none(a.get("investments", "no")):
            for inv in _split(a["investments"]):
                extra.append(f"account assets:investments:{slug(inv)}")
        if mode == "personal" and _none(a.get("donations", "yes")):
            base = base.replace("account expenses:donations\n", "")
        for s in _split(a.get("suppliers", "")) if not _none(a.get("suppliers", "none")) else []:
            extra.append(f"account liabilities:payable:{slug(s)}")
        for s in _split(a.get("staff", "")) if not _none(a.get("staff", "none")) else []:
            extra.append(f"account assets:staff:advance:{slug(s)}")
        rules_src = TEMPLATES / ("rules_shop.md" if mode == "shop" else "rules.md")
        text = base.rstrip("\n") + "\n\n## Added at setup\n" + "\n".join(extra) + "\n"
        fixed = a.get("fixed", "")
        if mode == "shop" and fixed and not _none(fixed):
            rules_txt = ["\n## Recurring — periodic rules; budget and forecast read these\n"]
            for item in _split(fixed):
                m = re.match(r"(.+?)\s+([\d,\.]+)\s*k?$", item.strip(), re.I)
                if not m:
                    continue
                what, amt = m.group(1).strip().lower(), m.group(2).replace(",", "")
                acct = "expenses:rent" if "rent" in what or "kiraya" in what else "expenses:salaries" if "salar" in what or "tankh" in what else f"expenses:{slug(what)}"
                if acct not in text:
                    text += f"account {acct}\n"
                rules_txt.append(f"~ monthly from {date.today().strftime('%Y-%m')}  {what}  ; budget:\n    {acct:<40}{cur} {float(amt):,.2f}\n    {first}\n")
            text += "\n".join(rules_txt)
        (d / "accounts.md").write_text(text, encoding="utf-8")
        (d / "rules.md").write_text(rules_src.read_text(encoding="utf-8"), encoding="utf-8")
        (d / "hisab.md").write_text(f"# Hisab — master file\n\ncommodity {cur} 1,000.00\ncommodity USD 1,000.00\n\ninclude accounts.md\n", encoding="utf-8")
        self.ledger.quarter_file(date.today())
        self.ledger.check()


def money_account(text):
    t = text.strip().lower()
    if "cash" in t or t in ("nakad", "naqad"):
        return "assets:cash"
    wallets = ("easypaisa", "jazzcash", "nayapay", "sadapay", "wallet", "paypal", "wise")
    if any(w in t for w in wallets):
        return "assets:wallet:" + slug(re.sub(r"\bwallet\b", "", t))
    return "assets:bank:" + slug(re.sub(r"\b(bank|account)\b", "", t))
