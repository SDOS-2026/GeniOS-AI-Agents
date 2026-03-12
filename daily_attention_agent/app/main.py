from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from zoneinfo import ZoneInfo

from app.state import DAAState
from app.graph import build_graph
from app.utils.google_creds import load_google_credentials
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
IST = ZoneInfo("Asia/Kolkata")

calendar_llm_cache = {}

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
    }

    graph = build_graph()
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

                print(
                    f"- [{item['priority_level'].upper()}] [{email_time}] {item['title']}"
                )

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

                ts = item["evidence"]["timestamp"]
                event_time = ts.astimezone(IST).strftime("%d %b %H:%M")

                priority = item["priority_level"].upper()

                calendar_name = item["evidence"].get("calendar_name", "")

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

            continue