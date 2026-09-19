"""Validate the configured model endpoint and transcription in one run. Use it the moment a key is pasted.

  python3 tests/check_endpoint.py [--audio path.ogg] [--config config.yaml]

Checks: key present → model id exists and supports tools (OpenRouter) → one tool-call probe → one transcription
probe through wa-agent (the given audio, else a short clip synthesised with macOS `say` when available). Prints PASS/FAIL per step.
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests
from hisab import config as cfgmod
from hisab.wa import transcribe

ap = argparse.ArgumentParser(); ap.add_argument("--audio"); ap.add_argument("--config", default=None); a = ap.parse_args()
cfgmod.load_dotenv(); cfg = cfgmod.load(a.config)
base = (cfg["model"].get("base_url") or "https://openrouter.ai/api/v1").rstrip("/")
key_env = cfg["model"].get("api_key_env") or "OPENROUTER_API_KEY"
key = os.environ.get(key_env, "").strip() or cfg["secrets"]["openrouter_key"]
model = cfg["model"]["id"]
ok = True
def report(name, passed, detail=""):
    global ok; ok = ok and passed
    print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

print(f"model {model} via {cfg['model'].get('provider')} · voice via {cfg['transcription'].get('provider')}")
report(f"key in {key_env}", bool(key), "" if key else "empty — put OPENROUTER_API_KEY or GEMINI_API_KEY in .env")
if not key:
    sys.exit(1)

# 1. model exists + tools (OpenRouter only)
if "openrouter.ai" in base:
    r = requests.get(f"{base}/models", timeout=30)
    ids = {m["id"]: m for m in r.json().get("data", [])}
    m = ids.get(model)
    report(f"model {model} listed", bool(m), "" if m else "not in /models — pick another id")
    if m:
        report("model supports tools", "tools" in (m.get("supported_parameters") or []))
    kr = requests.get(f"{base}/auth/key", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    d = kr.json().get("data", {}) if kr.status_code == 200 else {}
    report("key valid", kr.status_code == 200, f"limit={d.get('limit')} usage={d.get('usage')}" if d else f"HTTP {kr.status_code}")

# 2. tool-call probe
body = {"model": model, "messages": [{"role": "system", "content": "Post ledger entries by calling the tool."}, {"role": "user", "content": "2500 coffee"}],
        "tools": [{"type": "function", "function": {"name": "append_entry", "description": "post", "parameters": {"type": "object", "properties": {"description": {"type": "string"}, "amount": {"type": "number"}}, "required": ["description", "amount"]}}}],
        "tool_choice": "auto"}
r = requests.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=60)
try:
    msg = r.json()["choices"][0]["message"]; tc = msg.get("tool_calls")
    report("tool call returned", bool(tc), tc[0]["function"]["arguments"] if tc else f"text: {str(msg.get('content'))[:80]}")
except Exception:
    report("tool call returned", False, f"HTTP {r.status_code} {r.text[:200]}")

# 3. transcription probe
audio = Path(a.audio) if a.audio else None
if not audio and sys.platform == "darwin":
    tmp = Path(tempfile.mkdtemp()); aiff = tmp / "t.aiff"; audio = tmp / "t.m4a"
    subprocess.run(["say", "-o", str(aiff), "twenty five hundred for coffee"], check=False)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(audio)], check=False, capture_output=True)
    if not audio.exists():
        audio = None
if audio and audio.exists():
    try:
        text = transcribe(audio, cfg)
        report(f"transcription ({cfg['transcription'].get('provider')})", bool(text), text[:80])
    except Exception as e:
        report(f"transcription ({cfg['transcription'].get('provider')})", False, str(e)[:200])
else:
    print("[SKIP] transcription — pass --audio <file.ogg|m4a> (a WhatsApp voice note works)")
print("\nALL PASS" if ok else "\nSOMETHING FAILED — fix before recording")
sys.exit(0 if ok else 1)
