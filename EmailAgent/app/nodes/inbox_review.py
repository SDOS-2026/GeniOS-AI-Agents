def inbox_review_node(state):
    """
    Shows a list of processed emails, filtered by priority/criteria.
    Allows user to select an email to act on (Summarize/Reply).
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
        display_mode = f"Top {len(final_list)} Important"
    else:
        # Standard ANY filter (just show latest, but since we fetched recent, main list is time sorted mostly)
        # But here we sorted by priority? 
        # If ANY, maybe we should respect time?
        # Let's revert to time sort for ANY? 
        # Actually input usually implies "Check inbox" -> show recent.
        # But if we sorted by priority above, we messed up time order.
        # For ANY, let's keep original order.
        if target_priority in [None, "ANY"]:
            final_list = emails[:limit]
            display_mode = "Recent" if target_priority else "All"
        else:
             # Specific filter logic (e.g. LOW only? Not supported yet really)
             final_list = [c[0] for c in candidates][:limit]
             display_mode = f"Filter: {target_priority}"

    if not final_list:
        print(f"\nNo emails found matching criteria.")
        return {**state, "user_action": "DONE"}

    # 2. Display List
    print(f"\n=== INBOX ({len(final_list)}) - {display_mode} ===")
    for i, email in enumerate(final_list):
        prio = email.get("classification", {}).get("priority", "MED")
        subject = email.get("subject", "No Subject")
        sender = email.get("from", "Unknown")
        print(f"[{i+1}] [{prio}] {sender}: {subject}")
    
    print("-" * 30)

    # 3. Interaction Loop
    while True:
        choice = input("\nSelect Email # (or [E]xit): ").strip().lower()
        
        if choice in ["e", "exit", "done"]:
            state["user_action"] = "DONE"
            break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(final_list):
                selected_email = final_list[idx]
                
                # Load selected email into main context for other nodes
                state["raw_thread"] = selected_email
                state["summary"]= selected_email
                state["reply_message_id"] = selected_email.get("message_id")
                state["thread_id"] = selected_email.get("thread_id")
                from_addr = selected_email.get("from")

                if from_addr:
                    state["recipient"] = {
                        "to": [from_addr],
                        "cc": [],
                        "bcc": []
                    }
                # Also copy classification if available
                if "classification" in selected_email:
                    state["classification"] = selected_email["classification"]

                action = input(f"Selected #{idx+1}. Action? [S]ummarize / [R]eply / [B]ack: ").strip().lower()
                
                if action in ["s", "summarize"]:
                    state["user_action"] = "SUMMARIZE"
                    break
                elif action in ["r", "reply"]:
                    state["user_action"] = "REPLY"
                    break
                elif action in ["b", "back"]:
                    continue
                else:
                    print("Invalid action.")
            else:
                print("Invalid selection number.")
        except ValueError:
            print("Please enter a valid number or 'exit'.")

    return state
