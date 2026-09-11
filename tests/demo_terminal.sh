#!/usr/bin/env bash
# Terminal demo against a COPY of the sample kiryana ledger. Safe to re-run; the copy is rebuilt each time.
# Needs: hledger on PATH, python3 with requirements.txt, and a key in .env (GEMINI_API_KEY tonight, OPENROUTER_API_KEY at the event).
cd "$(dirname "$0")/.."
rm -rf scratch-sample scratch-sample-data && cp -R sample-vault scratch-sample
sed -e 's|path: ./vault|path: ./scratch-sample|' -e 's|path: ./data|path: ./scratch-sample-data|' -e 's|template: personal|template: shop|' config.yaml > config-sample.yaml
echo "Try:  Metro ko kitna dena hai  ·  is mahine vs pichla  ·  balances  ·  aaj ki sale 45000  ·  Metro ko 20000 diye  ·  what can I afford  ·  undo"
HISAB_CONFIG=config-sample.yaml python3 -m hisab.loop --stdin
