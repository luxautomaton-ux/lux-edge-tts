import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from openai import AsyncOpenAI

app = FastAPI()

TTS_SECRET = os.getenv("TTS_SECRET", "")
# Replace edge-tts defaults with OpenAI defaults
DEFAULT_VOICE = os.getenv("TTS_DEFAULT_VOICE", "nova")

# Initialize OpenAI client
# It will automatically use the OPENAI_API_KEY environment variable
openai_client = AsyncOpenAI()

def _auth_ok(auth_header: str | None) -> bool:
    print(f"Checking auth. Provided Header: {auth_header!r}")
    if not TTS_SECRET:
        print("TTS_SECRET is empty!")
        return False
    if not auth_header:
        print("Auth header is empty!")
        return False
    expected = f"Bearer {TTS_SECRET}"
    return auth_header.strip() == expected

@app.get("/")
def read_root():
    return {"message": "Lux Enterprise TTS is live. Use /health to check status or POST /tts to generate audio."}

@app.get("/health")
def health():
    return {"ok": True}

# Map Edge-TTS names to OpenAI voices to preserve backward compatibility for frontend
VOICE_MAP = {
    "en-US-JennyNeural": "nova",
    "en-US-AriaNeural": "nova",
    "en-US-GuyNeural": "echo",
    "en-US-DavisNeural": "onyx",
    "en-US-BrandonNeural": "echo",
    "en-US-TonyNeural": "alloy",
    "en-US-MichelleNeural": "shimmer"
}

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

    # Map the requested voice or fallback to default
    requested_voice = (payload.get("voice") or DEFAULT_VOICE).strip()
    openai_voice = VOICE_MAP.get(requested_voice, "nova")

    # Keep it sane for voice notes
    if len(text) > 4000:
        text = text[:4000]

    try:
        # Generate speech using OpenAI
        response = await openai_client.audio.speech.create(
            model="tts-1",
            voice=openai_voice,
            input=text,
            response_format="opus" # opus is native OGG and exactly what we need
        )

        audio_data = response.read()

        return Response(
            content=audio_data,
            media_type="audio/ogg",
            headers={"Content-Disposition": "attachment; filename=voice.ogg"}
        )
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
