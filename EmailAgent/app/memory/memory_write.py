from app.memory.supabase_client import supabase
from app.memory.embeddings import embed_text
from app.gmail.client import get_gmail_service
from app.gmail.utils import get_user_profile


def memory_write_node(state):
    """
    Persist a completed agent interaction as an episodic memory.
    Writes to: agent_episodes, and optionally reply_memory, compose_prompt_memory, or priority_email_memory.
    """
    print("🧠 MEMORY STATE KEYS:", state.keys())
    print("🧠 intent:", state.get("intent"))
    print("🧠 user_intent:", state.get("user_intent"))
    print("🧠 mode:", state.get("mode"))

    # If Supabase is not configured, skip memory write
    if supabase is None:
        print("ℹ️ Supabase not configured - skipping memory write")
        return state

    # --- REQUIRED FIELDS ---
    user_id = state.get("user_id", "default_user")
    
    # Fallback if still default
    if user_id == "default_user":
        try:
            service = get_gmail_service()
            user_id = get_user_profile(service) or "default_user"
        except Exception:
            pass
            
    # Intent mapping: 'mode' or derived from user_action
    intent = state.get("mode", "UNKNOWN")
    if state.get("user_action") == "REPLY":
        intent = "REPLY"

    # --- OUTCOME LOGIC ---
    if state.get("approval_status") == "APPROVED":
        outcome = "APPROVED"
    elif state.get("draft"):
        outcome = "DRAFT_CREATED"
    elif state.get("ranked_emails"):
        outcome = "EMAILS_RANKED"
    else:
        outcome = "COMPLETED"

    try:
        # 1. Write to agent_episodes (Parent Table)
        episode_data = {
            "user_id": user_id,
            "intent": intent,
            "outcome": outcome,
        }
        episode_res = supabase.from_("agent_episodes").insert(episode_data).execute()
        
        if not episode_res.data:
            print("⚠️ Failed to create episode record.")
            return state
            
        episode_id = episode_res.data[0]["id"]
        print(f"🧠 Created Episode ID: {episode_id}")

        # 2. Write to specific memory tables based on context
        
        # --- A. REPLY MEMORY ---
        # If we replied to an email, we should have the original email context and a draft.
        # Check if 'REPLY' action or if we have a draft and it's responding to a thread.
        # For simplicity, assuming 'REPLY' intent + draft presence => Reply Memory
        # OR if we have 'raw_thread' and 'draft' (implying a reply context).
        is_reply = (intent == "REPLY") or (state.get("mode") == "CHECK_INBOX" and state.get("draft"))

        if is_reply and state.get("draft"):
            original_summary = "Original email context missing"
            # Try to get summary from state, or extract from raw_thread
            if state.get("summary"): 
                original_summary = state.get("summary")
            elif state.get("raw_thread"):
                original_summary = state["raw_thread"].get("snippet", "")

            reply_body = state.get("draft")
            reply_embedding = embed_text(reply_body)
            
            reply_data = {
                "episode_id": episode_id,
                "original_email_summary": original_summary,
                "reply_summary": f"Replying to: {original_summary[:50]}...", # Placeholder if distinct summary not available
                "reply_body": reply_body,
                "reply_embedding": reply_embedding,
                "metadata": {
                    "thread_id": state.get("thread_id"),
                    "cc": state.get("cc"),
                    "bcc": state.get("bcc"),
                    "tone": state.get("reply_metadata", {}).get("tone"),
                    "brevity": state.get("reply_metadata", {}).get("brevity"),
                }
            }
            supabase.from_("reply_memory").insert(reply_data).execute()
            print("🧠 Saved Reply Memory")

        # --- B. COMPOSE PROMPT MEMORY ---
        # If we composed from a prompt (not necessarily a reply, or a cold email)
        elif state.get("mode") == "COMPOSE" and state.get("draft"):
            user_prompt = state.get("user_prompt") or "User requested draft"
            draft_body = state.get("draft")
            
            prompt_embedding = embed_text(user_prompt)
            draft_embedding = embed_text(draft_body)

            compose_data = {
                "episode_id": episode_id,
                "user_prompt": user_prompt,
                "draft_summary": state.get("summary") or "Draft generated from prompt",
                "draft_body": draft_body,
                "prompt_embedding": prompt_embedding,
                "draft_embedding": draft_embedding,
                "metadata": {
                    "tone": state.get("draft_metadata", {}).get("tone"),
                    "brevity": state.get("draft_metadata", {}).get("brevity"),
                    "summary": state.get("draft_metadata", {}).get("summary"),
                }
            }
            supabase.from_("compose_prompt_memory").insert(compose_data).execute()
            print("🧠 Saved Compose Memory")

        # --- C. PRIORITY EMAIL MEMORY ---
        # Save classification examples. 
        # Iterate over processed emails in state["emails"]
        if state.get("emails"):
            for email in state["emails"]:
                classification = email.get("classification")
                if classification:
                    email_summary = email.get("snippet") or email.get("body") or ""
                    # Embed the email content (summary/snippet) for similarity search
                    email_embedding = embed_text(email_summary)
                    
                    priority_data = {
                        "user_id": user_id,
                        "email_summary": email_summary,
                        "priority": classification.get("priority"),
                        "category": classification.get("category"),
                        "source": email.get("from"), # Using sender as source
                        "email_embedding": email_embedding,
                        "metadata": {
                            "reasoning": classification.get("reasoning"),
                            "intent": classification.get("intent")
                        }
                    }
                    supabase.from_("priority_email_memory").insert(priority_data).execute()
            print(f"🧠 Saved {len(state['emails'])} Priority Memories")

    except Exception as e:
        print("⚠️ Memory write failed:", e)
        print("  This is OK if Supabase is not configured. Core email features will still work.")

    return state
