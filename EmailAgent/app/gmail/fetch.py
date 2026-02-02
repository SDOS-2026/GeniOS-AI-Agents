import base64

def fetch_recent_emails(service, max_results=5, query=None):
    kwargs = {
        "userId": "me",
        "maxResults": max_results
    }
    if query:
        kwargs["q"] = query

    results = service.users().messages().list(**kwargs).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full",
            metadataHeaders=["From", "Subject", "Message-Id"]
        ).execute()

        headers = {
            h["name"]: h["value"]
            for h in msg_data["payload"]["headers"]
        }
        body = ""
        payload = msg_data.get("payload", {})
        if payload.get("body", {}).get("data"):
            body = base64.urlsafe_b64decode(
                payload["body"]["data"].encode("utf-8")
            ).decode("utf-8", errors="replace")
        else:
            for part in payload.get("parts", []) or []:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(
                        part["body"]["data"].encode("utf-8")
                    ).decode("utf-8", errors="replace")
                    break

        emails.append({
            "id": msg["id"],
            "thread_id": msg_data["threadId"],
            "message_id": headers.get("Message-Id"),
            "from": headers.get("From"),
            "subject": headers.get("Subject"),
            "message_id": headers.get("Message-Id") or headers.get("Message-ID"),
            "body": body,
        })

    return emails
