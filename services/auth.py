from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database.supabase_client import supabase


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Verify a Supabase access token and return the authenticated user."""

    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")

    try:
        response = supabase.auth.get_user(credentials.credentials)
        user = getattr(response, "user", None)
        user_id = getattr(user, "id", None)
    except Exception as error:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired authentication token: {error}",
        )

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    return {
        "id": str(user_id),
        "email": getattr(user, "email", None),
        "_access_token": credentials.credentials,
    }
