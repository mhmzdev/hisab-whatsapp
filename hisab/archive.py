"""Build the export-ledger ZIP: the canonical markdown ledger only. Everything else (secrets, worker
state, message history, downloaded media) lives outside the ledger directory and is never touched here.
"""
import re
import zipfile
from pathlib import Path

INCLUDE_RE = re.compile(r"^include\s+(\S+)\s*$", re.M)


def build_export_zip(ledger, dest_path):
    """Write hisab.md, its `include`d quarter files, accounts.md, rules.md and settings.json (whichever
    exist) to a ZIP at dest_path. Raises FileNotFoundError if the ledger has no hisab.md yet."""
    if not ledger.master.exists():
        raise FileNotFoundError(f"no ledger at {ledger.dir}")
    files, seen = [ledger.master], {ledger.master.name}
    for candidate in (ledger.accounts, ledger.rules, ledger.dir / "settings.json"):
        if candidate.exists() and candidate.name not in seen:
            files.append(candidate); seen.add(candidate.name)
    ledger_dir = ledger.dir.resolve()
    for name in INCLUDE_RE.findall(ledger.master.read_text(encoding="utf-8")):
        qf = ledger.dir / name
        # `include` (e.g. `accounts.md`, a quarter file) resolves inside the ledger dir only, and only once
        if qf.exists() and qf.resolve().parent == ledger_dir and qf.name not in seen:
            files.append(qf); seen.add(qf.name)
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)
    return dest_path
