"""The generic ledger core: hledger on markdown, append under `check --strict` with rollback, undo by entry
number, reports, category rules. No personal assumptions; the chart of accounts comes from the template + setup.
"""
import csv
import io
import json
import re
import subprocess
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from . import clock
from .i18n import norm_lang


class LedgerError(Exception):
    pass


class Ledger:
    def __init__(self, path, currency="PKR", timezone=clock.DEFAULT_TZ):
        self.dir = Path(path)
        self.tz = timezone or clock.DEFAULT_TZ
        self.master = self.dir / "hisab.md"
        self.accounts = self.dir / "accounts.md"
        self.rules = self.dir / "rules.md"
        self.currency = currency

    def today(self):
        """Today in the ledger's timezone — the only "today" an entry, a quarter file or a report period uses."""
        return clock.today(self.tz)

    # ---------- state ----------
    def exists(self):
        return self.master.exists() and self.accounts.exists()

    def hledger(self, *args, check=True):
        # --today: hledger's own "this month"/"last month" would otherwise read the container's UTC clock (#40)
        r = subprocess.run(["hledger", "-f", str(self.master), f"--today={self.today().isoformat()}", *args], capture_output=True, text=True)
        if check and r.returncode != 0:
            # cleaned like a rejected append: the error reaches the model through tools.call, and the raw banner carries the ledger's path
            raise LedgerError(_clean_err(r.stderr) if r.stderr.strip() else f"hledger failed: {' '.join(args)}")
        return r

    def check(self):
        self.hledger("check", "--strict")
        return True

    # ---------- settings (language, mode, currency) ----------
    def settings(self):
        f = self.dir / "settings.json"
        try:
            return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        except json.JSONDecodeError:
            return {}

    def set_settings(self, updates):
        cur = self.settings(); cur.update(updates)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "settings.json").write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
        return cur

    def language(self):
        return norm_lang(self.settings().get("language", "en"))

    # ---------- files ----------
    def quarter_file(self, d=None, create=True):
        d = d or self.today()
        q = (d.month - 1) // 3 + 1
        path = self.dir / f"{d.year}-Q{q}.md"
        if create and not path.exists():
            path.write_text(f"# {d.year} Q{q} — ledger\n", encoding="utf-8")
            master = self.master.read_text(encoding="utf-8")
            line = f"include {path.name}\n"
            if line not in master:
                self.master.write_text(master.rstrip("\n") + "\n" + line, encoding="utf-8")
        return path

    def _ensure_month_heading(self, path, d):
        text = path.read_text(encoding="utf-8")
        heading = f"## {d.strftime('%Y-%m')}"
        if heading not in text:
            path.write_text(text.rstrip("\n") + f"\n\n{heading}\n", encoding="utf-8")

    # ---------- entry numbers ----------
    def next_entry_number(self):
        n = 0
        for f in self.dir.glob("*.md"):
            for m in re.finditer(r"\bn:(\d+)\b", f.read_text(encoding="utf-8")):
                n = max(n, int(m.group(1)))
        return n + 1

    # ---------- write ----------
    def fmt_amount(self, amount, currency=None):
        cur = currency or self.currency
        a = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{cur} {a:,.2f}"

    def append(self, d, description, postings, tags=None):
        """postings: list of (account, amount|None, currency|None). One posting may have amount None (balanced by hledger).
        Returns (entry_number, block)."""
        d = d if isinstance(d, date) else datetime.strptime(d, "%Y-%m-%d").date()
        if d > self.today():
            raise LedgerError("future-dated entries are not accepted")
        n = self.next_entry_number()
        tag_str = f"n:{n}" + ("".join(f", {t}" for t in (tags or [])))
        lines = [f"{d.isoformat()} {description.strip()}  ; {tag_str}"]
        for acct, amt, cur in postings:
            acct = acct.strip()
            lines.append(f"    {acct:<40}{self.fmt_amount(amt, cur) if amt is not None else ''}".rstrip())
        block = "\n".join(lines)
        path = self.quarter_file(d)
        self._ensure_month_heading(path, d)
        before = path.read_text(encoding="utf-8")
        path.write_text(before.rstrip("\n") + "\n\n" + block + "\n", encoding="utf-8")
        r = self.hledger("check", "--strict", check=False)
        if r.returncode != 0:
            path.write_text(before, encoding="utf-8")
            raise LedgerError("rejected, nothing written: " + _clean_err(r.stderr))
        return n, block

    def undo(self, n=None):
        """Remove entry n (or the last one). Returns the removed block."""
        target = n or (self.next_entry_number() - 1)
        if target < 1:
            raise LedgerError("nothing to undo")
        pat = re.compile(rf"\n(\d{{4}}-\d{{2}}-\d{{2}} [^\n]*; n:{target}\b[^\n]*\n(?:[ \t]+[^\n]*\n)*)")
        for f in sorted(self.dir.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            m = pat.search(text + "\n")
            if m:
                block = m.group(1)
                new = (text + "\n").replace("\n" + block, "\n", 1)
                new = re.sub(r"\n{3,}", "\n\n", new)
                f.write_text(new.rstrip("\n") + "\n", encoding="utf-8")
                self.hledger("check", "--strict")
                return block.strip()
        raise LedgerError(f"entry #{target} not found")

    # ---------- accounts ----------
    def account_names(self):
        return re.findall(r"^account ([^;\n]+?)\s*(?:;.*)?$", self.accounts.read_text(encoding="utf-8"), re.M)

    def add_account(self, name, comment=""):
        name = name.strip()
        if name in self.account_names():
            return False
        text = self.accounts.read_text(encoding="utf-8")
        line = f"account {name}" + (f"    ; {comment}" if comment else "")
        # place under the matching top-level section if one exists, else append
        top = name.split(":")[0]
        m = re.search(rf"^## .*\b{re.escape(top)}\b.*$", text, re.M | re.I)
        if m:
            nxt = re.search(r"^## ", text[m.end():], re.M)
            ins = m.end() + (nxt.start() if nxt else len(text[m.end():]))
            text = text[:ins].rstrip("\n") + "\n" + line + "\n\n" + text[ins:].lstrip("\n")
        else:
            text = text.rstrip("\n") + "\n\n" + line + "\n"
        self.accounts.write_text(text, encoding="utf-8")
        self.hledger("check", "--strict")
        return True

    # ---------- rules ----------
    def match_rule(self, text):
        if not self.rules.exists():
            return None
        t = " " + re.sub(r"\s+", " ", text.lower()) + " "
        rules = []
        for line in self.rules.read_text(encoding="utf-8").splitlines():
            if "=>" not in line or line.lstrip().startswith("#"):
                continue
            keys, acct = line.split("=>", 1)
            for k in keys.split(","):
                k = k.strip().lower()
                if k:
                    rules.append((k, acct.strip()))
        rules.sort(key=lambda kv: -len(kv[0]))
        for k, acct in rules:
            if f" {k} " in t or re.search(rf"\b{re.escape(k)}\b", t):
                return acct
        return None

    def learn_rule(self, keywords, account):
        account = account.strip()
        if account not in self.account_names():
            raise LedgerError(f"unknown account {account}")
        kws = ", ".join(k.strip().lower() for k in keywords if k.strip())
        with self.rules.open("a", encoding="utf-8") as f:
            f.write(f"{kws} => {account}\n")
        return kws

    # ---------- periodic rules ----------
    def periodic_rules(self):
        """`~ …` rules in accounts.md as dicts: desc, account, amount (Decimal), from."""
        lines = self.accounts.read_text(encoding="utf-8").splitlines()
        rules, i = [], 0
        while i < len(lines):
            line = lines[i]
            if not line.startswith("~ "):
                i += 1; continue
            head = line[2:].split(";")[0]
            parts = re.split(r"\s{2,}", head.strip(), maxsplit=1)
            desc = parts[1].strip() if len(parts) > 1 else ""
            postings, j = [], i + 1
            while j < len(lines) and lines[j][:1] in (" ", "\t") and lines[j].strip():
                p = lines[j].strip().split(";")[0].rstrip()
                if p:
                    ap = re.split(r"\s{2,}", p, maxsplit=1)
                    postings.append((ap[0], ap[1].strip() if len(ap) > 1 else ""))
                j += 1
            if len(postings) >= 2:
                rules.append({"desc": desc, "account": postings[0][0], "amount": _num(postings[0][1]), "from": postings[1][0]})
            i = j
        return rules

    def afford(self, ym=None):
        """Liquid money − cards owed − this month's periodic items whose account has no posting yet this month."""
        ym = ym or self.today().strftime("%Y-%m")
        liquid = {k: v for k, v in self._bal("assets").items()
                  if not k.startswith(("assets:receivable", "assets:staff", "assets:investments", "assets:plots"))}
        liquid_total = sum(liquid.values(), Decimal(0))
        cards = -sum(self._bal("liabilities:card").values(), Decimal(0))
        cards = cards if cards > 0 else Decimal(0)
        pending = []
        for r in self.periodic_rules():
            if self._total(f"^{re.escape(r['account'])}$", "not:tag:opening", period=ym) == 0:
                pending.append((r["desc"], r["amount"]))
        pending_total = sum(v for _, v in pending)
        return {"month": ym, "liquid": {k: fmt(v) for k, v in liquid.items()}, "liquid_total": fmt(liquid_total),
                "cards_owed": fmt(cards), "not_yet_paid_this_month": [(d, fmt(v)) for d, v in pending],
                "pending_total": fmt(pending_total), "can_afford": fmt(liquid_total - cards - pending_total)}

    # ---------- reports ----------
    def _bal(self, *query, period=None, depth=None):
        args = ["balance", "-N", "--flat", "-O", "csv", "-X", self.currency, "--infer-market-prices"]
        if period:
            args += ["-p", period]
        if depth:
            args += ["--depth", str(depth)]
        out = self.hledger(*args, *query).stdout
        res = {}
        for row in csv.reader(io.StringIO(out)):
            if len(row) < 2 or row[0] in ("account", "total", "Total:"):
                continue
            res[row[0]] = _num(row[1])
        return res

    def _total(self, *q, **kw):
        return sum(self._bal(*q, **kw).values(), Decimal(0))

    def month_summary(self, ym=None):
        ym = ym or self.today().strftime("%Y-%m")
        income = -self._total("income", "not:tag:opening", period=ym)
        expenses = self._total("expenses", "not:tag:opening", period=ym)
        cats = sorted(self._bal("expenses", "not:tag:opening", period=ym, depth=2).items(), key=lambda kv: -kv[1])[:3]
        entries = self.hledger("print", "-p", ym, "not:tag:opening", check=False).stdout
        n = len(re.findall(r"^\d{4}-\d{2}-\d{2}", entries, re.M))
        return {"month": ym, "in": fmt(income), "out": fmt(expenses), "saved": fmt(income - expenses),
                "top": [(k.replace("expenses:", ""), fmt(v)) for k, v in cats], "entries": n}

    def report(self, kind, arg=None, period=None):
        kind = (kind or "").lower()
        if kind == "month":
            return self.month_summary(period)
        if kind == "week":
            return {"this_week": fmt(self._total("expenses", "not:tag:opening", period="this week")),
                    "last_week": fmt(self._total("expenses", "not:tag:opening", period="last week"))}
        if kind == "balances":
            return {k: fmt(v) for k, v in self._bal("assets", "liabilities").items()}
        if kind == "owed":
            rec = {k: fmt(v) for k, v in self._bal("assets:receivable").items() if v}
            pay = {k: fmt(-v) for k, v in self._bal("liabilities").items() if v}
            return {"owed_to_me": rec, "i_owe": pay}
        if kind == "category":
            if not arg:
                raise LedgerError("category report needs an account")
            q = arg if ":" in arg else f"expenses:{arg}"
            months = {}
            for m in ("this month", "last month"):
                months[m] = fmt(self._total(q, "not:tag:opening", period=m))
            reg = self.hledger("register", q, "-p", "this month", "not:tag:opening", check=False).stdout
            return {"account": q, **months, "this_month_entries": [l.strip() for l in reg.splitlines()[-8:]]}
        if kind == "register":
            reg = self.hledger("register", "-p", period or "this month", "not:tag:opening", *( [arg] if arg else []), check=False).stdout
            return {"lines": [l.rstrip() for l in reg.splitlines()[-25:]]}
        if kind == "afford":
            return self.afford(period)
        raise LedgerError(f"unknown report {kind}; use month, week, balances, owed, category, register, afford")


def _num(s):
    s = re.sub(r"[^0-9.\-]", "", (s or "").split(",  ")[0])
    try:
        return Decimal(s) if s not in ("", "-", ".") else Decimal(0)
    except Exception:
        return Decimal(0)


def fmt(n):
    n = Decimal(n).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{n:,.0f}"


def _clean_err(stderr):
    """hledger's strict-check stderr -> one short sentence the user and the model can act on. Drops the
    `hledger: Error: <path>:<line>:` banner (the path is the operator's filesystem), the "Strict ... checking
    is enabled, and" preamble and the "Consider adding ..." advice; keeps the reason and the line it points at."""
    lines = stderr.strip().splitlines()
    excerpt, prose = [], []
    for l in lines:
        if l.startswith("hledger: Error:") or l.startswith("hledger:"):
            continue
        (excerpt if re.match(r"\s*\d*\s*\|", l) else prose).append(l)
    pointed = None
    for i, l in enumerate(excerpt):
        if re.match(r"\s*\|\s*\^+\s*$", l) and i > 0:
            pointed = excerpt[i - 1]
            break
    text = " ".join(p.strip() for p in prose if p.strip())
    text = re.sub(r"^Strict \w+ checking is enabled, and\s*", "", text)
    text = text.split("Consider adding")[0].strip()
    if pointed:
        pointed = " ".join(pointed.split("|", 1)[1].split())
        text = f"{text} ({pointed})" if text else pointed
    if not text:
        text = next((l.strip() for l in reversed(lines) if l.strip() and not l.startswith("hledger:")), "hledger check failed")
    return text[:200]
