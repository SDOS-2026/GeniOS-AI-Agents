def entry_node(state):
    if state.get("user_prompt"):
        state["mode"] = "COMPOSE"
    else:
        state["mode"] = "INBOX"
    return state
