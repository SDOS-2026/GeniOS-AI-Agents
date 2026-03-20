# app/rules/email_rules.py

from typing import List, Tuple
from datetime import datetime, timedelta, timezone

from app.models.unified_signal import UnifiedSignal


from app.llm.client import gemini_gmail_batch_priority


def apply_email_rules(
    signal: UnifiedSignal,
    vip_senders: List[str],
    keywords: List[str],
) -> Tuple[float, List[str]]:
    """
    Deterministic email scoring rules.
    Returns (score_delta, reasons)
    """
    score = 5.0
    reasons: List[str] = ["Selected for attention check"]

    meta = signal.raw_metadata
    last_sender = meta.get("last_sender", "").lower()

    # 1. Requires action
    if signal.requires_action:
        score += 25
        reasons.append("Email likely requires a reply")

    # 2. VIP sender
    for vip in vip_senders:
        if vip.lower() in last_sender:
            score += 30
            reasons.append("Email from VIP sender")
            break

    # 3. Keyword intent
    content = f"{signal.title} {signal.snippet}".lower()
    for kw in keywords:
        if kw.lower() in content:
            score += 15
            reasons.append(f"Contains keyword: '{kw}'")
            break

    # 4. Staleness
    now_utc = datetime.now(timezone.utc)
    age_hours = (now_utc - signal.timestamp).total_seconds() / 3600
    if age_hours > 24:
        score += 10
        reasons.append("Email pending for over 24 hours")

    if age_hours > 72:
        score += 10
        reasons.append("Email pending for over 72 hours")

    return score, reasons


def apply_email_batch(signals, cache, vip_senders, keywords):
    """
    Apply LLM-based batch scoring for emails with rule-based fallback.
    """
    if not signals:
        return

    uncached_signals = []

    # ---------- Check cache first ----------
    for s in signals:
        cache_key = f"{s.record_id}_{s.timestamp.isoformat()}"
        if cache_key in cache:
            cached = cache[cache_key]
            meta = s.raw_metadata
            meta["llm_score"] = cached["score"]
            meta["llm_reasons"] = cached["reasons"]
            meta["category"] = cached.get("category")
            meta["llm_cached"] = True
        else:
            uncached_signals.append(s)

    if not uncached_signals:
        print("[DEBUG] All emails loaded from cache")
        return

    try:
        results = gemini_gmail_batch_priority(uncached_signals)

        for s in uncached_signals:
            cache_key = f"{s.record_id}_{s.timestamp.isoformat()}"
            r = results.get(s.record_id)

            meta = s.raw_metadata

            if r is None:
                score, reasons = apply_email_rules(s, vip_senders, keywords)
                meta["llm_score"] = score
                meta["llm_reasons"] = reasons
                meta["llm_cached"] = False
                cache[cache_key] = {"score": score, "reasons": reasons, "category": None}
                continue

            score = float(r["score"])
            reasons = r["reasons"]
            category = r.get("category")

            meta["llm_score"] = score
            meta["llm_reasons"] = reasons
            meta["category"] = category
            meta["llm_cached"] = False

            # ---------- Save to cache ----------
            cache[cache_key] = {"score": score, "reasons": reasons, "category": category}

    except Exception as e:
        print("\n====== GMAIL GEMINI ERROR ======")
        print(e)
        print("============================\n")

        for s in uncached_signals:
            cache_key = f"{s.record_id}_{s.timestamp.isoformat()}"
            score, reasons = apply_email_rules(s, vip_senders, keywords)
            meta = s.raw_metadata
            meta["llm_score"] = score
            meta["llm_reasons"] = reasons
            meta["llm_cached"] = False
            cache[cache_key] = {"score": score, "reasons": reasons, "category": None}
    
    print("[DEBUG] Email additional cache size:", len(cache))
