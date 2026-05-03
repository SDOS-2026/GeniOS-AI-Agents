"""EmailAgent application package."""

from importlib import import_module


def __getattr__(name):
	if name in {
		"classification",
		"gmail",
		"graph",
		"guardrails",
		"llm",
		"memory",
		"nodes",
		"policy",
		"utils",
	}:
		return import_module(f"{__name__}.{name}")
	raise AttributeError(name)
