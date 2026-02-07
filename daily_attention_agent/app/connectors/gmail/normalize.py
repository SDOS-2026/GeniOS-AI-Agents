# app/connectors/gmail/normalize.py

from typing import List
from datetime import datetime
from email.utils import parsedate_to_datetime

from app.models.unified_signal import UnifiedSignal


def normalize_gmail_threads(raw_threads: List[dict]) -> List[UnifiedSignal]:
    signals: List[UnifiedSignal] = []

    for thread in raw_threads:
        messages = thread.get("messages", [])
        if not messages:
            continue

        last_msg = messages[-1]
        headers = {
            h["name"]: h["value"]
            for h in last_msg.get("payload", {}).get("headers", [])
        }

        subject = headers.get("Subject", "(no subject)")
        from_header = headers.get("From", "")
        date_header = headers.get("Date")

        try:
            timestamp = parsedate_to_datetime(date_header)
        except Exception:
            timestamp = datetime.utcnow()

        snippet = last_msg.get("snippet", "")[:200]

        requires_action = (
            "?" in subject.lower()
            or "please" in snippet.lower()
        )

        signal = UnifiedSignal(
            signal_type="EMAIL_THREAD",
            source_tool="gmail",
            record_id=thread["id"],
            owner=from_header,
            timestamp=timestamp,
            title=subject,
            snippet=snippet,
            url=f"https://mail.google.com/mail/u/0/#inbox/{thread['id']}",
            requires_action=requires_action,
            raw_metadata={
                "message_count": len(messages),
                "last_sender": from_header,
            }
        )

        signals.append(signal)

    return signals
