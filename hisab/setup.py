"""Setup as a conversation: eight numbered questions (n/8), then the ledger files exist. State lives in the store."""
import json
import re
from pathlib import Path
from .i18n import q, s, detect_lang, norm_lang

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

PERSONAL = ["mode", "holder", "currency", "money", "cards", "income", "investments", "donations"]
SHOP = ["mode", "holder", "currency", "money", "suppliers", "staff", "income_shop", "fixed"]


def slug(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip().replace(" ", " ")


def _split(s):
    return [x.strip() for x in re.split(r"[,،]|\band\b|\baur\b", s) if x.strip()]


def _numbered(text, step, total):
    """Every onboarding message opens with n/total, Latin digits in both languages; a rejected answer repeats its number."""
    return f"{step + 1}/{total} · {text}"


def _none(x):
    return x.strip().lower() in ("none", "no", "nahi", "nahin", "skip", "-", "n", "نہیں", "نہی", "koi nahi", "koi nahin")


class Setup:
    def __init__(self, ledger, store, hosted=False):
        self.ledger = ledger
        self.store = store
        self.hosted = hosted  # hosted mode: the ledger folder is vault/<uid>, never shown to the user (#28)

    def active(self):
        return self.store.setup_state() is not None

    def start(self, parked=None):
        state = {"step": 0, "answers": {}, "parked": parked, "flow": PERSONAL}
        self.store.set_setup_state(state)
        return _numbered(s("greeting", "en"), 0, len(PERSONAL))

    def lang(self):
        st = self.store.setup_state()
        return norm_lang((st or {}).get("answers", {}).get("language", "en"))

    def set_lang(self, lg):
        """/lang during setup: the rest of the questions follow it, and no detection note is added."""
        st = self.store.setup_state()
        st["answers"]["language"] = lg
        self.store.set_setup_state(st)

    def answer(self, text):
        """Feed one answer. Returns (reply, done, parked_message)."""
        st = self.store.setup_state()
        if "language" in st["flow"]:  # a setup started before the language question was dropped
            st["flow"] = [k for k in st["flow"] if k != "language"]
            st["step"] = max(0, st["step"] - 1)
        key = st["flow"][st["step"]]
        t = text.strip()
        # no language question: the first answer (to the bilingual greeting) decides, unless /lang already did
        detected = "language" not in st["answers"]
        lang = detect_lang(t) if detected else norm_lang(st["answers"]["language"])
        note = ""
        step, total = st["step"], len(st["flow"])
        if key == "mode":
            if re.search(r"shop|dukan|dukaan|store|business|kiryana|karyana|دکان|دوکان", t, re.I):
                mode = "shop"
            elif re.search(r"personal|apna|mera|myself|me\b|home|ghar|ذاتی|زاتی|اپنا", t, re.I):
                mode = "personal"
            else:
                return _numbered(q("mode_again", lang), step, total), False, None
            st["answers"]["mode"] = mode
            if detected:
                st["answers"]["language"] = lang
                note = "\n" + s("lang_note", lang)
            st["flow"] = SHOP if mode == "shop" else PERSONAL
        elif key == "holder":
            name = " ".join(t.split())
            if _none(name):
                st["answers"]["holder"] = ""  # skipped: the prompt's direction ladder falls through to asking
            elif not (2 <= len(name) <= 60) or re.search(r"\d", name):  # a digit is an account number pasted where a name was asked
                return _numbered(q("holder_again", lang), step, total), False, None
            else:
                st["answers"]["holder"] = name
        elif key == "currency":
            cur = re.sub(r"[^A-Za-z]", "", t).upper()
            if not (3 <= len(cur) <= 4):
                return _numbered(q("currency_again", lang), step, total), False, None
            st["answers"]["currency"] = cur
        else:
            st["answers"][key] = t
        st["step"] += 1
        if st["step"] >= len(st["flow"]):
            self.write(st["answers"])
            parked = st.get("parked")
            self.store.set_setup_state(None)
            done = q("done_hosted", lang) if self.hosted else q("done", lang, dir=self.ledger.dir.name)
            return (done + (q("done_parked", lang) if parked else ""), True, parked)
        self.store.set_setup_state(st)
        return _numbered(q(st["flow"][st["step"]], lang), st["step"], len(st["flow"])) + note, False, None

    # ---------- file generation ----------
    def write(self, a):
        mode = a.get("mode", "personal")
        cur = a.get("currency", "PKR")
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
                rules_txt.append(f"~ monthly from {self.ledger.today().strftime('%Y-%m')}  {what}  ; budget:\n    {acct:<40}{cur} {float(amt):,.2f}\n    {first}\n")
            text += "\n".join(rules_txt)
        (d / "accounts.md").write_text(text, encoding="utf-8")
        (d / "rules.md").write_text(rules_src.read_text(encoding="utf-8"), encoding="utf-8")
        (d / "hisab.md").write_text(f"# Hisab — master file\n\ncommodity {cur} 1,000.00\ncommodity USD 1,000.00\n\ninclude accounts.md\n", encoding="utf-8")
        self.ledger.set_settings({"language": norm_lang(a.get("language", "en")), "mode": mode, "currency": cur, "holder": a.get("holder", "")})
        self.ledger.quarter_file(self.ledger.today())
        self.ledger.check()


def money_account(text):
    t = text.strip().lower()
    if "cash" in t or t in ("nakad", "naqad"):
        return "assets:cash"
    wallets = ("easypaisa", "jazzcash", "nayapay", "sadapay", "wallet", "paypal", "wise")
    if any(w in t for w in wallets):
        return "assets:wallet:" + slug(re.sub(r"\bwallet\b", "", t))
    return "assets:bank:" + slug(re.sub(r"\b(bank|account)\b", "", t))
