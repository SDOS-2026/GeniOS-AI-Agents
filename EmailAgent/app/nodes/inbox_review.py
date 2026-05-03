from langgraph.types import interrupt


def inbox_review_node(state):
    """
    Shows a list of processed emails, filtered by priority/criteria.
    Interrupts the graph so the frontend can display the list and
    collect the user's selection + action (Summarize / Reply / Done).
    """
    emails = state.get("emails", [])
    filters = state.get("filter_criteria", {})

    # 1. Filter Logic
    target_priority = filters.get("priority")
    limit = filters.get("limit")
    if limit is None:
        limit = len(emails)
    # Priority mapping for sorting
    prio_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NOT_REQUIRED": 0, "MED": 2}

    candidates = []

    for email in emails:
        prio_str = email.get("classification", {}).get("priority", "MEDIUM")
        # Normalize MEDIUM/MED
        if prio_str == "medium": prio_str = "MEDIUM"
        if prio_str == "high": prio_str = "HIGH"
        if prio_str == "low": prio_str = "LOW"
        if prio_str == "not_required": prio_str = "NOT_REQUIRED"

        candidates.append((email, prio_map.get(prio_str, 1)))

    # Sort by priority desc
    candidates.sort(key=lambda x: x[1], reverse=True)

    final_list = []

    if target_priority in ["HIGH", "MEDIUM"]:
        # Cascading Logic:
        # If user asked for High/Medium, we show the best ones we found,
        # filtering out junk (NOT_REQUIRED) unless we are desperate?
        # Let's filter out NOT_REQUIRED for "Important" queries
        final_list = [c[0] for c in candidates if c[1] > 0][:limit]
    else:
        # Standard ANY filter (show latest)
        if target_priority in [None, "ANY"]:
            final_list = emails[:limit]
        else:
            # Specific filter logic (e.g. LOW only? Not supported yet really)
            final_list = [c[0] for c in candidates][:limit]

    if not final_list:
        return {"user_action": "DONE"}

    # 2. Build interrupt payload for the frontend
    email_summaries = []
    for i, email in enumerate(final_list):
        prio = email.get("classification", {}).get("priority", "MEDIUM")
        email_summaries.append({
            "index": i,
            "from": email.get("from", "Unknown"),
            "subject": email.get("subject", "No Subject"),
            "priority": prio,
            "snippet": email.get("snippet", ""),
        })

    # 3. Interrupt — wait for user selection
    resume = interrupt({
        "interrupt_type": "inbox_review",
        "emails": email_summaries,
    })
    # resume = {"email_index": 2, "action": "REPLY"} | {"action": "DONE"}

    action = resume.get("action", "DONE")

    if action == "DONE":
        return {"interrupt_type": "inbox_review", "user_action": "DONE"}

    idx = resume.get("email_index", 0)
    if idx < 0 or idx >= len(final_list):
        return {"interrupt_type": "inbox_review", "user_action": "DONE"}

    selected_email = final_list[idx]

    # Load selected email into state for downstream nodes
    from_addr = selected_email.get("from")
    recipient = None
    if from_addr:
        recipient = {"to": [from_addr], "cc": [], "bcc": []}

    return {
        "interrupt_type": "inbox_review",
        "current_email_index": idx,
        "selected_email": selected_email,
        "raw_thread": selected_email,
        "summary": selected_email,
        "reply_message_id": selected_email.get("message_id"),
        "recipient": recipient,
        "user_action": action,  # "SUMMARIZE" | "REPLY" | "DONE"
    }
