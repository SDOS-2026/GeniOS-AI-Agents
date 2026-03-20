from typing import List, Tuple
from datetime import datetime, timezone

from app.models.unified_signal import UnifiedSignal
from app.llm.client import gemini_calendar_batch_priority
from datetime import timedelta


def detect_calendar_risks(signals):
    """
    Analyze calendar signals for conflicts, overload, and missing info.
    Returns list of risk dicts.
    """

    risks = []

    events = sorted(signals, key=lambda s: s.timestamp)

    # ---------- Conflict detection ----------
    for i in range(len(events) - 1):
        a = events[i]
        b = events[i + 1]

        if abs((b.timestamp - a.timestamp).total_seconds()) < 3600:
            risks.append({
                "title": "Calendar conflict",
                "reason": f"{a.title} overlaps with {b.title}",
                "tool": "calendar",
            })

    # ---------- Back-to-back overload ----------
    consecutive = 1
    for i in range(len(events) - 1):
        diff = (events[i + 1].timestamp - events[i].timestamp)

        if diff <= timedelta(minutes=5):
            consecutive += 1
        else:
            consecutive = 1

        if consecutive >= 3:
            risks.append({
                "title": "Meeting overload",
                "reason": f"{consecutive} meetings scheduled back-to-back",
                "tool": "calendar",
            })

    # ---------- Missing link ----------
    for e in events:
        if not e.raw_metadata.get("has_meet_link", True):
            risks.append({
                "title": e.title,
                "reason": "Meeting has no join link or location",
                "tool": "calendar",
            })

    # ---------- Missing agenda ----------
    for e in events:
        if not e.snippet or e.snippet == "No description provided":
            risks.append({
                "title": e.title,
                "reason": "Meeting has no agenda or description",
                "tool": "calendar",
            })

    return risks

def rule_based_fallback(signal: UnifiedSignal):

    score = 0
    reasons = []

    meta = signal.raw_metadata

    now_utc = datetime.now(timezone.utc)
    hours_until = (signal.timestamp - now_utc).total_seconds() / 3600

    if 0 <= hours_until <= 2:
        score += 30
        reasons.append("Meeting starting soon")

    if not meta.get("has_meet_link", True):
        score += 20
        reasons.append("Missing meeting link")

    if not signal.snippet or signal.snippet == "No description provided":
        score += 15
        reasons.append("No agenda")

    if meta.get("attendee_count", 0) >= 3:
        score += 10
        reasons.append("Multiple attendees")

    return score, reasons

def apply_calendar_batch(signals, cache):



    if not signals:
        return


    uncached_signals = []

    # ---------- Check cache first ----------
    for s in signals:

        cache_key = f"{s.record_id}_{s.timestamp.isoformat()}"
        # print("[DEBUG] LOOKUP KEY:", cache_key)
        # print("[DEBUG] CACHE KEYS SAMPLE:", list(cache.keys())[:3])
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
        print("[DEBUG] All cal events loaded from cache")
        return

    try:
        results = gemini_calendar_batch_priority(uncached_signals)

        for s in uncached_signals:

            cache_key = f"{s.record_id}_{s.timestamp.isoformat()}"
            r = results.get(cache_key)

            meta = s.raw_metadata

            if r is None:
                score, reasons = rule_based_fallback(s)

                meta["llm_score"] = score
                meta["llm_reasons"] = reasons
                meta["llm_cached"] = False

                cache[cache_key] = {
                    "score": score,
                    "reasons": reasons,
                    "category": None
                }

                continue

            score = float(r["score"])
            reasons = r["reasons"]
            category = r.get("category")

            meta["llm_score"] = score
            meta["llm_reasons"] = reasons
            meta["category"] = category
            meta["llm_cached"] = False

            # ---------- Save to cache ----------
            cache[cache_key] = {
                "score": score,
                "reasons": reasons,
                "category": category
            }

    except Exception as e:

        print("\n====== GEMINI ERROR ======")
        print(e)
        print("==========================\n")

        for s in uncached_signals:

            cache_key = f"{s.record_id}_{s.timestamp.isoformat()}"
            score, reasons = rule_based_fallback(s)

            meta = s.raw_metadata
            meta["llm_score"] = score
            meta["llm_reasons"] = reasons
            meta["llm_cached"] = False

            cache[cache_key] = {
                "score": score,
                "reasons": reasons,
                "category": None
            }
    print("[DEBUG] Calendar addetinal cache size:", len(cache))