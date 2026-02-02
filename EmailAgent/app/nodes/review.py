from app.utils.reasoning import add_reasoning

def review_node(state):
    """
    Interactively asks the user to review the draft.
    Returns the state with 'user_action' set to SEND, EDIT, or CANCEL.
    """
    assert isinstance(state["recipient"]["to"], list), \
        "Invariant violated: recipient.to must be a list"
    recipients = state["recipient"]
    subject = state.get("subject") or "No Subject"
    draft = state.get("draft", "")
    attachments = state.get("attachments") or []

    def join(lst):
        return ", ".join(lst) if lst else "—"

    add_reasoning(state, "Presenting the current draft for your review.")

    if state.get("show_reasoning"):
        print("\n--- REASONING ---")
    for line in state.get("reasoning", []):
        print(f"- {line}")
    print("-----------------\n")


    print("\n--- DRAFT REVIEW ---")
    print(f"To:  {join(recipients.get('to', []))}")
    print(f"CC:  {join(recipients.get('cc', []))}")
    print(f"BCC: {join(recipients.get('bcc', []))}")
    print(f"Subject: {subject}")
    if attachments:
        print("Attachments:")
        for a in attachments:
            print(f" - {a}")
    print("-" * 20)
    print(draft)
    print("-" * 20)



    while True:
        choice = input("\n[S]end / [E]dit / [C]ancel: ").strip().lower()

        if choice in ["s", "send"]:
            state["user_action"] = "SEND"
            state["approval_status"] = "APPROVED"
            break
        
        elif choice in ["e", "edit"]:
            state["user_action"] = "EDIT"
            state["approval_status"] = "REJECTED"
            instructions = input("What changes would you like? ")
            state["edit_instructions"] = instructions
            # print (state["edit_instructions"])
            break

        elif choice in ["c", "cancel"]:
            state["user_action"] = "CANCEL"
            break
            
        else:
            print("Invalid choice. Please type S, E, or C.")

    return state
