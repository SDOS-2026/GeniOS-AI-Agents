def approval_node(state):
    risk_flags = state.get("risk_flags", [])

    if risk_flags:
        state["approval_status"] = "REQUIRED"
    else:
        state["approval_status"] = "NOT_REQUIRED"

    return state
