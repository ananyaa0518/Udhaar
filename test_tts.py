
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GNANI_API_KEY")
URL = "https://api.vachana.ai/api/v1/tts/inference"

if not API_KEY:
    raise ValueError("GNANI_API_KEY missing. Check your .env file.")

# Hindi reminder
text = (
    "रमेश जी, आपका चार सौ पचास रुपये का बिल "
    "पांच दिन से लंबित है। कृपया जल्दी भुगतान कर दीजिए।"
)

headers = {
    "X-API-Key-ID": API_KEY,
    "Content-Type": "application/json"
}

payload = {
    "text": text,
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

print("Generating Hindi reminder...")

response = requests.post(
    URL,
    headers=headers,
    json=payload,
    timeout=120
)

print("Status:", response.status_code)
response.raise_for_status()

# Save generated audio
with open("reminder.mp3", "wb") as f:
    f.write(response.content)

print("Success! Audio saved as reminder.mp3")
