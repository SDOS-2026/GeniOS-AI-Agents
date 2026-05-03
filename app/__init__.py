"""Compatibility package for legacy `app.*` imports used by both projects.

This package exposes the EmailAgent and daily_attention_agent app directories on
the import path so existing `from app...` imports continue to work in tests.
"""

from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
__path__ = [
    str(_ROOT / "EmailAgent" / "app"),
    str(_ROOT / "daily_attention_agent" / "app"),
]
