
import os
import requests
import subprocess
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------

app = FastAPI(title="Udhaar Voice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GNANI_API_KEY")
STT_URL = "https://api.vachana.ai/stt/v3"

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "video/webm",
}


# --------------------------------------------------
# Health checks
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Udhaar Voice API is running!",
        "status": "healthy",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# Speech-to-Text
# --------------------------------------------------


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):

    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Gnani API key missing."
        )

    # Normalize browser MIME type
    content_type = (
        (audio.content_type or "")
        .split(";")[0]
        .strip()
        .lower()
    )

    allowed_types = {
        "audio/webm",
        "audio/mp4",
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
        "video/webm",
    }

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type: {audio.content_type}"
        )

    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty audio file."
        )

    # Check FFmpeg installation
    try:
        ffmpeg_check = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not installed. Run: brew install ffmpeg"
        )

    if ffmpeg_check.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not working correctly."
        )

    # Save original recording for debugging
    original_path = UPLOAD_DIR / f"original_{uuid4().hex}.webm"
    original_path.write_bytes(audio_bytes)

    # Convert browser audio to WAV, 16 kHz, mono
    try:
        conversion = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-i", "pipe:0",
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                "-f", "wav",
                "pipe:1"
            ],
            input=audio_bytes,
            capture_output=True,
            timeout=30
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Audio conversion timed out."
        )

    if conversion.returncode != 0 or not conversion.stdout:
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not convert browser recording to WAV: "
                + conversion.stderr.decode("utf-8", errors="replace")[:500]
            )
        )

    wav_bytes = conversion.stdout

    # Save converted WAV
    wav_path = UPLOAD_DIR / f"converted_{uuid4().hex}.wav"
    wav_path.write_bytes(wav_bytes)

    # Send WAV to Gnani Prisma
    headers = {
        "X-API-Key-ID": API_KEY
    }

    payload = {
        "language_code": "hi-IN",
        "preferred_language": "hi-IN",
        "format": "transcribe"
    }

    files = {
        "audio_file": (
            "recording.wav",
            wav_bytes,
            "audio/wav"
        )
    }

    try:
        response = requests.post(
            STT_URL,
            headers=headers,
            data=payload,
            files=files,
            timeout=90
        )

        if not response.ok:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Prisma error {response.status_code}: "
                    f"{response.text[:1000]}"
                )
            )

        result = response.json()

        if not result.get("success"):
            raise HTTPException(
                status_code=502,
                detail=f"Transcription unsuccessful: {result}"
            )

        return {
            "success": True,
            "transcript": result.get("transcript", ""),
            "literal": result.get("output", {}).get("literal", ""),
            "model": result.get("model", ""),
            "processing_time": result.get("processing_time"),
            "audio_format": "wav",
            "sample_rate": 16000,
            "channels": 1
        }

    except requests.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Gnani transcription request timed out."
        )

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to Gnani: {str(error)}"
        )

    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Gnani returned an invalid JSON response."
        )

    finally:
        await audio.close()
