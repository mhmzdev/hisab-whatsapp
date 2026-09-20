"""Check by hand that the model reads the direction of a transfer receipt (#43). Needs a model key; never part of the repo check.

  python3 tests/check_receipts.py [--config config.yaml] [--holder "Muhammad Hamza"] [--stranger "Ayesha Khan"] [--fixtures dir]

Blurred receipt photos in tests/fixtures/receipts/ (see the README there). Each goes through Agent.run against a temp ledger whose
setup answered the holder name. The check asserts TOOL CALLS, never wording:

  r1           holder sent money to a company     an append_entry out of a money account, or a question whose candidates are all money-out
  r2           holder sent money to a person      the same, and a question offers assets:receivable:<name>
  r3           "Successfully Sent to <a name that contains a word of the holder's>", no sender named:
               the whole name must not match; "Sent to" decides money out: no income: posting, no money-in question
  r4           "Transferred To: <holder>", "From Account: <someone>": the "to" label is not a direction word, the holder is on the
               receiving side: money in, an append_entry into a declared account, or a question whose candidates are all money-in
  r1-stranger  r1 again with an unrelated holder   a question about direction, and no append_entry

A model can fail this on a bad day without anything having regressed, so it gates nothing. Run it before a release or after a prompt
change and paste the result into the PR. A missing fixture is a SKIP (exit 0); any FAIL exits 1. Writes only to a temp directory.
"""
import argparse, base64, re, sys, tempfile
from pathlib import Path
from typing import NamedTuple
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "receipts"
HOLDER = "Muhammad Hamza"  # the name the fixtures show as the sender; pass --holder when the images carry another one
STRANGER = "Ayesha Khan"  # named on none of them


class Case(NamedTuple):
    name: str
    fixture: str
    who: str            # "holder" or "stranger": which name setup is given
    want: str           # "out", "in" or "ask" (a direction question and no entry)
    receivable: bool = False  # a question must offer assets:receivable:<name>
    no_income: bool = False   # no income: posting, no money-in question


CASES = (Case("r1", "r1", "holder", "out"), Case("r2", "r2", "holder", "out", receivable=True),
         Case("r3", "r3", "holder", "out", no_income=True), Case("r4", "r4", "holder", "in"),
         Case("r1-stranger", "r1", "stranger", "ask"))
MONEY_PREFIXES = ("assets:bank:", "assets:wallet:", "assets:cash")
ACCOUNT_RE = re.compile(r"\b(?:assets|liabilities|expenses|income|equity):[A-Za-z0-9:_-]+")
# mirrors hisab/loop.py: what a receipt photo without a caption is sent as
PHOTO_PROMPT = "Receipt photo. Post it as an entry; ask one question if the amount or category is unclear."


def find_fixture(directory, name):
    for ext in (".jpg", ".jpeg", ".png"):
        p = Path(directory) / f"{name}{ext}"
        if p.exists():
            return p
    return None


def money_delta(postings):
    """Net change to the user's money accounts in one entry. A null amount is what balances the rest, as the ledger does it."""
    known = [p["amount"] for p in postings if p.get("amount") is not None]
    nulls = [p for p in postings if p.get("amount") is None]
    delta = 0.0
    for p in postings:
        if not str(p.get("account", "")).startswith(MONEY_PREFIXES):
            continue
        amt = p["amount"] if p.get("amount") is not None else (-sum(known) if len(nulls) == 1 else 0)
        delta += amt
    return delta


def question_side(reply):
    """For a reply that asks: 'out' when the candidates are expenses, 'in' when they are income, None when mixed or when it is not a question.
    equity:transfer is neither, so a question that offers it beside expenses or income is the mixed question #43 was filed about."""
    accounts = set(ACCOUNT_RE.findall(reply))
    if "?" not in reply or len(accounts) < 2 or "equity:transfer" in accounts:
        return None
    has_in, has_out = any(a.startswith("income:") for a in accounts), any(a.startswith("expenses:") for a in accounts)
    return None if has_in == has_out else "in" if has_in else "out"


def judge(case, calls, reply):
    """(passed, why) from the tool calls one turn made and its reply. case: a Case; calls: [(tool name, args, result)]."""
    attempted = [c for c in calls if c[0] == "append_entry"]
    posted = [c for c in attempted if "error" not in (c[2] or {})]
    if case.want == "ask":
        if attempted:
            return False, "posted an entry for a receipt that names neither side of the user"
        return ("?" in reply), ("asked a question, posted nothing" if "?" in reply else "no question and no entry")
    if posted:
        deltas = [money_delta(c[1].get("postings") or []) for c in posted]
        got = "in" if all(d > 0 for d in deltas) else "out" if all(d < 0 for d in deltas) else "mixed/none"
        if case.no_income and any(str(p.get("account", "")).startswith("income:") for c in posted for p in c[1].get("postings") or []):
            return False, "posted an income: posting for money that was sent"
        return got == case.want, f"posted {len(posted)} entr{'y' if len(posted) == 1 else 'ies'}, money {got} (wanted {case.want})"
    side = question_side(reply)
    if side != case.want:
        return False, "no entry, and the question is not one-sided" if "?" in reply else "no entry and no question"
    if case.receivable and "assets:receivable:" not in reply:
        return False, "asked with money-out candidates, but assets:receivable:<name> is not one of them"
    return True, f"asked with every candidate on the money-{case.want} side"


def run_case(agent, path, calls):
    b64 = base64.b64encode(path.read_bytes()).decode()
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    content = [{"type": "text", "text": PHOTO_PROMPT}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]
    calls.clear()
    reply, _ = agent.run([], content)
    return reply


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--holder", default=HOLDER)
    ap.add_argument("--stranger", default=STRANGER, help="a name on none of the receipts, for the r1-stranger case")
    ap.add_argument("--fixtures", default=str(FIXTURES))
    a = ap.parse_args(argv)
    found = {c.name: find_fixture(a.fixtures, c.fixture) for c in CASES}
    for c in CASES:
        if not found[c.name]:
            print(f"[SKIP] {c.name} — no {c.fixture}.jpg or {c.fixture}.png in {a.fixtures} (see the README there)")
    if not any(found.values()):
        print("\nSKIP — no receipt fixtures yet; nothing was run and no model was called")
        return 0

    from hisab import config as cfgmod
    from hisab.agent import Agent
    from hisab.ledger import Ledger
    from hisab.setup import Setup
    from hisab.store import Store
    from hisab.tools import Tools

    cfgmod.load_dotenv(); cfg = cfgmod.load(a.config)
    calls = []
    real_call = Tools.call

    def recording(self, name, args):  # the seam: record every tool call without touching hisab/tools.py
        result = real_call(self, name, args)
        calls.append((name, args, result))
        return result
    Tools.call = recording
    ok = True
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for case in CASES:
                if not found[case.name]:
                    continue
                led = Ledger(Path(tmp) / case.name, "PKR")  # a fresh ledger per case, so one entry never colours the next
                Setup(led, Store(Path(tmp) / f"state-{case.name}")).write(
                    {"mode": "personal", "holder": a.holder if case.who == "holder" else a.stranger, "currency": "PKR", "money": "Alfalah bank, Easypaisa wallet, cash",
                     "cards": "none", "income": "salary", "investments": "no", "donations": "yes"})
                try:
                    reply = run_case(Agent(cfg, led), found[case.name], calls)
                except Exception as e:
                    ok = False
                    print(f"[FAIL] {case.name} — the run failed: {type(e).__name__}: {str(e)[:160]}")
                    continue
                passed, why = judge(case, list(calls), reply)
                ok = ok and passed
                print(f"[{'PASS' if passed else 'FAIL'}] {case.name} — {why}\n         reply: {reply[:200]!r}")
    finally:
        Tools.call = real_call
    print("\nALL PASS" if ok else "\nSOMETHING FAILED — read the replies above before blaming the prompt; a model can have a bad day")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
