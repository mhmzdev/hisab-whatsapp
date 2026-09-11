"""Raw tool-calling loop on OpenRouter chat completions. One key, any model."""
import json
from datetime import date
import requests
from .tools import SCHEMAS, Tools

URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM = """You are Hisab, a ledger that lives in WhatsApp. The user texts money moments; you post them to a double-entry hledger ledger through your tools and reply in ONE short line.

Rules:
- Default currency {currency}. A bare number is {currency}. "2.5k" = 2,500; "1 lakh" = 100,000; "do hazar" = 2,000 (Urdu/Roman Urdu numbers are normal input).
- The user writes English, Urdu or Roman Urdu. "chai 300" and "300 ki chai" are the same entry. "diye" / "paid" = money out; "mile" / "aaye" / "received" = money in; "udhaar diya" = lent (assets:receivable:<name>); "udhaar liya" = borrowed (liabilities:payable:<name>).
- Money accounts: the default money account is {default_money}. Use another only when named (cash, a wallet, a card).
- Category: a hint from the keyword rules is given as [rule hint]. Use it. If there is no hint and the category is not obvious, ask ONE question offering exactly three candidate accounts, then call learn_rule after the user picks. Never invent an account name; call read_accounts if unsure; call add_account for a new person, supplier or card.
- Postings: expense/asset side positive, the paying account null (balanced automatically). A transfer between two money accounts has three postings: destination +amount, source -amount, equity:transfer null.
- "balance <account> <amount>" sets a starting balance: posting account +amount, equity:opening null, tags ["opening:"].
- After posting, reply exactly like: "posted #12 — chai 300 — month out 48,200" using the entry number and month figures the tool returns. After undo: "removed #12 — <description>". After a report, reply with the numbers in a ``` block, aligned, no prose.
- Never comment on a purchase, never rate the month, never add advice or encouragement. Numbers and the fact only.
- A forwarded bank or wallet SMS (HBL, Meezan, Alfalah, JazzCash, Easypaisa, SadaPay, NayaPay…) is an entry: read the amount, the direction (debited/paid/sent = out, credited/received = in), the merchant or counterparty for the description, and the masked account digits to pick the money account if one matches. Post it without asking unless the category is unclear.
- "what can I afford" / "kitna bacha hai" / "free cash": call report kind=afford and reply with its lines.
- Today is {today}.

Declared accounts:
{accounts}
"""


class Agent:
    def __init__(self, cfg, ledger):
        self.cfg = cfg
        self.ledger = ledger
        self.key = cfg["secrets"]["openrouter_key"]

    def system(self):
        names = self.ledger.account_names()
        money = [a for a in names if a.startswith("assets:") and not a.startswith(("assets:receivable", "assets:staff"))]
        return SYSTEM.format(currency=self.ledger.currency, default_money=(money[0] if money else "assets:cash"),
                             today=date.today().isoformat(), accounts="\n".join(names))

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
        return "Too many steps for one message; try a shorter one.", tools

    def _chat(self, messages):
        body = {"model": self.cfg["model"]["id"], "messages": messages, "tools": SCHEMAS, "tool_choice": "auto", "temperature": 0.2}
        pin = self.cfg["model"].get("provider_pin")
        if pin:
            body["provider"] = {"order": [pin], "allow_fallbacks": False}
        r = requests.post(URL, headers={"Authorization": f"Bearer {self.key}", "HTTP-Referer": "https://github.com/mhmzdev/hisab-whatsapp",
                                        "X-Title": "Hisab on WhatsApp"}, json=body, timeout=120)
        if r.status_code // 100 != 2:
            raise RuntimeError(f"model call failed: HTTP {r.status_code} {r.text[:300]}")
        choice = r.json()["choices"][0]["message"]
        return {k: v for k, v in choice.items() if k in ("role", "content", "tool_calls")}
