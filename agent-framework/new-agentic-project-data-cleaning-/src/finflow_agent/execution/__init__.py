"""Execution package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "ColumnNotInPackageError",
    "ContentHashMismatchError",
    "ExecutionEngine",
    "ExecutionError",
    "ExecutionResult",
    "Executor",
    "ExecutorIntentPackage",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from finflow_agent.execution import engine as _engine

    value = getattr(_engine, name)
    globals()[name] = value
    return value
