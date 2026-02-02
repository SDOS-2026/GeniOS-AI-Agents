def summarize_compose_memory(memories):
    prefs = {
        "tone": None,
        "brevity": None,
    }

    if not memories:
        return prefs
        
    # The new memories come from 'compose_prompt_memory' or 'reply_memory'.
    # They should have a 'metadata' field.
    # We assume valid memories are passed (retrieval logic filters relevant ones).

    tones = []
    for m in memories:
        meta = m.get("metadata") or {}
        if meta.get("tone"):
            tones.append(meta["tone"])

    if tones:
        prefs["tone"] = max(set(tones), key=tones.count)

    # Simplified logic: if we found any valid memory, default to concise if not specified
    if memories:
        prefs["brevity"] = "concise"
        
    return prefs
