# app/connectors/gmail/fetch.py

from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.state import DAAState
from app.connectors.gmail.client import get_gmail_service


MAX_THREADS = 50


def fetch_gmail_signals(state: DAAState) -> List[Dict[str, Any]]:
    """
    Fetch raw Gmail thread metadata.
    Returns raw dicts (normalization happens later).
    """
    creds = state.raw_metadata.get("gmail_credentials")  # injected upstream
    service = get_gmail_service(creds)

    query = "in:inbox"
    if state.depth_mode == "quick":
        days = 3
    else:
        days = 7

    after_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y/%m/%d")
    query += f" after:{after_date}"

    response = service.users().threads().list(
        userId="me",
        q=query,
        maxResults=MAX_THREADS,
    ).execute()

    threads = response.get("threads", [])
    raw_threads = []

    for thread in threads:
        thread_data = service.users().threads().get(
            userId="me",
            id=thread["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()

        raw_threads.append(thread_data)

    return raw_threads
