from app.memory.supabase_client import supabase
from app.memory.embeddings import embed_text

def memory_retrieve_node(state):
    print("retrieving memory!!!!")
    user_id = state.get("user_id", "default_user")

    query_text = (
        state.get("user_input")
        or state.get("user_prompt")
        or ""
    )

    if not query_text.strip():
        state["compose_memory"] = []
        state["reply_memory"] = []
        return state

    # If Supabase is not configured, skip memory retrieval
    if supabase is None:
        state["episodic_memory"] = []
        return state

    # If Supabase is not configured, skip memory retrieval
    if supabase is None:
        state["episodic_memory"] = []
        return state

    try:
        query_embedding = embed_text(query_text)
    except Exception as e:
        print("⚠️ Memory retrieval embedding failed:", e)
        state["compose_memory"] = []
        state["reply_memory"] = []
        return state

    # Decide which memory to retrieve
    rpc_func = None
    target_key = None

    if state.get("mode") == "COMPOSE":
        rpc_func = "match_compose_prompt_memory"
        target_key = "compose_memory"

    elif state.get("user_action") == "REPLY":
        rpc_func = "match_reply_memory"
        target_key = "reply_memory"

    if not rpc_func:
        state["compose_memory"] = []
        state["reply_memory"] = []
        return state

    try:
        response = supabase.rpc(
            rpc_func,
            {
                "query_embedding": query_embedding,
                "match_user_id": user_id,
                "match_count": 3,
            }
        ).execute()

        state[target_key] = response.data or []
        print(f"🧠 Retrieved {len(state[target_key])} memories via {rpc_func}")

    except Exception as e:
        print(f"⚠️ Memory retrieval RPC ({rpc_func}) failed:", e)
        print("  This is OK if Supabase is not configured. Core email features will still work.")
        state[target_key] = []

    return state
