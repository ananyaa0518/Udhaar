
import os
import requests
import subprocess
import re
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from number_utils import (
    hindi_to_number,
    number_to_hindi,
    HINDI_NUMBERS,
    ROMAN_NUMBERS
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
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
load_dotenv() 
API_KEY = os.getenv("GNANI_API_KEY")
STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"

AUDIO_DIR = Path("generated_audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

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
class RemindRequest(BaseModel):
    name: str
    amount: int
    days: int
class ExtractRequest(BaseModel):
    transcript: str

app.mount(
    "/audio",
    StaticFiles(directory=str(AUDIO_DIR)),
    name="audio"
)
NUMBER_WORDS = (
    set(HINDI_NUMBERS.keys())
    | set(ROMAN_NUMBERS.keys())
    | {
        "सौ", "sau",
        "हजार", "hazar", "hazaar",
        "लाख", "lakh"
    }
)

CURRENCY_WORDS = {
    "रुपये", "रुपया", "रुपए", "रूपये",
    "रूपए", "रुपी", "रु", "rs"
}

DAY_WORDS = {
    "दिन", "दिनों", "day", "days", "din"
}


def tokenize_hindi(text):
    """Split text on whitespace while preserving Hindi matras."""
    punctuation = ".,!?।,:;()[]{}\"'"

    return [
        token.strip(punctuation)
        for token in text.lower().split()
        if token.strip(punctuation)
    ]


def extract_number_before(tokens, keyword_index):
    """Find and convert number words immediately before a keyword."""

    start = keyword_index - 1

    while start >= 0:
        token = tokens[start]

        if (
            token.isdigit()
            or token in NUMBER_WORDS
            or token.startswith("₹")
        ):
            start -= 1
        else:
            break

    number_tokens = tokens[start + 1:keyword_index]

    if not number_tokens:
        return None

    # Handle ₹450
    if len(number_tokens) == 1:
        token = number_tokens[0].replace("₹", "")
        if token.isdigit():
            return int(token)

    try:
        return hindi_to_number(" ".join(number_tokens))
    except (ValueError, TypeError):
        return None


def extract_ledger_details(transcript):

    tokens = tokenize_hindi(transcript)

    # 1. Extract customer name
    name = None

    for i, token in enumerate(tokens):
        if token in {"ने", "ne"} and i > 0:
            name = tokens[i - 1]
            break

    # 2. Extract amount
    amount = None

    for i, token in enumerate(tokens):
        if token in CURRENCY_WORDS:
            amount = extract_number_before(tokens, i)
            if amount is not None:
                break

        # Handle ₹450 directly
        if token.startswith("₹"):
            numeric_part = token.replace("₹", "")
            if numeric_part.isdigit():
                amount = int(numeric_part)
                break

    # 3. Extract days
    days = None

    for i, token in enumerate(tokens):
        if token in DAY_WORDS:
            days = extract_number_before(tokens, i)

            if days is not None:
                break

    return {
        "name": name,
        "amount": amount,
        "days": days,
        "missing_fields": [
            field
            for field, value in {
                "name": name,
                "amount": amount,
                "days": days
            }.items()
            if value is None
        ]
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


#extract endpoint 
@app.post("/extract")
def extract(request: ExtractRequest):

    if not request.transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="Transcript cannot be empty."
        )

    result = extract_ledger_details(request.transcript)

    return {
        "success": True,
        **result
    }

#remind
@app.post("/remind")
def generate_reminder(request: RemindRequest):

    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Gnani API key missing."
        )

    if not request.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Customer name cannot be empty."
        )

    if request.amount <= 0 or request.days < 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive and days cannot be negative."
        )

    # Convert numbers into Hindi words
    try:
        amount_words = number_to_hindi(request.amount)
        days_words = number_to_hindi(request.days)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    # Generate personalized Hindi reminder
    reminder_text = (
        f"{request.name.strip()} जी, आपका "
        f"{amount_words} रुपये का उधार "
        f"{days_words} दिन से बाकी है। "
        "कृपया सुविधा अनुसार भुगतान कर दें। धन्यवाद।"
    )

    headers = {
        "X-API-Key-ID": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": reminder_text,
        "voice": "Nalini",
        "model": "timbre-v2.5",
        "language": "hi-IN",
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 44100,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "mp3"
        }
    }

    try:
        response = requests.post(
            TTS_URL,
            headers=headers,
            json=payload,
            timeout=120
        )

        if not response.ok:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Gnani TTS error {response.status_code}: "
                    f"{response.text[:1000]}"
                )
            )

        if not response.content:
            raise HTTPException(
                status_code=502,
                detail="Gnani returned empty audio."
            )

        # Save generated audio
        filename = f"reminder_{uuid4().hex}.mp3"
        audio_path = AUDIO_DIR / filename
        audio_path.write_bytes(response.content)

        return {
            "success": True,
            "name": request.name,
            "amount": request.amount,
            "days": request.days,
            "reminder_text": reminder_text,
            "audio_url": f"/audio/{filename}"
        }

    except requests.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Gnani TTS request timed out."
        )

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to Gnani TTS: {str(error)}"
        )
