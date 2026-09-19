"""Voiceover: Microsoft neural voices via edge-tts (online), cached as mp3 under <root>/cache/tts."""
from __future__ import annotations
import asyncio, hashlib, re, threading
from . import store

# Verified English neural voices (edge-tts). g = gender, a = accent.
VOICES = [
    ("en-US-GuyNeural", "m", "US", "warm, mature narrator"), ("en-US-ChristopherNeural", "m", "US", "deep, authoritative"),
    ("en-US-EricNeural", "m", "US", "clear, confident"), ("en-US-RogerNeural", "m", "US", "older, gravelly-ish"),
    ("en-US-SteffanNeural", "m", "US", "calm, measured"), ("en-US-AndrewNeural", "m", "US", "friendly, casual"),
    ("en-US-BrianNeural", "m", "US", "relaxed, young adult"), ("en-US-JennyNeural", "f", "US", "bright, friendly"),
    ("en-US-AriaNeural", "f", "US", "expressive, crisp"), ("en-US-MichelleNeural", "f", "US", "smooth, mature"),
    ("en-US-EmmaNeural", "f", "US", "cheerful, clear"), ("en-US-AvaNeural", "f", "US", "soft, intimate"),
    ("en-US-AnaNeural", "f", "US", "child"), ("en-GB-RyanNeural", "m", "UK", "British, steady"),
    ("en-GB-ThomasNeural", "m", "UK", "British, dry"), ("en-GB-SoniaNeural", "f", "UK", "British, poised"),
    ("en-GB-LibbyNeural", "f", "UK", "British, lively"), ("en-GB-MaisieNeural", "f", "UK", "British child"),
    ("en-AU-NatashaNeural", "f", "AU", "Australian"), ("en-AU-WilliamMultilingualNeural", "m", "AU", "Australian"),
    ("en-IE-ConnorNeural", "m", "IE", "Irish"), ("en-IE-EmilyNeural", "f", "IE", "Irish"),
    ("en-IN-PrabhatNeural", "m", "IN", "Indian"), ("en-IN-NeerjaNeural", "f", "IN", "Indian"),
    ("en-ZA-LukeNeural", "m", "ZA", "South African"), ("en-ZA-LeahNeural", "f", "ZA", "South African"),
    ("en-NG-AbeoNeural", "m", "NG", "Nigerian"), ("en-NG-EzinneNeural", "f", "NG", "Nigerian"),
    ("en-KE-ChilembaNeural", "m", "KE", "Kenyan"), ("en-KE-AsiliaNeural", "f", "KE", "Kenyan"),
    ("en-SG-WayneNeural", "m", "SG", "Singaporean"), ("en-SG-LunaNeural", "f", "SG", "Singaporean"),
    ("en-CA-LiamNeural", "m", "CA", "Canadian"), ("en-CA-ClaraNeural", "f", "CA", "Canadian"),
    ("en-NZ-MitchellNeural", "m", "NZ", "New Zealand"), ("en-NZ-MollyNeural", "f", "NZ", "New Zealand"),
    ("en-HK-SamNeural", "m", "HK", "Hong Kong"), ("en-HK-YanNeural", "f", "HK", "Hong Kong"),
    ("en-PH-JamesNeural", "m", "PH", "Filipino"), ("en-PH-RosaNeural", "f", "PH", "Filipino"),
]
DEFAULT_NARRATOR = {"voice": "en-US-GuyNeural", "rate": "-4%", "pitch": "-2Hz", "fx": ""}
FX = ["", "radio", "robot", "echo", "deep"]
_lock = threading.Lock()


def norm_voice(v):
    if not v:
        return None
    if isinstance(v, str):
        v = {"voice": v}
    out = {"voice": v.get("voice") or DEFAULT_NARRATOR["voice"], "rate": v.get("rate") or "+0%",
           "pitch": v.get("pitch") or "+0Hz", "fx": v.get("fx") or ""}
    if not re.fullmatch(r"[+-]\d{1,3}%", out["rate"]):
        out["rate"] = "+0%"
    if not re.fullmatch(r"[+-]\d{1,3}Hz", out["pitch"]):
        out["pitch"] = "+0Hz"
    return out


def auto_voice(name: str, exclude=(), gender: str | None = None):
    pool = [v for v in VOICES if v[0] not in exclude and v[1] in ("m", "f") and "child" not in v[3]]
    if gender in ("m", "f"):
        pool = [v for v in pool if v[1] == gender] or pool
    h = int(hashlib.sha1((name or "?").encode()).hexdigest(), 16)
    v = pool[h % len(pool)]
    pitch = ((h >> 8) % 9) - 4
    return {"voice": v[0], "rate": "+0%", "pitch": f"{pitch:+d}Hz", "fx": ""}


def _clean(text):
    text = re.sub(r"[*_#`>\[\]]", "", text or "")
    return re.sub(r"\s+", " ", text).strip()[:3000]


def synth(text, voice="en-US-GuyNeural", rate="+0%", pitch="+0Hz"):
    """Return path to an mp3 (cached). Raises on failure."""
    import edge_tts  # installed in .venv via requirements
    text = _clean(text)
    if not text:
        raise ValueError("empty text")
    key = hashlib.sha1(f"{voice}|{rate}|{pitch}|{text}".encode()).hexdigest()
    path = store.CACHE / "tts" / f"{key}.mp3"
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")

    async def run():
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(tmp))
    with _lock:
        if not (path.exists() and path.stat().st_size > 0):
            asyncio.run(run())
            tmp.replace(path)
    return path
