from typing import List, Tuple
from datetime import datetime, timezone
from collections import defaultdict
from app.models.unified_signal import UnifiedSignal
from app.llm.client import gemini_calendar_batch_priority
from datetime import timedelta


def detect_conflicts(signals):

    events = sorted(signals, key=lambda s: s.timestamp)

    overlapping = set()

    for i in range(len(events)):
        for j in range(i + 1, len(events)):

            a = events[i]
            b = events[j]

            if a.is_all_day or b.is_all_day:
                continue

            if not a.end_time or not b.end_time:
                continue

            if a.timestamp < b.end_time and b.timestamp < a.end_time:
                overlapping.add(a.title)
                overlapping.add(b.title)

    if not overlapping:
        return []

    return [{
        "title": "Calendar conflicts",
        "reason": "Overlapping meetings detected",
        "events": list(overlapping)
    }]


def detect_overload(signals):

    hours_per_day = defaultdict(float)
    events_per_day = defaultdict(list)

    for s in signals:

        if s.is_all_day:
            continue

        if not s.end_time:
            continue

        duration = (s.end_time - s.timestamp).total_seconds() / 3600
        day = s.timestamp.date()

        hours_per_day[day] += duration
        events_per_day[day].append(s.title)

    risks = []

    for day, hours in hours_per_day.items():

        if hours >= 5:
            risks.append({
                "title": "Meeting overload",
                "reason": f"{hours:.1f} hours of meetings on {day}",
                "events": events_per_day[day]
            })

    return risks

def detect_missing_links(signals):

    affected = []

    for s in signals:
        if s.is_all_day:
            continue

        if s.raw_metadata.get("attendee_count", 0) <= 1:
            continue

        if not s.raw_metadata.get("has_meet_link", True):
            affected.append(s.title)

    if not affected:
        return []

    return [{
        "title": "Meetings missing join links",
        "reason": f"{len(affected)} events missing links",
        "events": affected
    }]


def detect_missing_agenda(signals):

    affected = []

    for s in signals:
        if s.is_all_day:
            continue

        if s.snippet == "No description provided":
            affected.append(s.title)

    if not affected:
        return []

    return [{
        "title": "Events missing agenda",
        "reason": f"{len(affected)} events lack descriptions",
        "events": affected
    }]

def detect_duplicates(signals):

    seen = {}
    duplicates = set()

    for s in signals:
        key = (s.title, s.timestamp)

        if key in seen:
            duplicates.add(s.title)
        else:
            seen[key] = True

    if not duplicates:
        return []

    return [{
        "title": "Duplicate calendar events",
        "reason": f"{len(duplicates)} duplicated events detected",
        "events": list(duplicates)
    }]



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
                "category": None}
            
    print("[DEBUG] Calendar addetinal cache size:", len(cache))