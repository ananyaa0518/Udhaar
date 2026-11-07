
import os
import re
import subprocess
from pathlib import Path
from typing import Literal
from uuid import uuid4

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from number_utils import HINDI_NUMBERS, ROMAN_NUMBERS, hindi_to_number


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GNANI_API_KEY")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"

UPLOAD_DIR = BASE_DIR / "uploads"
AUDIO_DIR = BASE_DIR / "generated_audio"

UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)


# ==================================================
# FASTAPI APP
# ==================================================

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

app.mount(
    "/audio",
    StaticFiles(directory=str(AUDIO_DIR)),
    name="audio",
)


# ==================================================
# SUPPORTED LANGUAGES AND VOICES
# Verify voice IDs against your Gnani account.
# ==================================================

VOICE_MAP = {
    "bn-IN": "Kirra",
    "en-IN": "Kaveri",
    "gu-IN": "Falak",
    "hi-IN": "Nalini",
    "kn-IN": "Saanvi",
    "ml-IN": "Reshma",
    "mr-IN": "Zahira",
    "pa-IN": "Mehuli",
    "ta-IN": "Asmita",
    "te-IN": "Suhana",
}

LANGUAGE_NAMES = {
    "bn-IN": "Bengali",
    "en-IN": "English",
    "gu-IN": "Gujarati",
    "hi-IN": "Hindi",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "pa-IN": "Punjabi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
}

SUPPORTED_LANGUAGES = tuple(VOICE_MAP.keys())


# ==================================================
# MULTILINGUAL REMINDER TEMPLATES
# ==================================================

REMINDER_TEMPLATES = {
    "bn-IN": (
        "{name}, আপনার ₹{amount} বকেয়া {days} দিন ধরে বাকি রয়েছে। "
        "অনুগ্রহ করে সুবিধামতো পেমেন্ট করে দিন। ধন্যবাদ।"
    ),

    "en-IN": (
        "Dear {name}, your outstanding balance of rupees {amount} "
        "has been pending for {days} days. Please clear it at your "
        "earliest convenience. Thank you."
    ),

    "gu-IN": (
        "{name}ભાઈ, તમારા ₹{amount} બાકી છે અને {days} દિવસથી બાકી છે. "
        "કૃપા કરીને અનુકૂળ સમયે ચુકવણી કરી આપશો. આભાર."
    ),

    "hi-IN": (
        "{name} जी, आपका ₹{amount} का उधार {days} दिन से बाकी है। "
        "कृपया सुविधा अनुसार भुगतान कर दें। धन्यवाद।"
    ),

    "kn-IN": (
        "{name}, ನಿಮ್ಮ ₹{amount} ಬಾಕಿ ಹಣ {days} ದಿನಗಳಿಂದ ಉಳಿದಿದೆ. "
        "ದಯವಿಟ್ಟು ಅನುಕೂಲವಾದಾಗ ಪಾವತಿಸಿ. ಧನ್ಯವಾದಗಳು."
    ),

    "ml-IN": (
        "{name}, നിങ്ങളുടെ ₹{amount} കുടിശ്ശിക {days} ദിവസമായി ബാക്കിയുണ്ട്. "
        "ദയവായി സൗകര്യപ്രകാരം പണമടയ്ക്കുക. നന്ദി."
    ),

    "mr-IN": (
        "{name}, तुमचे ₹{amount} बाकी असून {days} दिवस झाले आहेत. "
        "कृपया सोयीनुसार पैसे भरावेत. धन्यवाद."
    ),

    "pa-IN": (
        "{name} ਜੀ, ਤੁਹਾਡੇ ₹{amount} ਬਕਾਇਆ ਹਨ ਅਤੇ {days} ਦਿਨਾਂ ਤੋਂ ਬਾਕੀ ਹਨ। "
        "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਸਹੂਲਤ ਅਨੁਸਾਰ ਭੁਗਤਾਨ ਕਰ ਦਿਓ। ਧੰਨਵਾਦ।"
    ),

    "ta-IN": (
        "{name}, உங்களுடைய ₹{amount} நிலுவைத் தொகை {days} நாட்களாக உள்ளது. "
        "தயவுசெய்து உங்களுக்கு வசதியான நேரத்தில் பணம் செலுத்துங்கள். நன்றி."
    ),

    "te-IN": (
        "{name}, మీ ₹{amount} బకాయి {days} రోజులుగా ఉంది. "
        "దయచేసి మీకు అనుకూలమైన సమయంలో చెల్లించండి. ధన్యవాదాలు."
    ),
}


# ==================================================
# REQUEST MODELS
# ==================================================

class RemindRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: int = Field(gt=0)
    days: int = Field(ge=0)

    language: Literal[
        "bn-IN",
        "en-IN",
        "gu-IN",
        "hi-IN",
        "kn-IN",
        "ml-IN",
        "mr-IN",
        "pa-IN",
        "ta-IN",
        "te-IN",
    ] = "hi-IN"


class ExtractRequest(BaseModel):
    transcript: str = Field(min_length=1)


# ==================================================
# HINDI NUMBER EXTRACTION HELPERS
# ==================================================

NUMBER_WORDS = (
    set(HINDI_NUMBERS.keys())
    | set(ROMAN_NUMBERS.keys())
    | {
        "सौ", "sau",
        "हजार", "hazar", "hazaar",
        "लाख", "lakh",
    }
)

CURRENCY_WORDS = {
    "रुपये", "रुपया", "रुपए",
    "रूपये", "रूपए", "रुपी",
    "रु", "rs",
}

DAY_WORDS = {
    "दिन", "दिनों", "day", "days", "din",
}


def tokenize_hindi(text: str) -> list:
    """Normalize punctuation and split transcript into tokens."""

    text = text.lower()

    text = re.sub(
        r"[.,!?।,:;()\[\]{}\"']",
        " ",
        text
    )

    return text.split()


def parse_number_words(words: list):
    """Convert digit or Hindi number words into an integer."""

    if not words:
        return None

    phrase = " ".join(words).strip()

    # Handle digits
    digit_match = re.fullmatch(r"[₹\s]*([0-9,]+)", phrase)

    if digit_match:
        return int(digit_match.group(1).replace(",", ""))

    # Handle Hindi and supported Romanized number words
    try:
        result = hindi_to_number(phrase)

        if result is not None:
            return int(result)

    except (ValueError, TypeError):
        pass

    return None


def extract_number_before(tokens: list, keyword_index: int):
    """Extract a number immediately before a keyword."""

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

    return parse_number_words(number_tokens)


# ==================================================
# MAIN LEDGER EXTRACTION
# ==================================================

def extract_ledger_details(transcript: str) -> dict:

    tokens = tokenize_hindi(transcript)
    cleaned = transcript.strip()

    name = None
    amount = None
    days = None

    # ----------------------------------------------
    # 1. CUSTOMER NAME
    # ----------------------------------------------

    # Supports:
    # राम जी आपका...
    # राम ने 450 रुपये...
    # Rahul ji...
    # Rahul ne...

    for i, token in enumerate(tokens):

        if token in {"जी", "ने", "ji", "ne"} and i > 0:

            candidate = tokens[i - 1]

            if candidate not in {
                "आपका", "आपकी", "आपके",
                "मेरा", "मेरी", "मेरे",
            }:
                name = candidate
                break

    # Fallback: first word before "का उधार"
    if not name:

        for i, token in enumerate(tokens):

            if token == "उधार" and i >= 2:

                candidate = tokens[0]

                if candidate not in {
                    "आपका", "आपकी", "आपके",
                    "मेरा", "मेरी", "मेरे",
                }:
                    name = candidate

                break

    # ----------------------------------------------
    # 2. AMOUNT
    # ----------------------------------------------

    # Supports ₹450 and ₹ 450

    symbol_match = re.search(
        r"₹\s*([0-9][0-9,]*)",
        cleaned
    )

    if symbol_match:

        amount = int(
            symbol_match.group(1).replace(",", "")
        )

    # Supports:
    # 450 रुपये
    # रुपये 450
    # 450 रुपए
    # Rs 450

    if amount is None:

        currency_pattern = (
            r"(?:रुपये|रुपया|रुपए|रूपये|रूपए|रु|रुपी|rs\.?)"
            r"\s*([0-9][0-9,]*)"
            r"|"
            r"([0-9][0-9,]*)\s*"
            r"(?:रुपये|रुपया|रुपए|रूपये|रूपए|रु|रुपी|rs\.?)"
        )

        match = re.search(
            currency_pattern,
            cleaned,
            flags=re.IGNORECASE
        )

        if match:

            numeric = match.group(1) or match.group(2)

            amount = int(
                numeric.replace(",", "")
            )

    # Supports number words before currency:
    # चार सौ पचास रुपये

    if amount is None:

        for i, token in enumerate(tokens):

            if token in CURRENCY_WORDS:

                amount = extract_number_before(
                    tokens,
                    i
                )

                if amount is not None:
                    break

    # Supports:
    # 450 का उधार
    # चार सौ पचास का उधार

    if amount is None:

        for i, token in enumerate(tokens):

            if token == "उधार" and i > 0:

                amount = extract_number_before(
                    tokens,
                    i
                )

                if amount is not None:
                    break

    # ----------------------------------------------
    # 3. PENDING DAYS
    # ----------------------------------------------

    # Supports:
    # 5 दिन
    # पांच दिन
    # 5 days
    # five days (if number_utils supports it)

    for i, token in enumerate(tokens):

        if token in DAY_WORDS:

            days = extract_number_before(
                tokens,
                i
            )

            if days is not None:
                break

    # ----------------------------------------------
    # FINAL RESULT
    # ----------------------------------------------

    values = {
        "name": name,
        "amount": amount,
        "days": days,
    }

    missing_fields = [
        field
        for field, value in values.items()
        if value is None
    ]

    return {
        **values,
        "missing_fields": missing_fields,
    }


# ==================================================
# ROOT AND HEALTH ENDPOINTS
# ==================================================

@app.get("/")
def home():

    return {
        "message": "Udhaar Voice API is running!",
        "status": "healthy",
    }


@app.get("/health")
def health():

    return {
        "status": "ok"
    }


@app.get("/languages")
def get_languages():

    return [
        {
            "code": language,
            "name": LANGUAGE_NAMES[language],
            "voice": VOICE_MAP[language],
        }
        for language in SUPPORTED_LANGUAGES
    ]


# ==================================================
# SPEECH TO TEXT - PRISMA
# ==================================================

@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language_code: str = Form("hi-IN"),
):

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail="Gnani API key missing. Check your .env file."
        )

    if language_code not in SUPPORTED_LANGUAGES:

        raise HTTPException(
            status_code=422,
            detail="Unsupported language code."
        )

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
    await audio.close()

    if not audio_bytes:

        raise HTTPException(
            status_code=400,
            detail="Empty audio file."
        )

    # Save original audio
    extension_map = {
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/webm": ".webm",
        "video/webm": ".webm",
    }

    original_extension = extension_map.get(
        content_type,
        ".audio"
    )

    original_path = (
        UPLOAD_DIR /
        f"original_{uuid4().hex}{original_extension}"
    )

    original_path.write_bytes(audio_bytes)

    # Convert to WAV 16kHz mono
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
                "pipe:1",
            ],
            input=audio_bytes,
            capture_output=True,
            timeout=30,
        )

    except FileNotFoundError:

        raise HTTPException(
            status_code=500,
            detail="FFmpeg not installed. Run brew install ffmpeg."
        )

    except subprocess.TimeoutExpired:

        raise HTTPException(
            status_code=500,
            detail="Audio conversion timed out."
        )

    if conversion.returncode != 0 or not conversion.stdout:

        error_text = conversion.stderr.decode(
            "utf-8",
            errors="replace"
        )[:500]

        raise HTTPException(
            status_code=422,
            detail=f"Audio conversion failed: {error_text}"
        )

    wav_bytes = conversion.stdout

    wav_path = UPLOAD_DIR / f"converted_{uuid4().hex}.wav"
    wav_path.write_bytes(wav_bytes)

    headers = {
        "X-API-Key-ID": API_KEY
    }

    form_data = {
        "language_code": language_code,
        "preferred_language": language_code,
        "format": "transcribe",
    }

    files = {
        "audio_file": (
            "recording.wav",
            wav_bytes,
            "audio/wav",
        )
    }

    try:

        response = requests.post(
            STT_URL,
            headers=headers,
            data=form_data,
            files=files,
            timeout=90,
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
            "language_code": language_code,
            "transcript": result.get("transcript", ""),
            "literal": result.get("output", {}).get("literal", ""),
            "model": result.get("model", ""),
            "processing_time": result.get("processing_time"),
            "audio_format": "wav",
            "sample_rate": 16000,
            "channels": 1,
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
            detail="Gnani returned invalid JSON."
        )


# ==================================================
# EXTRACT CUSTOMER, AMOUNT AND DAYS
# ==================================================

@app.post("/extract")
def extract(request: ExtractRequest):

    if not request.transcript.strip():

        raise HTTPException(
            status_code=400,
            detail="Transcript cannot be empty."
        )

    result = extract_ledger_details(
        request.transcript
    )

    return {
        "success": True,
        **result,
    }


# ==================================================
# MULTILINGUAL TEXT TO SPEECH - TIMBRE
# ==================================================

@app.post("/remind")
def generate_reminder(request: RemindRequest):

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail="Gnani API key missing. Check your .env file."
        )

    name = request.name.strip()

    if not name:

        raise HTTPException(
            status_code=422,
            detail="Customer name cannot be empty."
        )

    language = request.language
    voice = VOICE_MAP[language]

    reminder_text = REMINDER_TEMPLATES[language].format(
        name=name,
        amount=request.amount,
        days=request.days,
    )

    headers = {
        "X-API-Key-ID": API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": reminder_text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": language,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 44100,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "mp3",
        },
    }

    try:

        response = requests.post(
            TTS_URL,
            headers=headers,
            json=payload,
            timeout=120,
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

        filename = f"reminder_{uuid4().hex}.mp3"

        audio_path = AUDIO_DIR / filename
        audio_path.write_bytes(response.content)

        return {
            "success": True,
            "name": name,
            "amount": request.amount,
            "days": request.days,
            "language": language,
            "language_name": LANGUAGE_NAMES[language],
            "voice": voice,
            "reminder_text": reminder_text,
            "audio_url": f"/audio/{filename}",
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
