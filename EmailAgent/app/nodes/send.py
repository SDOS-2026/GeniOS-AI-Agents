import logging
from app.mcp_client import get_mcp_client

logger = logging.getLogger(__name__)


def _validate_recipients(recipients: dict) -> str | None:
    """
    Validate recipient lists. Returns an error message string if invalid,
    or None if everything is OK.
    """
    to_list = recipients.get("to", [])
    cc_list = recipients.get("cc", [])
    bcc_list = recipients.get("bcc", [])

    if not isinstance(to_list, list) or not isinstance(cc_list, list) or not isinstance(bcc_list, list):
        return "Recipient fields must be lists"

    if not to_list:
        return "No recipients specified in 'to' field"

    overlap_to_cc = set(to_list) & set(cc_list)
    overlap_to_bcc = set(to_list) & set(bcc_list)
    overlap_cc_bcc = set(cc_list) & set(bcc_list)

    if overlap_to_cc or overlap_to_bcc or overlap_cc_bcc:
        overlaps = overlap_to_cc | overlap_to_bcc | overlap_cc_bcc
        return f"Recipient overlap detected: {', '.join(overlaps)}"

    return None


async def send_node(state):
    """
    Executes the email send action via the MCP Server.
    Returns a partial state update (never the full state).
    """
    logger.info("[SendNode] Preparing to send email...")

    recipients = state.get("recipient") or {"to": [], "cc": [], "bcc": []}

    # Validate recipients — return error state instead of crashing
    error = _validate_recipients(recipients)
    if error:
        logger.error(f"[SendNode] Validation failed: {error}")
        return {"sent": False, "reasoning": [f"Send blocked: {error}"]}

    to_list = recipients.get("to", [])
    cc_list = recipients.get("cc", [])
    bcc_list = recipients.get("bcc", [])

    logger.info(f"[SendNode] To: {to_list}, Subject: {state.get('subject')}")

    try:
        mcp = get_mcp_client()
        result = await mcp.call_tool("gmail_send", {
            "to": ", ".join(to_list),
            "subject": state.get("subject", ""),
            "body": state.get("draft", ""),
            "cc": ", ".join(cc_list) if cc_list else None,
            "bcc": ", ".join(bcc_list) if bcc_list else None,
            "thread_id": state.get("thread_id"),
            "in_reply_to": state.get("reply_message_id"),
            "references": state.get("reply_message_id"),
        })

        # Check if MCP returned an error
        if result.is_error:
            error_text = result.content[0].text if result.content else "Unknown MCP error"
            logger.error(f"[SendNode] MCP send failed: {error_text}")
            return {"sent": False, "reasoning": [f"Send failed: {error_text}"]}

        logger.info("[SendNode] Email sent successfully.")
        return {"sent": True, "reasoning": ["Email sent."]}

    except Exception as e:
        logger.exception(f"[SendNode] Failed to send email: {e}")
        return {"sent": False, "reasoning": [f"Send failed: {e}"]}
