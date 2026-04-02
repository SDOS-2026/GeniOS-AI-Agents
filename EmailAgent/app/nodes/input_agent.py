import json
import re
from app.llm.gemini import interpret_intent
from app.utils.reasoning import add_reasoning


def _safe_structure(intent: str = "UNKNOWN") -> dict:
    return {
        "intent": intent,
        "parameters": {
            "recipient": {"to": [], "cc": [], "bcc": []},
            "subject": None,
            "body": None,
            "attachments": [],
        },
        "filters": {
            "priority": None,
            "time_range": None,
            "limit": None,
        },
    }


def _extract_limit(text: str):
    lower = text.lower()

    direct = re.search(r"\b(?:last|latest|recent)\s+(\d+)\b", lower)
    if direct:
        return int(direct.group(1))

    count_style = re.search(r"\b(\d+)\s+(?:mail|mails|email|emails)\b", lower)
    if count_style:
        return int(count_style.group(1))

    if "most recent" in lower or "latest" in lower or "last mail" in lower or "last email" in lower:
        return 1

    return None


def _fallback_intent(user_prompt: str) -> dict:
    text = (user_prompt or "").strip().lower()
    analysis = _safe_structure("UNKNOWN")

    if not text:
        return analysis

    compose_terms = ["compose", "draft", "write", "send email", "send mail", "mail to", "email to"]
    reply_terms = ["reply", "respond", "response to", "revert to"]
    inbox_terms = ["check", "inbox", "show", "list", "read", "unread", "latest", "recent", "mail", "email"]

    if any(term in text for term in reply_terms):
        analysis["intent"] = "REPLY"
    elif any(term in text for term in compose_terms):
        analysis["intent"] = "COMPOSE"
    elif any(term in text for term in inbox_terms):
        analysis["intent"] = "CHECK_INBOX"

    limit = _extract_limit(text)
    if limit is not None:
        analysis["filters"]["limit"] = limit

    if "urgent" in text or "high priority" in text or "important" in text:
        analysis["filters"]["priority"] = "HIGH"
    elif "low priority" in text:
        analysis["filters"]["priority"] = "LOW"
    elif "medium priority" in text:
        analysis["filters"]["priority"] = "MEDIUM"
    elif analysis["intent"] in {"CHECK_INBOX", "REPLY"}:
        analysis["filters"]["priority"] = "ANY"

    return analysis


def _normalize_analysis(analysis: dict, user_prompt: str) -> dict:
    if not isinstance(analysis, dict):
        return _fallback_intent(user_prompt)

    normalized = _safe_structure(analysis.get("intent", "UNKNOWN"))

    params = analysis.get("parameters") or {}
    rec = params.get("recipient") or {}
    normalized["parameters"]["recipient"] = {
        "to": rec.get("to") or [],
        "cc": rec.get("cc") or [],
        "bcc": rec.get("bcc") or [],
    }
    normalized["parameters"]["subject"] = params.get("subject")
    normalized["parameters"]["body"] = params.get("body")
    normalized["parameters"]["attachments"] = params.get("attachments") or []

    filters = analysis.get("filters") or {}
    normalized["filters"]["priority"] = filters.get("priority")
    normalized["filters"]["time_range"] = filters.get("time_range")
    normalized["filters"]["limit"] = filters.get("limit")

    if normalized["intent"] == "UNKNOWN":
        return _fallback_intent(user_prompt)

    return normalized

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
        analysis = _normalize_analysis(interpret_intent(user_prompt), user_prompt)
    except Exception as e:
        print(f"Intent recognition failed: {e}")
        analysis = _fallback_intent(user_prompt)



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
