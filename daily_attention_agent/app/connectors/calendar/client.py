# app/connectors/calendar/client.py

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def get_calendar_service(creds: Credentials):
    """
    Returns an authenticated Google Calendar service client.
    OAuth is assumed to be handled upstream.
    """
    return build("calendar", "v3", credentials=creds)
