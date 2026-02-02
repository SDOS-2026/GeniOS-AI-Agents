from app.gmail.send import send_email
from app.gmail.client import get_gmail_service
from app.utils.reasoning import add_reasoning

def send_node(state):
    """
    Executes the email send action.
    """
    print("\nSending email...")
    
    # Check if we have real credentials/service (simulated if not available is fine for now, 
    # but based on previous code we have get_gmail_service)
    try:
        service = get_gmail_service()
        print("Service found successfully")

        recipients = state.get("recipient") or {"to": [], "cc": [], "bcc": []}

        to_list = recipients.get("to", [])
        cc_list = recipients.get("cc", [])
        bcc_list = recipients.get("bcc", [])
        
        # 🔒 Invariants
        assert isinstance(to_list, list)
        assert isinstance(cc_list, list)
        assert isinstance(bcc_list, list)
        assert not (set(to_list) & set(cc_list) or
                    set(to_list) & set(bcc_list) or
                    set(cc_list) & set(bcc_list)), \
            "Recipient overlap between to/cc/bcc"

        to_str = ", ".join(to_list)
        cc_str = ", ".join(cc_list) if cc_list else None
        bcc_str = ", ".join(bcc_list) if bcc_list else None

        print("To:", to_str)
        print("Subject:", state.get("subject"))
        print("CC:", cc_str)
        print("BCC:", bcc_str)

        if state.get("attachments"):
            add_reasoning(state, "SUser approved the draft. Sending email with final recipients and attachments.")
        else:
            add_reasoning(state, "User approved the draft. Sending email with final recipients.")

        if state.get("show_reasoning"):
            print("\n--- REASONING ---")
        for line in state.get("reasoning", []):
            print(f"- {line}")
        print("-----------------\n")

        send_email(
            service=service,
            to=to_str,
            subject=state.get("subject"),
            body=state.get("draft"),
            approval_status="APPROVED",
            cc=cc_str,
            bcc=bcc_str,
            attachments=state.get("attachments"),
            thread_id=state.get("thread_id"),
            in_reply_to=state.get("reply_message_id"),
            references=state.get("reply_message_id"),
        )

        # print("✅ Email sent successfully.")
        add_reasoning(state, "Email sent.")

        if state.get("show_reasoning"):
            print("\n--- REASONING ---")
        for line in state.get("reasoning", []):
            print(f"- {line}")
        print("-----------------\n")

        # Optionally clear reasoning so next session starts fresh:
        state["reasoning"] = []

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        # In a real app we might want to loop back to review on failure
        
    return state
