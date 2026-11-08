
import os

from dotenv import load_dotenv
from supabase import create_client, Client

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY",
    os.getenv("SUPABASE_ANON_KEY"),
)

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_SECRET_KEY in .env"
    )

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


def user_supabase(access_token: str) -> Client:
    """Create a request client whose PostgREST JWT is the logged-in user."""

    client = create_client(
        SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY or SUPABASE_SECRET_KEY,
    )
    client.postgrest.auth(access_token)
    return client
