"""
Google API service builders for Gmail and Calendar.

Creates authenticated API clients using credentials from auth.py.
Services are built lazily and cached for reuse.
"""
import logging
from googleapiclient.discovery import build
from mcp_server.auth import get_credentials

logger = logging.getLogger(__name__)

_gmail_service = None
_calendar_service = None


def get_gmail_service():
    """Get or create the Gmail API service (v1)."""
    global _gmail_service
    if _gmail_service is None:
        creds = get_credentials()
        _gmail_service = build("gmail", "v1", credentials=creds)
        logger.info("[Services] Gmail API service built.")
    return _gmail_service


def get_calendar_service():
    """Get or create the Calendar API service (v3)."""
    global _calendar_service
    if _calendar_service is None:
        creds = get_credentials()
        _calendar_service = build("calendar", "v3", credentials=creds)
        logger.info("[Services] Calendar API service built.")
    return _calendar_service
