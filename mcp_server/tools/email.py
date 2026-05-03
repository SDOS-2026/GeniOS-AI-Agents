"""
Email tool handlers for the MCP server.

Provides two tools used by the EmailAgent:
  - gmail_fetch_messages: Fetch individual messages with full decoded body
  - gmail_send: Send an email via the Gmail API
"""
import base64
import json
import logging
from typing import Any, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


async def handle_gmail_fetch_messages(args: Dict[str, Any]):
    """
    Fetch Gmail messages with full body content.

    Unlike gmail_search (which returns thread metadata/snippets), this returns
    individual messages with decoded plaintext bodies — exactly what the
    EmailAgent's classify/draft/reply nodes need.

    Args:
      - query: str          Gmail search query (default: "in:inbox")
      - maxResults: int     Max messages to return (default 5)

    Returns ToolResponse with content containing a JSON list of message dicts:
      {
        "id": "msg_id",
        "thread_id": "thread_id",
        "message_id": "<rfc822-message-id>",
        "from": "sender@example.com",
        "subject": "Subject line",
        "body": "Full decoded plaintext body"
      }
    """
    from mcp_server.main import ToolResponse, ContentItem
    from mcp_server.services import get_gmail_service

    service = get_gmail_service()
    query = args.get("query", "in:inbox")
    max_results = args.get("maxResults", 5)

    try:
        # Step 1: List messages matching the query
        list_result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = list_result.get("messages", [])
        logger.info(f"[Email] Found {len(messages)} messages for query: {query}")

        if not messages:
            return ToolResponse(content=[ContentItem(text="[]")])

        # Step 2: Fetch full message data for each message
        emails = []
        for msg in messages:
            try:
                msg_data = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )

                # Extract headers
                headers = {
                    h["name"]: h["value"]
                    for h in msg_data.get("payload", {}).get("headers", [])
                }

                # Decode body
                body = _extract_body(msg_data.get("payload", {}))

                emails.append({
                    "id": msg["id"],
                    "thread_id": msg_data.get("threadId"),
                    "message_id": headers.get("Message-Id") or headers.get("Message-ID"),
                    "from": headers.get("From"),
                    "subject": headers.get("Subject"),
                    "snippet": msg_data.get("snippet", ""),
                    "body": body,
                })
            except Exception as e:
                logger.warning(f"[Email] Failed to fetch message {msg['id']}: {e}")
                continue

        logger.info(f"[Email] Returning {len(emails)} full message objects.")
        return ToolResponse(content=[ContentItem(text=json.dumps(emails))])

    except Exception as e:
        logger.exception("[Email] gmail_fetch_messages failed")
        return ToolResponse(
            content=[ContentItem(text=f"Gmail API error: {e}")],
            is_error=True,
        )


def _extract_body(payload: dict) -> str:
    """
    Extract and decode the plaintext body from a Gmail message payload.
    Handles both single-part and multipart messages.
    """
    # Single-part message
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(
            payload["body"]["data"].encode("utf-8")
        ).decode("utf-8", errors="replace")

    # Multipart message — find the text/plain part
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                part["body"]["data"].encode("utf-8")
            ).decode("utf-8", errors="replace")

    return ""


async def handle_gmail_send(args: Dict[str, Any]):
    """
    Send an email via the Gmail API.

    Args:
      - to: str             Comma-separated recipient addresses (required)
      - subject: str        Email subject
      - body: str           Email body (plaintext)
      - cc: str             Comma-separated CC addresses (optional)
      - bcc: str            Comma-separated BCC addresses (optional)
      - thread_id: str      Thread ID for replies (optional)
      - in_reply_to: str    Message-Id header for threading (optional)
      - references: str     References header for threading (optional)

    Returns ToolResponse with a success message or error.
    """
    from mcp_server.main import ToolResponse, ContentItem
    from mcp_server.services import get_gmail_service

    service = get_gmail_service()

    to = args.get("to")
    subject = args.get("subject", "")
    body = args.get("body", "")
    cc = args.get("cc")
    bcc = args.get("bcc")
    thread_id = args.get("thread_id")
    in_reply_to = args.get("in_reply_to")
    references = args.get("references")

    if not to:
        return ToolResponse(
            content=[ContentItem(text="Missing required argument: 'to'")],
            is_error=True,
        )

    try:
        # Build MIME message
        message = MIMEText(body, "plain")
        message["To"] = to
        message["Subject"] = subject or ""

        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references

        # Encode
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body_payload = {"raw": raw}

        if thread_id and (in_reply_to or references):
            body_payload["threadId"] = thread_id

        # Send
        result = (
            service.users()
            .messages()
            .send(userId="me", body=body_payload)
            .execute()
        )

        msg_id = result.get("id", "unknown")
        logger.info(f"[Email] Email sent successfully. Message ID: {msg_id}")

        return ToolResponse(
            content=[ContentItem(text=json.dumps({
                "status": "sent",
                "message_id": msg_id,
                "thread_id": result.get("threadId"),
            }))]
        )

    except Exception as e:
        logger.exception("[Email] gmail_send failed")
        return ToolResponse(
            content=[ContentItem(text=f"Gmail send error: {e}")],
            is_error=True,
        )
