"""LLM helpers for EmailAgent."""

from importlib import import_module

from .router import call_llm


def __getattr__(name):
	if name == "router":
		return import_module(f"{__name__}.router")
	raise AttributeError(name)
