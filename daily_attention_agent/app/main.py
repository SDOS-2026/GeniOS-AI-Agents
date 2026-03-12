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

IST = ZoneInfo("Asia/Kolkata")

calendar_llm_cache = {}


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
            
            for item in events:

                ts = item["evidence"]["timestamp"]
                event_time = ts.astimezone(IST).strftime("%d %b %H:%M")

                priority = item["priority_level"].upper()

                snippet = item["evidence"]["snippet"]
                calendar_name = snippet.split("]")[0].strip("[") if snippet.startswith("[") else ""

                print(f"\n[{priority}] {event_time}  {item['title']} ({calendar_name})")

                for r in item["why_flagged"]:
                    print(f"   reason: {r}")

                print(f"   action: {item['recommended_action']}")
            
            print("\n-- Risks --")

            if not state.risks:
                print("(none)")
            else:
                for r in state.risks:
                    print(f"- {r['title']}: {r['reason']}")

        again = input("\nRun again? (y/n): ").strip().lower()

        if again != "y":
            break
