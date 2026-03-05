import os
import base64
import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response

app = FastAPI()

TTS_SECRET = os.getenv("TTS_SECRET", "")
GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY", "")

# Replace OpenAI defaults with Google defaults
DEFAULT_VOICE = os.getenv("TTS_DEFAULT_VOICE", "en-US-Standard-C")

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
    return {"message": "Lux Enterprise TTS (Google Cloud) is live. Use /health to check status or POST /tts to generate audio."}

@app.get("/health")
def health():
    if not GOOGLE_TTS_API_KEY:
        return {"ok": False, "error": "Missing GOOGLE_TTS_API_KEY"}
    return {"ok": True}

# Map previous system voices to Google Standard voices
VOICE_MAP = {
    # Lana (Female)
    "en-US-JennyNeural": "en-US-Standard-C",
    "en-US-AriaNeural": "en-US-Standard-E",
    
    # Andre (Male)
    "en-US-GuyNeural": "en-US-Standard-D",
    "en-US-DavisNeural": "en-US-Standard-I",
    
    # Tyrone (Deeper male)
    "en-US-BrandonNeural": "en-US-Standard-B",
    
    # Others
    "en-US-TonyNeural": "en-US-Standard-A",
    "en-US-MichelleNeural": "en-US-Standard-F"
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
    google_voice = VOICE_MAP.get(requested_voice, "en-US-Standard-C")

    # Keep it sane for voice notes
    if len(text) > 4000:
        text = text[:4000]

    if not GOOGLE_TTS_API_KEY:
        raise HTTPException(status_code=500, detail="Google TTS API Key not configured")

    try:
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"
        
        # Check if text contains SSML tags for better formatting
        is_ssml = text.startswith("<speak>") and text.endswith("</speak>")
        input_payload = {"ssml": text} if is_ssml else {"text": text}

        request_body = {
            "input": input_payload,
            "voice": {
                "languageCode": "en-US",
                "name": google_voice
            },
            "audioConfig": {
                "audioEncoding": "OGG_OPUS"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            data = response.json()

            if "audioContent" not in data:
                raise Exception("audioContent not found in Google TTS response")

            # Decode the base64 audio
            audio_data = base64.b64decode(data["audioContent"])

            return Response(
                content=audio_data,
                media_type="audio/ogg",
                headers={"Content-Disposition": "attachment; filename=voice.ogg"}
            )
    except httpx.HTTPStatusError as e:
        print(f"Google API Error: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Google TTS API Error: {e.response.status_code}")
    except Exception as e:
        print(f"TTS Process Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
