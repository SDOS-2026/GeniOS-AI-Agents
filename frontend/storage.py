from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from common import EMAIL_DIR


STATE_DIR = EMAIL_DIR / ".streamlit"
HISTORY_FILE = STATE_DIR / "email_history.json"
DRAFTS_FILE = STATE_DIR / "email_drafts.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, value: Any) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history() -> list[dict[str, Any]]:
    return _load_json(HISTORY_FILE, [])


def save_history(history: list[dict[str, Any]]) -> None:
    _save_json(HISTORY_FILE, history)


def append_history(action: str, detail: str, payload: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    history = load_history()
    history.insert(
        0,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "detail": detail,
            "payload": payload,
            "result": result,
        },
    )
    history = history[:200]
    save_history(history)
    return history


def load_drafts() -> dict[str, Any]:
    return _load_json(DRAFTS_FILE, {"reply": None, "compose": None})


def save_drafts(drafts: dict[str, Any]) -> None:
    _save_json(DRAFTS_FILE, drafts)


def export_bundle() -> bytes:
    bundle = {
        "history": load_history(),
        "drafts": load_drafts(),
    }
    return json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")


def import_bundle(raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed = json.loads(raw.decode("utf-8"))
    history = parsed.get("history", [])
    drafts = parsed.get("drafts", {"reply": None, "compose": None})
    if not isinstance(history, list):
        raise ValueError("Invalid history format")
    if not isinstance(drafts, dict):
        raise ValueError("Invalid drafts format")
    save_history(history)
    save_drafts(drafts)
    return history, drafts
