# app/connectors/gmail/client.py

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def get_gmail_service(creds: Credentials):
    """
    Returns an authenticated Gmail service client.
    Assumes OAuth is already handled upstream.
    """
    return build("gmail", "v1", credentials=creds)
