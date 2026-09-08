"""The agent's whole surface: six tools over the ledger. No shell, no file access."""
import json
from datetime import date
from .ledger import Ledger, LedgerError

SCHEMAS = [
    {"type": "function", "function": {
        "name": "append_entry",
        "description": "Post one balanced transaction to the ledger. Postings must sum to zero; leave exactly one amount null to have it balanced automatically. Expenses positive, the paying money account negative (or null). Returns the entry number and this month's running totals.",
        "parameters": {"type": "object", "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD; today unless the user said otherwise"},
            "description": {"type": "string", "description": "short, in the user's words, English"},
            "postings": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                "account": {"type": "string"}, "amount": {"type": ["number", "null"]}, "currency": {"type": ["string", "null"]}},
                "required": ["account", "amount"]}},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "optional hledger tags like 'opening:' or 'estimate:'"}},
            "required": ["date", "description", "postings"]}}},
    {"type": "function", "function": {
        "name": "undo_last",
        "description": "Remove an entry. With no number, the most recent one. Use the number when the user replied to an older message.",
        "parameters": {"type": "object", "properties": {"entry_number": {"type": ["integer", "null"]}}}}},
    {"type": "function", "function": {
        "name": "report",
        "description": "Read-only numbers. kind: month (in/out/saved/top categories), week, balances, owed (receivables and payables), category (needs arg = account), register (recent entries, arg optional filter).",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["month", "week", "balances", "owed", "category", "register"]},
            "arg": {"type": ["string", "null"]}, "period": {"type": ["string", "null"], "description": "YYYY-MM or hledger period like 'last month'"}},
            "required": ["kind"]}}},
    {"type": "function", "function": {
        "name": "learn_rule",
        "description": "Remember keyword(s) → account so the same words are never asked about again. Call after the user confirms a category.",
        "parameters": {"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}, "account": {"type": "string"}},
                       "required": ["keywords", "account"]}}},
    {"type": "function", "function": {
        "name": "read_accounts",
        "description": "List every declared account. Use before inventing a name; entries to undeclared accounts are rejected.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "add_account",
        "description": "Declare a new account (a person who owes you, a new card, a supplier). Use the existing tree: assets:receivable:<name>, liabilities:payable:<name>, assets:bank:<name>, expenses:<category>.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "comment": {"type": ["string", "null"]}}, "required": ["name"]}}},
]


class Tools:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self.last_entry = None  # entry number posted during this turn, if any

    def call(self, name, args):
        try:
            fn = getattr(self, f"t_{name}")
        except AttributeError:
            return {"error": f"unknown tool {name}"}
        try:
            return fn(**(args or {}))
        except LedgerError as e:
            return {"error": str(e)}
        except TypeError as e:
            return {"error": f"bad arguments: {e}"}

    def t_append_entry(self, date=None, description="", postings=None, tags=None):
        d = date or __import__("datetime").date.today().isoformat()
        p = [(x["account"], x.get("amount"), x.get("currency")) for x in (postings or [])]
        n, block = self.ledger.append(d, description, p, tags)
        self.last_entry = n
        return {"entry": n, "block": block, "month": self.ledger.month_summary()}

    def t_undo_last(self, entry_number=None):
        block = self.ledger.undo(entry_number)
        return {"removed": block, "month": self.ledger.month_summary()}

    def t_report(self, kind, arg=None, period=None):
        return self.ledger.report(kind, arg, period)

    def t_learn_rule(self, keywords, account):
        return {"learned": self.ledger.learn_rule(keywords, account), "account": account}

    def t_read_accounts(self):
        return {"accounts": self.ledger.account_names()}

    def t_add_account(self, name, comment=None):
        return {"added": self.ledger.add_account(name, comment or ""), "name": name.strip()}
