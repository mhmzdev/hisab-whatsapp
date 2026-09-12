#!/usr/bin/env bash
# Compare a model on the fixed demo script, non-interactively, against a copy of the sample ledger.
#   bash tests/bakeoff.sh openai/gpt-4.1-mini
#   bash tests/bakeoff.sh anthropic/claude-haiku-4.5
# Uses config.yaml for everything except model.id. Prints the replies; judge shape, language handling, one-line-ness.
set -e; cd "$(dirname "$0")/.."
MODEL="${1:?model id}"
rm -rf scratch-bakeoff scratch-bakeoff-data && cp -R sample-vault scratch-bakeoff && rm -rf scratch-bakeoff/.obsidian
python3 - "$MODEL" <<'PY'
import sys, yaml
cfg = yaml.safe_load(open("config.yaml"))
cfg["model"]["id"] = sys.argv[1]
cfg["ledger"]["path"] = "./scratch-bakeoff"; cfg["state"]["path"] = "./scratch-bakeoff-data"
yaml.safe_dump(cfg, open("config-bakeoff.yaml", "w"))
PY
echo "=== $MODEL ==="
printf '%s\n' "300 ki chai easypaisa se" "Metro ko 20000 diye" "udhaar diya Sadia ko 5000" "HBL: Your A/C **1234 has been debited by PKR 1,690.00 at DIGITALOCEAN on 12-09-26" "aaj ki sale 45000" "Metro ko kitna dena hai" "is mahine vs pichla" "undo" "quit" \
 | HISAB_CONFIG=config-bakeoff.yaml python3 -m hisab.loop --stdin 2>/dev/null | sed 's/^> //' | grep -v '^Hisab, terminal mode'
