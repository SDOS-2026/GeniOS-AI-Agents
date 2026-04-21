from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from zoneinfo import ZoneInfo
import json
from pathlib import Path
from app.core.state import DAAState
from app.core.graph import build_graph
from app.core.graph import build_graph
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
SHOW_LOW_EMAIL_EVENTS = True

async def run_daily_attention_agent(
    payload: Dict[str, Any],
    mcp_session: Any = None,
) -> Dict[str, Any]:
    user_id = payload.get("user_id")
    workspace_id = payload.get("workspace_id")
    vip_senders = payload.get("vip_senders") or []
    keywords = payload.get("keywords") or []
    depth_mode = payload.get("depth_mode", "quick")
    output_mode = payload.get("output_mode", "brief_only")

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
        mcp_session=mcp_session,
    )

    state.raw_metadata = {
        "calendar_llm_cache": calendar_llm_cache,
        "email_llm_cache": email_llm_cache,
    }

    graph = build_graph()
    final_state = await graph.ainvoke(state)

    return final_state



# CLI entry point has been moved to app/api/main.py

