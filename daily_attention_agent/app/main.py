from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from zoneinfo import ZoneInfo
import json
from pathlib import Path
from app.state import DAAState
from app.graph import build_graph
from app.utils.google_creds import load_google_credentials
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
IST = ZoneInfo("Asia/Kolkata")

def load_cache(filename: str) -> Dict[str, Any]:
    path = Path(filename)
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load cache {filename}: {e}")
    return {}

def save_cache(filename: str, data: Dict[str, Any]):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save cache {filename}: {e}")

calendar_llm_cache = load_cache("calendar_llm_cache.json")
email_llm_cache = load_cache("email_llm_cache.json")

# ---- Runtime settings ----
SHOW_LOW_CALENDAR_EVENTS = True

def run_daily_attention_agent(
    user_id: str,
    workspace_id: str,
    vip_senders=None,
    keywords=None,
    depth_mode: str = "quick",
    output_mode: str = "brief_only",
) -> Dict[str, Any]:

    vip_senders = vip_senders or []
    keywords = keywords or []

    google_creds = load_google_credentials()

    # ---------- Time Window ----------
    now = datetime.now(IST)

    time_window = {
        "start": now - timedelta(days=3),
        "end": now + timedelta(days=7),
    }

    state = DAAState(
        user_id=user_id,
        workspace_id=workspace_id,
        connected_tools=["gmail", "calendar"],
        time_window=time_window,
        vip_senders=vip_senders,
        keywords=keywords,
        depth_mode=depth_mode,
        output_mode=output_mode,
    )

    state.raw_metadata = {
        "gmail_credentials": google_creds,
        "calendar_credentials": google_creds,
        "calendar_llm_cache": calendar_llm_cache,
        "email_llm_cache": email_llm_cache,
    }

    graph = build_graph()
    # print("main cache id:", id(calendar_llm_cache))
    # print("state cache id:", id(state["raw_metadata"]["calendar_llm_cache"]))
    final_state = graph.invoke(state)

    return final_state


if __name__ == "__main__":

    while True:

        state = run_daily_attention_agent(
            user_id="user_123",
            workspace_id="workspace_123",
            vip_senders=["ceo@company.com"],
            keywords=["urgent", "approval", "deadline"],
        )

        print("\n=== DAILY ATTENTION BRIEF ===\n")

        # Save caches after each run
        save_cache("calendar_llm_cache.json", calendar_llm_cache)
        save_cache("email_llm_cache.json", email_llm_cache)

        emails = []
        events = []

        for item in state["attention_items"]:
            if item["type"] == "email":
                emails.append(item)
            elif item["type"] == "meeting":
                events.append(item)

        print("-- Email --")
        if not emails:
            print("(none)")
        else:
            for item in emails:
                ts = item["evidence"]["timestamp"]
                email_time = ts.astimezone(IST).strftime("%d %b %H:%M")
                priority = item["priority_level"].upper()
                print(f"[{priority}] [{email_time}] {item['title']}")
                if item.get("summary"):
                    print(f"   summary: {item['summary']}")
                else:
                    print("NO summary")
                if item["priority_level"] in ["medium", "high", "critical"]:
                    for r in item["why_flagged"]:
                        print(f"   reason: {r}")
                    print(f"   action: {item['recommended_action']}")
        print("\n-- Events --")

        if not events:
            print("(none)")
        else:
            events_to_show = []
            routine_events = []

            for item in events:

                if item["priority_level"] == "low":

                    if not SHOW_LOW_CALENDAR_EVENTS:
                        routine_events.append(item)
                    else:
                        events_to_show.append(item)

                else:
                    events_to_show.append(item)
                
            for item in events_to_show:

                evidence = item["evidence"]
                ts = evidence["timestamp"].astimezone(IST)
                end_ts = evidence.get("end_time")
                if end_ts:
                    end_ts = end_ts.astimezone(IST)
                is_all_day = evidence.get("is_all_day", False)

                if is_all_day:
                    # Check if it spans multiple days
                    # Note: Google Calendar all-day end date is exclusive
                    if end_ts and (end_ts.date() - ts.date()).days > 1:
                        # Spans multiple days (e.g. Mar 20 - Mar 22)
                        # We show inclusive range: Start date to (End date - 1 day)
                        actual_end = end_ts - timedelta(days=1)
                        event_time = f"{ts.strftime('%d %b')} - {actual_end.strftime('%d %b')} (All Day)"
                    else:
                        event_time = f"{ts.strftime('%d %b')} (All Day)"
                else:
                    # Timed event
                    start_str = ts.strftime("%d %b %H:%M")
                    if end_ts and end_ts != ts:
                        if end_ts.date() == ts.date():
                            # Same day: 20 Mar 10:00 - 11:00
                            duration = end_ts - ts
                            hours, remainder = divmod(duration.total_seconds(), 3600)
                            minutes = (remainder + 30) // 60  # Round to nearest minute
                            if hours > 0:
                                duration_str = f"{int(hours)}h"
                                if minutes > 0:
                                    duration_str += f" {int(minutes)}m"
                            else:
                                duration_str = f"{int(minutes)}m"
                            event_time = f"{start_str} - {end_ts.strftime('%H:%M')} ({duration_str})"
                        else:
                            # Different days: 20 Mar 10:00 - 21 Mar 11:00
                            event_time = f"{start_str} - {end_ts.strftime('%d %b %H:%M')}"
                    else:
                        event_time = start_str

                priority = item["priority_level"].upper()
                calendar_name = evidence.get("calendar_name", "")

                print(f"\n[{priority}] {event_time}  {item['title']} ({calendar_name})")

                for r in item["why_flagged"]:
                    print(f"   reason: {r}")

                print(f"   action: {item['recommended_action']}")
            
            if not SHOW_LOW_CALENDAR_EVENTS and routine_events:

                print("\nRoutine schedule:")

                count = len(routine_events)

                calendars = set()

                for e in routine_events:
                    cal = e["evidence"].get("calendar_name", "")
                    calendars.add(cal)

                cal_list = ", ".join(calendars)

                print(f"   • {count} routine events from calendars: {cal_list}")


        print("\n-- Attention Required --")

        risks = state.get("risks", [])

        if not risks:
            print("(none)")
        else:
            for r in risks:
                print(f"- {r['title']}")
                print(f"  {r['reason']}")

                risk_events = r.get("events", [])
                for e in risk_events[:5]:
                    print(f"   • {e}")

                if len(risk_events) > 5:
                    print(f"   • +{len(risk_events)-5} more")



        cmd = input("\nRun again? (y/n/settings): ").strip().lower()

        if cmd == "settings":

            while True:

                print("\nSettings")
                print("1. Toggle LOW calendar events")
                print("2. Back")

                s = input("Choice: ").strip()

                if s == "1":
                    SHOW_LOW_CALENDAR_EVENTS = not SHOW_LOW_CALENDAR_EVENTS

                    state = "ON" if SHOW_LOW_CALENDAR_EVENTS else "OFF"
                    print(f"\nShow LOW priority calendar events: {state}")

                elif s == "2":
                    break
        elif cmd == 'y':
            continue
        else:
            break
