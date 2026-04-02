from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


FRONTEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = FRONTEND_DIR.parent
DAILY_DIR = REPO_ROOT / "daily_attention_agent"
EMAIL_DIR = REPO_ROOT / "EmailAgent"


def run_agent_command(agent: str, command: str, payload: dict[str, Any]) -> dict[str, Any]:
    if agent == "daily":
        target_dir = DAILY_DIR
    elif agent == "email":
        target_dir = EMAIL_DIR
    else:
        return {"ok": False, "error": f"Unknown agent: {agent}"}

    proc = subprocess.run(
        [sys.executable, "-m", "app.streamlit_runner", command],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(target_dir),
    )

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if not stdout:
        return {
            "ok": False,
            "error": stderr or f"No output returned from {command}",
            "stderr": stderr,
            "command": command,
            "agent": agent,
        }

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": stderr or stdout,
            "stderr": stderr,
            "raw_stdout": stdout,
            "command": command,
            "agent": agent,
        }

    if proc.returncode != 0:
        parsed.setdefault("ok", False)
        if stderr:
            parsed["stderr"] = stderr
        parsed["command"] = command
        parsed["agent"] = agent

    return parsed


def format_dt(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return value
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y, %H:%M")
    return str(value)


def json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)
