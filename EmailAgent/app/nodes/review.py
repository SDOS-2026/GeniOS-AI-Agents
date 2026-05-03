from langgraph.types import interrupt


def review_node(state):
    """
    Presents the draft for review via an interrupt.
    The frontend renders the draft and collects the user's decision:
    Send, Edit (with instructions), or Cancel.
    """
    recipients = state["recipient"]
    subject = state.get("subject") or "No Subject"
    draft = state.get("draft", "")
    reasoning = state.get("reasoning", [])

    # Interrupt — let the frontend display the draft and collect decision
    resume = interrupt({
        "interrupt_type": "draft_review",
        "message": "I have prepared a draft for you. Please review it before I send it.",
        "draft": {
            "to": recipients.get("to", []),
            "cc": recipients.get("cc", []),
            "bcc": recipients.get("bcc", []),
            "subject": subject,
            "body": draft,
        },
        "reasoning": reasoning,
    })

    # resume = {"decision": "SEND"} | {"decision": "EDIT", "edit_instructions": "..."} | {"decision": "CANCEL"}

    decision = resume.get("decision", "CANCEL")

    if decision == "SEND":
        return {
            "interrupt_type": "draft_review",
            "user_action": "SEND",
            "approval_decision": "YES",
        }
    elif decision == "EDIT":
        return {
            "interrupt_type": "draft_review",
            "user_action": "EDIT",
            "approval_decision": "NO",
            "edit_instructions": resume.get("edit_instructions", ""),
        }
    else:  # CANCEL
        return {
            "interrupt_type": "draft_review",
            "user_action": "CANCEL",
            "approval_decision": "NO",
        }
