"""Voice notes → text. Provider "openrouter" uses the transcription endpoint (same key as the model);
provider "gemini" uses google-genai directly with the audio bytes (accepts WhatsApp's OGG as-is)."""
import os
from pathlib import Path
import requests

PROMPT = ("Transcribe this voice note exactly as spoken. Keep the language as is: English stays English, Urdu may be "
          "written in Urdu script or Roman Urdu as the speaker would type it. Numbers as digits. Output only the transcript.")


def transcribe(path, cfg):
    path = Path(path)
    tc = cfg["transcription"]
    provider = (tc.get("provider") or "openrouter").lower()
    if provider == "gemini":
        return _gemini(path, os.environ.get("GEMINI_API_KEY", ""), tc.get("gemini_model") or "gemini-2.5-flash")
    # "openrouter" and "openai" share the OpenAI-compatible /audio/transcriptions shape; base_url and key env are config
    base = (tc.get("base_url") or ("https://api.openai.com/v1" if provider == "openai" else "https://openrouter.ai/api/v1")).rstrip("/")
    key_env = tc.get("api_key_env") or ("OPENAI_API_KEY" if provider == "openai" else "OPENROUTER_API_KEY")
    key = os.environ.get(key_env, "").strip() or cfg["secrets"]["openrouter_key"]
    if not key:
        raise RuntimeError(f"{key_env} is not set")
    return _openai_compatible(path, f"{base}/audio/transcriptions", key, tc.get("model") or "whisper-1", tc.get("language"))


def _openai_compatible(path, url, api_key, model, language=None):
    data = {"model": model}
    if language:
        data["language"] = language
    with open(path, "rb") as f:
        r = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, data=data,
                          files={"file": (path.name, f)}, timeout=120)
    if r.status_code // 100 != 2:
        raise RuntimeError(f"transcription failed: HTTP {r.status_code} {r.text[:300]}")
    text = (r.json().get("text") or "").strip()
    if not text:
        raise RuntimeError("transcription returned no text")
    return text


def _gemini(path, api_key, model):
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    from google import genai
    from google.genai import types
    mime = {".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
            ".mp3": "audio/mpeg", ".amr": "audio/amr", ".wav": "audio/wav"}.get(path.suffix.lower(), "audio/ogg")
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(model=model, contents=[types.Part.from_bytes(data=path.read_bytes(), mime_type=mime), PROMPT])
    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("transcription returned no text")
    return text
