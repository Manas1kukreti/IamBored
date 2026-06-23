"""Pydantic schemas for visualization API responses."""
from __future__ import annotations

from pydantic import BaseModel, Field


class VisualizationSpecRead(BaseModel):
    """Read schema for a single VisualizationSpec returned in job-detail responses."""

    schema_version: str
    visualization_id: str
    operation_id: str
    source_result_id: str
    status: str
    chart_type: str
    title: str
    encoding: dict = Field(default_factory=dict)
    data: list[dict] = Field(default_factory=list)
    options: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
