"""Raw tool-calling loop on OpenRouter chat completions. One key, any model."""
import json
import os
import re
import time
import requests
from . import errors
from .errors import HisabError
from .tools import SCHEMAS, Tools
from .i18n import MODEL_LANG

OPENROUTER = "https://openrouter.ai/api/v1"
API_KEY_RE = re.compile(r"api[ _-]?key", re.IGNORECASE)  # a 400 that is really a bad key (Gemini: "API_KEY_INVALID")

SYSTEM = """You are Hisab, a ledger that lives in WhatsApp. The user texts money moments; you post them to a double-entry hledger ledger through your tools and reply in ONE short line.

Rules:
- Default currency {currency}. A bare number is {currency}. "2.5k" = 2,500; "1 lakh" = 100,000; "do hazar" = 2,000 (Urdu/Roman Urdu numbers are normal input).
- The user writes English, Urdu or Roman Urdu. "chai 300" and "300 ki chai" are the same entry. "diye" / "paid" = money out; "mile" / "aaye" / "received" = money in; "udhaar diya" = lent (assets:receivable:<name>); "udhaar liya" = borrowed (liabilities:payable:<name>).
- Money accounts: the default money account is {default_money}. Use another only when named (cash, a wallet, a card). A receipt photo that shows how it was paid ("Cash", a card, a wallet) uses that account; one that does not uses the default. Read the TOTAL line, not a line item.
- Category: a hint from the keyword rules is given as [rule hint]. Use it. If there is no hint and the category is not obvious, ask ONE question offering exactly three candidate accounts, then call learn_rule after the user picks. Never invent an account name; call read_accounts if unsure; call add_account for a new person, supplier or card.
- Postings: expense/asset side positive, the paying account null (balanced automatically). A transfer between two money accounts has three postings: destination +amount, source -amount, equity:transfer null.
- "balance <account> <amount>" sets a starting balance: posting account +amount, equity:opening null, tags ["opening:"].
- After posting, reply exactly like: "posted #12 — chai 300 — month out 48,200" using the entry number and month figures the tool returns. After undo: "removed #12 — <description>". After a report, reply with the numbers in a ``` block, aligned, no prose.
- Never comment on a purchase, never rate the month, never add advice or encouragement. Numbers and the fact only.
- A forwarded bank or wallet SMS (HBL, Meezan, Alfalah, JazzCash, Easypaisa, SadaPay, NayaPay…) is an entry: read the amount, the merchant or counterparty for the description, and the direction by the ladder below. Post it without asking unless the direction or the category is unclear.
{direction}
- "what can I afford" / "kitna bacha hai" / "free cash": call report kind=afford and reply with its lines.
- Today is {today}.
- Language: {language}

Declared accounts:
{accounts}
"""


# Direction for a typed message, a forwarded SMS and a receipt photo alike (#43). The holder rung is dropped, and the rest
# renumbered, when setup's name question was skipped.
DIRECTION_STEPS = [
    'What the user said wins: "Uzair ko 35000 diye" is money out whatever the image shows. A photo\'s caption counts as what the user said.',
    'The document\'s own words about the USER\'S OWN account or action: "your account was debited", "you sent", "you received", "credited to your account". A label that names a party ("Transferred To: <name>", "From Account: <name>", "Sent to: <name>", "Sent by: <name>") does not state a direction: it names a side, and the next rungs read it.',
    "The account holder name (the user is {holder}): match the whole name, never one shared word. The holder on the to / transferred to / sent to side is money IN; the holder on the from / sent by side is money OUT.",
    'Only one party is named and it is not the holder: the receipt is the user\'s own app view of their own action. "Sent to <other>" is money OUT, "Received from <other>" is money IN.',
    'If none of those settles it, ask ONE question about direction alone: "did this money leave you or arrive?". Never mix money-in and money-out accounts in one question.',
]
BOTH_SIDES = """- Both sides name the account holder: the user moved their own money. When both institutions match declared money accounts, post the three-posting transfer (destination +amount, source -amount, bare equity:transfer) with no question, and name both accounts in the reply. When the other institution is not a declared account (a different person with the same name, or an account Hisab does not know), ask ONE question: your own account, or another person?"""
DIRECTION_RULES = """- Direction known, category not: ask ONE question whose three candidates are all on that side. A transfer to a named person offers assets:receivable:<name> among the three; it is never the silent default.
- A transfer entry's reply names the account used: "posted #4 — lent to Uzair 35,000 → assets:receivable:uzair — month out 3,000". Ordinary entries do not name the account."""


def direction(holder):
    """The holder rung and the both-sides rule need a name to match; without one they cannot fire, so they are left out. The own-app-view rung needs none."""
    steps = [x for i, x in enumerate(DIRECTION_STEPS) if holder or i != 2]  # only the holder rung needs the name
    ladder = "\n".join(f"  {n}. {x.format(holder=holder)}" for n, x in enumerate(steps, 1))
    head = "- Direction, for a typed message, a forwarded SMS and a receipt photo alike, in this order:\n" + ladder
    return "\n".join([head] + ([BOTH_SIDES] if holder else []) + [DIRECTION_RULES])


class Agent:
    def __init__(self, cfg, ledger):
        self.cfg = cfg
        self.ledger = ledger
        self.base = (cfg["model"].get("base_url") or OPENROUTER).rstrip("/")
        key_env = cfg["model"].get("api_key_env") or "OPENROUTER_API_KEY"
        self.key = os.environ.get(key_env, "").strip() or cfg["secrets"]["openrouter_key"]
        if not self.key:
            # an operator's startup failure, never a chat reply; auto means neither key was found (hisab/config.py)
            need = "OPENROUTER_API_KEY or GEMINI_API_KEY" if cfg["model"].get("provider") == "auto" else key_env
            raise RuntimeError(f"no API key: set {need} in .env")

    def system(self):
        names = self.ledger.account_names()
        money = [a for a in names if a.startswith("assets:") and not a.startswith(("assets:receivable", "assets:staff"))]
        return SYSTEM.format(currency=self.ledger.currency, default_money=(money[0] if money else "assets:cash"),
                             direction=direction(self.ledger.holder), today=self.ledger.today().isoformat(), accounts="\n".join(names), language=MODEL_LANG.get(self.ledger.language(), MODEL_LANG["en"]))

    def run(self, history, user_content, hint=None, max_rounds=6):
        """history: prior turns [{role, content}]. user_content: str or multimodal list. Returns (reply, tools)."""
        tools = Tools(self.ledger)
        content = user_content
        if hint and isinstance(content, str):
            content = f"{content}\n\n[rule hint: {hint}]"
        elif hint and isinstance(content, list):
            content = content + [{"type": "text", "text": f"[rule hint: {hint}]"}]
        messages = [{"role": "system", "content": self.system()}] + history + [{"role": "user", "content": content}]
        for _ in range(max_rounds):
            msg = self._chat(messages)
            messages.append(msg)
            calls = msg.get("tool_calls") or []
            if not calls:
                return (msg.get("content") or "").strip() or "(no reply)", tools
            for c in calls:
                name = c["function"]["name"]
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tools.call(name, args)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result, ensure_ascii=False)})
        return errors.reply("too_many_steps", self.ledger.language(), self.cfg.get("hosted")), tools

    def _chat(self, messages):
        body = {"model": self.cfg["model"]["id"], "messages": messages, "tools": SCHEMAS, "tool_choice": "auto", "temperature": 0.2}
        pin = self.cfg["model"].get("provider_pin")
        if pin:
            body["provider"] = {"order": [pin], "allow_fallbacks": False}
        headers = {"Authorization": f"Bearer {self.key}", "HTTP-Referer": "https://github.com/mhmzdev/hisab-whatsapp", "X-Title": "Hisab on WhatsApp"}
        last = None
        for attempt in range(4):  # 0s, 2s, 4s, 8s — hotspot blips and 429/5xx, not a hung demo
            try:
                r = requests.post(f"{self.base}/chat/completions", headers=headers, json=body, timeout=90)
                if r.status_code // 100 == 2:
                    try:
                        choice = r.json()["choices"][0]["message"]
                        return {k: v for k, v in choice.items() if k in ("role", "content", "tool_calls")}
                    except (ValueError, KeyError, IndexError, TypeError):
                        pass  # a 2xx carrying an upstream error object instead of choices: transient, retry
                last = f"HTTP {r.status_code} {r.text[:500]}"
                if r.status_code in (401, 403) or (r.status_code == 400 and API_KEY_RE.search(r.text)):
                    # a rejected key never becomes valid on retry; Gemini says it as 400 "Please pass a valid API key"
                    raise HisabError("model_auth", last)
                if r.status_code // 100 != 2 and r.status_code not in (408, 409, 425, 429, 500, 502, 503, 504):
                    raise HisabError("model_rejected", last)
            except (requests.ConnectionError, requests.Timeout) as e:
                last = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
        raise HisabError("model_unavailable", f"after retries: {last}")
