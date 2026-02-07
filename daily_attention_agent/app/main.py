# app/main.py

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from app.state import DAAState
from app.graph import build_graph
from app.utils.google_creds import load_google_credentials

from dotenv import load_dotenv
load_dotenv()


def run_daily_attention_agent(
    user_id: str,
    workspace_id: str,
    vip_senders=None,
    keywords=None,
    depth_mode: str = "quick",
    output_mode: str = "brief_only",
) -> Dict[str, Any]:
    """
    Entry point for running Daily Attention Agent (V1).
    Credentials are loaded from environment variables.
    """

    vip_senders = vip_senders or []
    keywords = keywords or []

    # ---------- Load Google Credentials ----------
    google_creds = load_google_credentials()

    # ---------- Time Window ----------
    now = datetime.now(timezone.utc)

    time_window = {
        "start": now - timedelta(days=3),
        "end": now + timedelta(days=7),
    }

    # ---------- Initial State ----------
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

    # Inject credentials (V1-safe)
    state.raw_metadata = {
        "gmail_credentials": google_creds,
        "calendar_credentials": google_creds,
    }

    # ---------- Run Graph ----------
    graph = build_graph()
    final_state: DAAState = graph.invoke(state)

    return {
        "attention_items": final_state.attention_items,
        "risks": final_state.risks,
        "opportunities": final_state.opportunities,
        "warnings": final_state.warnings,
        "run_started_at": final_state.run_started_at.isoformat(),
        "run_completed_at": final_state.run_completed_at.isoformat()
        if final_state.run_completed_at
        else None,
    }


if __name__ == "__main__":
    output = run_daily_attention_agent(
        user_id="user_123",
        workspace_id="workspace_123",
        vip_senders=["ceo@company.com"],
        keywords=["urgent", "approval", "deadline"],
    )

    print("\n=== DAILY ATTENTION BRIEF ===\n")
    for item in output["attention_items"]:
        print(f"- [{item['priority_level'].upper()}] {item['title']}")
