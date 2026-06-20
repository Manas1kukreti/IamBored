from __future__ import annotations


class Orchestrator:
    """Deprecated prompt-planning entrypoint.

    The canonical-intent pipeline no longer routes through prompt-driven
    planning. This stub remains only so old imports fail with a clear error
    instead of silently invoking a legacy fallback.
    """

    def build_plan(self, *args, **kwargs):
        raise RuntimeError(
            "canonical_intent_required: use canonical intents and typed plans."
        )


__all__ = ["Orchestrator"]
