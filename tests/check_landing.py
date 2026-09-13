"""Static checks on landing/: no Firebase/libsodium on the landing page, the pre-paint theme script, two-language completeness (exactly en and ur; Roman Urdu is the agent's, not the page's), verification direction, no payment collection, no WhatsApp branding, firebase.json shape, a portal string for every runner lastError code. Stdlib only, no node."""
import json
import re
import sys
from pathlib import Path

LANGS = ("en", "ur")

ROOT = Path(__file__).resolve().parent.parent

REVERSE_VERIFICATION_DENYLIST = [
    re.compile(r"we (have )?(sent|will send)", re.IGNORECASE),
    re.compile(r"code (was )?sent to (your|the) (phone|whatsapp|number)", re.IGNORECASE),
    re.compile(r"check your (phone|messages) for the code", re.IGNORECASE),
    re.compile(r"enter the code (we|hisab) sent", re.IGNORECASE),
]

PAYMENT_INPUT_RE = re.compile(r"card|cvc|cvv|iban|expiry", re.IGNORECASE)
PAYMENT_PROVIDER_RE = re.compile(r"stripe|paypal|razorpay|jazzcash|easypaisa|checkout\.", re.IGNORECASE)
WHATSAPP_ASSET_RE = re.compile(r"^whatsapp.*\.(svg|png|jpg|webp)$", re.IGNORECASE)
LANDING_FORBIDDEN_IMPORT_RE = re.compile(r"firebase|libsodium|^\.{1,2}/portal/|^@/app/portal/")
WHATSAPP_NAME_RE = re.compile(r"Hisab for WhatsApp|WhatsApp Hisab|Hisab WhatsApp", re.IGNORECASE)


def run(root):
    failures = []
    landing = root / "landing"
    strings_path = landing / "content" / "strings.json"

    strings = None
    if strings_path.exists():
        try:
            strings = json.loads(strings_path.read_text())
        except json.JSONDecodeError as e:
            failures.append(f"strings.json: invalid JSON ({e})")

    if strings is not None:
        for key, value in strings.items():
            if not isinstance(value, dict):
                failures.append(f"strings.json[{key}]: not an object")
                continue
            for lang in LANGS:
                v = value.get(lang)
                if not isinstance(v, str) or not v.strip():
                    failures.append(f"strings.json[{key}][{lang}]: missing or empty")
            for lang in value:
                if lang not in LANGS:
                    failures.append(f"strings.json[{key}]: unexpected language {lang!r}")

        verify_keys = [k for k in strings if "verify_instruction" in k]
        if not verify_keys:
            failures.append("strings.json: no *verify_instruction* key — the portal must tell the user to SEND verify <nonce> to the agent")

        for key, value in strings.items():
            if "verify_instruction" not in key or not isinstance(value, dict):
                continue
            for lang in LANGS:
                v = value.get(lang, "")
                if not isinstance(v, str):
                    continue
                if "verify" not in v or "{nonce}" not in v:
                    failures.append(f"strings.json[{key}][{lang}]: missing 'verify' or '{{nonce}}'")

        blob = json.dumps(strings, ensure_ascii=False)
        for pattern in REVERSE_VERIFICATION_DENYLIST:
            if pattern.search(blob):
                failures.append(f"strings.json: reverse-verification phrasing matched /{pattern.pattern}/")

        for lang in LANGS:
            brand = strings.get("brand", {}).get(lang)
            if brand is not None and WHATSAPP_NAME_RE.search(brand):
                failures.append(f"strings.json[brand][{lang}]: contains a disallowed product name")

        for key, value in strings.items():
            if not isinstance(value, dict):
                continue
            for lang in LANGS:
                v = value.get(lang, "")
                if isinstance(v, str) and WHATSAPP_NAME_RE.search(v):
                    failures.append(f"strings.json[{key}][{lang}]: contains a disallowed product name")

        brand_en = strings.get("brand", {}).get("en")
        if brand_en != "Hosted Hisab":
            failures.append(f"strings.json[brand][en]: expected 'Hosted Hisab', got {brand_en!r}")

        # every lastError code the runner can write has a portal string — the portal renders codes through t()
        errors_py = root / "runner" / "errors.py"
        if errors_py.exists():
            sys.path.insert(0, str(root))
            from runner.errors import LAST_ERROR_CODES
            for code in LAST_ERROR_CODES:
                key = f"portal_error_{code}"
                if key not in strings:
                    failures.append(f"strings.json: no {key} for runner lastError code {code!r}")
    elif strings_path.exists():
        pass
    else:
        failures.append("landing/content/strings.json: not found")

    if landing.exists():
        for path in landing.rglob("*"):
            if "node_modules" in path.parts or ".next" in path.parts or "out" in path.parts:
                continue
            if path.is_file() and WHATSAPP_ASSET_RE.match(path.name):
                failures.append(f"{path.relative_to(root)}: WhatsApp-branded asset is not allowed")

        app_dir = landing / "app"
        if app_dir.exists():
            for path in app_dir.rglob("*"):
                if not path.is_file() or path.suffix not in (".jsx", ".js", ".tsx", ".ts", ".html"):
                    continue
                text = path.read_text()
                for m in re.finditer(r"<input\b[^>]*>", text, re.IGNORECASE):
                    tag = m.group(0)
                    if PAYMENT_INPUT_RE.search(tag):
                        failures.append(f"{path.relative_to(root)}: payment-looking <input> found")
                for m in re.finditer(r'(?:src|href|action)\s*=\s*[\'"]([^\'"]*)[\'"]', text, re.IGNORECASE):
                    if PAYMENT_PROVIDER_RE.search(m.group(1)):
                        failures.append(f"{path.relative_to(root)}: payment-provider reference found ({m.group(1)})")

    # the landing page answers "signed in?" from the portal's localStorage hint, never by importing the
    # portal's Firebase/libsodium code — a signed-out visitor must not download it (#23)
    landing_page = landing / "app" / "page.jsx"
    if landing_page.exists():
        for m in re.finditer(r"""(?:from|import)\s*\(?\s*['"]([^'"]+)['"]""", landing_page.read_text()):
            if LANDING_FORBIDDEN_IMPORT_RE.search(m.group(1)):
                failures.append(f"landing/app/page.jsx: imports {m.group(1)!r} — the landing page must not load Firebase or portal code")

    # the theme is applied by an inline script in <head> before first paint; without it a reload flashes the wrong theme
    layout = landing / "app" / "layout.jsx"
    if layout.exists() and not re.search(r"<head>[\s\S]*dangerouslySetInnerHTML=\{\{\s*__html:\s*THEME_SCRIPT\s*\}\}[\s\S]*</head>", layout.read_text()):
        failures.append("landing/app/layout.jsx: no pre-paint THEME_SCRIPT in <head>")

    firebase_json_path = root / "firebase.json"
    if not firebase_json_path.exists():
        failures.append("firebase.json: not found")
    else:
        try:
            fb = json.loads(firebase_json_path.read_text())
        except json.JSONDecodeError as e:
            failures.append(f"firebase.json: invalid JSON ({e})")
            fb = None
        if fb is not None:
            public = fb.get("hosting", {}).get("public")
            if public != "landing/out":
                failures.append(f"firebase.json: hosting.public expected 'landing/out', got {public!r}")
            port = fb.get("emulators", {}).get("hosting", {}).get("port")
            if port is None:
                failures.append("firebase.json: emulators.hosting.port not set")

    return failures


if __name__ == "__main__":
    failures = run(ROOT)
    for f in failures:
        print(f)
    raise SystemExit(1 if failures else 0)
