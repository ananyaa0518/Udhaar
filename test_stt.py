
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GNANI_API_KEY")
URL = "https://api.vachana.ai/stt/v3"
AUDIO_FILE = "hindi_input.mp3"

if not API_KEY:
    raise ValueError("GNANI_API_KEY missing. Check your .env file.")

if not os.path.exists(AUDIO_FILE):
    raise FileNotFoundError(f"{AUDIO_FILE} not found.")

headers = {
    "X-API-Key-ID": API_KEY
}

payload = {
    "language_code": "hi-IN",
    "preferred_language": "hi-IN",
    "format": "transcribe"
}

with open(AUDIO_FILE, "rb") as audio:
    files = {
         "audio_file": (AUDIO_FILE, audio, "audio/mpeg")
    }

    response = requests.post(
        URL,
        headers=headers,
        data=payload,
        files=files,
        timeout=60
    )

print("Status:", response.status_code)
response.raise_for_status()

result = response.json()

print("\nFull response:")
print(result)

print("\nTranscript:")
print(result.get("transcript", "No transcript returned"))
