"""Voice notes → text through OpenRouter's transcription endpoint (same key as the model)."""
import requests

URL = "https://openrouter.ai/api/v1/audio/transcriptions"


def transcribe(path, api_key, model="openai/whisper-1", language=None):
    data = {"model": model}
    if language:
        data["language"] = language
    with open(path, "rb") as f:
        r = requests.post(URL, headers={"Authorization": f"Bearer {api_key}"},
                          data=data, files={"file": (path.name, f)}, timeout=120)
    if r.status_code // 100 != 2:
        raise RuntimeError(f"transcription failed: HTTP {r.status_code} {r.text[:300]}")
    text = (r.json().get("text") or "").strip()
    if not text:
        raise RuntimeError("transcription returned no text")
    return text
