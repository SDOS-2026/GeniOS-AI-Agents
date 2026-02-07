# app/utils/google_creds.py

import os
from google.oauth2.credentials import Credentials


def load_google_credentials() -> Credentials:
    """
    Loads Google OAuth credentials from environment variables.
    Uses refresh token to obtain access tokens automatically.
    """

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    token_uri = os.getenv(
        "GOOGLE_TOKEN_URI",
        "https://oauth2.googleapis.com/token"
    )

    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError(
            "Missing Google OAuth environment variables. "
            "Check .env configuration."
        )

    return Credentials(
        None,  # access token fetched automatically
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        ],
    )
