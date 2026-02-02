import json
from app.llm.gemini import interpret_intent
from app.utils.reasoning import add_reasoning

def input_agent_node(state):
    """
    Analyzes the user prompt and determines the intent, filters, and parameters.
    Default router / decision diamond.
    """
    state.setdefault("show_reasoning", True)
    state.setdefault("reasoning", [])
    user_prompt = state.get("user_prompt", "")
    
    if not user_prompt:
        # If no prompt, maybe we are just entering? 
        # But this node usually expects a prompt.
        # Default to checking inbox if empty? Or ask?
        # Let's assume prompt is present or we ask.
        pass

    print(f"Thinking about: '{user_prompt}'")
    
    try:
        analysis = interpret_intent(user_prompt)
    except Exception as e:
        print(f"⚠️ Intent recognition failed: {e}")
        # Fallback to simple keyword matching or just UNKNOWN
        analysis = {
            "intent": "UNKNOWN",
            "parameters": {
                "recipient": {"to": [], "cc": [], "bcc": []},
                "subject": None,
                "body": None,
                "attachments": []
            },
            "filters": {
                "priority": None,
                "time_range": None,
                "limit": None
            }
        }



    state["mode"] = analysis["intent"]
    filters = analysis.get("filters") or {}
    state["filter_criteria"] = {
        "priority": filters.get("priority"),
        "time_range": filters.get("time_range"),
        "limit": filters.get("limit")
    }

    params = analysis["parameters"]
    state["recipient"] = params["recipient"]
    state["subject"] = params["subject"]
    state["body"] = params["body"]
    state["attachments"] = params.get("attachments", [])

    add_reasoning(state, f"Detected intent: {state['mode']}.")
    if state["mode"] == "CHECK_INBOX":
        pr = state["filter_criteria"].get("priority", "ANY")
        if pr != "ANY":
            add_reasoning(state, f"Checking inbox with priority filter: {pr}.")
        else:
            add_reasoning(state, "Checking inbox with no special filters.")
    elif state["mode"] == "COMPOSE":
        add_reasoning(state, "Preparing to compose a new email.")
    elif state["mode"] == "REPLY":
        add_reasoning(state, "Reply intent detected; inbox context is required.")
        
    return state
