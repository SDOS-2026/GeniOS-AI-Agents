"""
Nodes package for EmailAgent graph execution.
"""

from importlib import import_module


def __getattr__(name):
	if name in {
		"approval",
		"classify",
		"compose",
		"draft",
		"entry",
		"extract",
		"fetch",
		"inbox_review",
		"input_agent",
		"review",
		"risk",
		"send",
		"summarize",
	}:
		return import_module(f"{__name__}.{name}")
	raise AttributeError(name)
