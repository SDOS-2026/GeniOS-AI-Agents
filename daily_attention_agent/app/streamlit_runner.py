from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import sys
from datetime import datetime
from typing import Any

from app.main import run_daily_attention_agent


def _json_safe(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))

    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump(mode="json"))
        except TypeError:
            return _json_safe(value.model_dump())

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]

    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=str)]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def run_brief(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = payload.get("user_id", "user_123")
    workspace_id = payload.get("workspace_id", "workspace_123")
    vip_senders = payload.get("vip_senders") or []
    keywords = payload.get("keywords") or []
    depth_mode = payload.get("depth_mode", "quick")
    output_mode = payload.get("output_mode", "brief_only")

    with contextlib.redirect_stdout(io.StringIO()):
        state = run_daily_attention_agent(
            user_id=user_id,
            workspace_id=workspace_id,
            vip_senders=vip_senders,
            keywords=keywords,
            depth_mode=depth_mode,
            output_mode=output_mode,
        )

    if hasattr(state, "model_dump"):
        state_data = state.model_dump(mode="json")
    else:
        state_data = dict(state)

    result = {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "run_started_at": _json_safe(state_data.get("run_started_at")),
        "run_completed_at": _json_safe(state_data.get("run_completed_at")),
        "attention_items": _json_safe(state_data.get("attention_items", [])),
        "risks": _json_safe(state_data.get("risks", [])),
        "opportunities": _json_safe(state_data.get("opportunities", [])),
        "warnings": _json_safe(state_data.get("warnings", [])),
    }

    return _json_safe(result)


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing command"}), file=sys.stderr)
        return 2

    command = sys.argv[1]
    payload_text = sys.stdin.read().strip()
    payload = json.loads(payload_text) if payload_text else {}

    if command != "run":
        print(json.dumps({"ok": False, "error": f"Unknown command: {command}"}), file=sys.stderr)
        return 2

    try:
        result = run_brief(payload)
        print(json.dumps({"ok": True, "result": result}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())