"""
Google OAuth2 credential management for the MCP server.

Handles:
  - Loading client secrets from credentials.json
  - OAuth2 authorization flow (browser-based consent)
  - Token persistence and automatic refresh
"""
import os
import logging
from pathlib import Path
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Scopes required for Gmail (read-only) and Calendar (read-only)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# Default paths (can be overridden via env vars)
CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "credentials.json"),
)
TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    os.path.join(os.path.dirname(__file__), "token.json"),
)


def get_credentials() -> Credentials:
    """
    Load or create Google OAuth2 credentials.

    Flow:
    1. If token.json exists and is valid → use it
    2. If token.json exists but expired → refresh it
    3. If no token.json → run the OAuth consent flow in the browser
    """
    creds = None

    token_file = Path(TOKEN_PATH)
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        logger.info("[Auth] Loaded existing token.")

    # Refresh or re-authorize if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("[Auth] Token expired — refreshing...")
            try:
                creds.refresh(GoogleAuthRequest())
                logger.info("[Auth] Token refreshed successfully.")
            except Exception as e:
                logger.warning(f"[Auth] Refresh failed ({e}), re-authorizing...")
                creds = _run_auth_flow()
        else:
            logger.info("[Auth] No valid token — starting OAuth flow...")
            creds = _run_auth_flow()

        # Persist the token for future runs
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        logger.info(f"[Auth] Token saved to {TOKEN_PATH}")

    return creds


def _run_auth_flow() -> Credentials:
    """
    Run the OAuth2 installed app flow.
    Opens the browser for the user to grant consent.
    """
    cred_file = Path(CREDENTIALS_PATH)
    if not cred_file.exists():
        raise FileNotFoundError(
            f"Cannot start OAuth flow: credentials.json not found at {cred_file.resolve()}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES)
    creds = flow.run_local_server(port=0)
    return creds
