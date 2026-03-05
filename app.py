import os, tempfile, subprocess, asyncio
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
import edge_tts

app = FastAPI()

TTS_SECRET = os.getenv("TTS_SECRET", "")
DEFAULT_VOICE = os.getenv("TTS_DEFAULT_VOICE", "en-US-JennyNeural")
DEFAULT_RATE  = os.getenv("TTS_DEFAULT_RATE", "+0%")
DEFAULT_PITCH = os.getenv("TTS_DEFAULT_PITCH", "+0Hz")

def _auth_ok(auth_header: str | None) -> bool:
    if not TTS_SECRET:
        return False
    if not auth_header:
        return False
    return auth_header.strip() == f"Bearer {TTS_SECRET}"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/tts")
async def tts(
    payload: dict,
    authorization: str | None = Header(default=None),
):
    if not _auth_ok(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")

    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="missing text")

    voice = (payload.get("voice") or DEFAULT_VOICE).strip()
    rate  = (payload.get("rate") or DEFAULT_RATE).strip()
    pitch = (payload.get("pitch") or DEFAULT_PITCH).strip()

    # Keep it sane for Telegram voice notes
    if len(text) > 4000:
        text = text[:4000]

    td = tempfile.mkdtemp()
    mp3_path = os.path.join(td, "out.mp3")
    ogg_path = os.path.join(td, "out.ogg")

    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(mp3_path)

        # Convert to OGG/OPUS voice-note friendly format
        subprocess.check_call([
            "ffmpeg", "-y",
            "-i", mp3_path,
            "-c:a", "libopus",
            "-b:a", "32k",
            "-vbr", "on",
            "-application", "voip",
            "-ac", "1",
            ogg_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return FileResponse(
            ogg_path,
            media_type="audio/ogg",
            filename="voice.ogg"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
