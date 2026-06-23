"""Visualization intent enricher for the canonical intent pipeline.

Integrates the TriggerDetector with the intent classification pipeline.
When trigger language is detected in the user prompt, this module enriches
the canonical intent's actions list with a VisualizeIntent action.

This module acts as the bridge between explicit trigger detection
(TriggerDetector) and the canonical intent model (CanonicalIntent.actions).

Flow:
    User Prompt → TriggerDetector.detect() → triggered?
        YES → Add VisualizeIntent action to canonical intent
        NO  → Leave canonical intent unchanged (empty visualizations array)

Requirements: 1.1, 1.4, 2.1, 5.2, 13.1, 13.2
"""

from __future__ import annotations

from typing import Any

from finflow_agent.planning.trigger_detector import TriggerDetector


# Module-level singleton detector instance.
_detector = TriggerDetector()


def enrich_intent_with_visualization(
    canonical_intent: dict[str, Any],
) -> dict[str, Any]:
    """Enrich a canonical intent dict with a VisualizeIntent action if trigger detected.

    Inspects the ``original_prompt`` field of the canonical intent. If the
    TriggerDetector finds visualization trigger language, a ``VisualizeIntent``
    action is appended to the ``actions`` list (unless one already exists).

    When no trigger language is detected, the canonical intent is returned
    unchanged — ensuring jobs without visualization intent produce empty
    visualizations arrays (Req 13.1, 13.2).

    Args:
        canonical_intent: A canonical intent dictionary (typically produced
            by the backend's intent creation pipeline).

    Returns:
        The same dict, potentially with a VisualizeIntent action appended.
        The dict is mutated in-place for efficiency but also returned for
        convenient chaining.

    Requirements: 1.1, 1.4, 2.1, 5.2, 13.1, 13.2
    """
    if not isinstance(canonical_intent, dict):
        return canonical_intent

    # Extract the original prompt for trigger detection.
    prompt = canonical_intent.get("original_prompt", "")
    if not prompt or not isinstance(prompt, str):
        return canonical_intent

    # Check if a VisualizeIntent action already exists.
    actions = canonical_intent.get("actions", [])
    if not isinstance(actions, list):
        actions = []
        canonical_intent["actions"] = actions

    for action in actions:
        if isinstance(action, dict) and action.get("kind") == "visualize":
            # Already has a visualization action — no enrichment needed.
            return canonical_intent

    # Run trigger detection.
    result = _detector.detect(prompt)

    if not result.triggered:
        # No trigger language found — no visualization intent (Req 13.1, 13.2).
        return canonical_intent

    # Build and append a VisualizeIntent action.
    visualize_action: dict[str, Any] = {
        "kind": "visualize",
        "chart_type": result.chart_type_hint,
        "fields": [],
    }
    actions.append(visualize_action)

    return canonical_intent


def should_produce_visualization(prompt: str) -> bool:
    """Check whether a prompt should produce a visualization intent.

    Simple utility function for use in pipelines that need a boolean
    check without modifying the intent.

    Args:
        prompt: The user's input prompt text.

    Returns:
        True if the prompt contains visualization trigger language.

    Requirements: 1.1, 1.4
    """
    if not prompt or not isinstance(prompt, str):
        return False
    result = _detector.detect(prompt)
    return result.triggered


__all__ = [
    "enrich_intent_with_visualization",
    "should_produce_visualization",
]
