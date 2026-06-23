"""Visualization agent for chart generation.

Produces a VisualizationSpec by consuming the OperationResult from upstream
calculation/filter steps. Delegates actual chart logic to the
VisualizationExecutor, which performs zero calculations — only structural
mapping from the operation result to a renderable chart spec.

The agent is gated by the ``ENABLE_VISUALIZATION`` config flag. When enabled,
it reads the upstream DataFrame/OperationResult, builds encoding from the
plan, and produces a VisualizationSpec that gets persisted and rendered.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from pydantic import BaseModel

from finflow_agent.registry import registry, AgentSpec
from finflow_agent.state import AgentResult
from finflow_agent.operations.schemas import VisualizationOperationPlan


logger = logging.getLogger(__name__)

# Canonical disabled-message used by the compiler, validator, and orchestrator
# when visualization is requested while the agent is disabled.
VISUALIZATION_DISABLED_MESSAGE = (
    "visualization_agent is not enabled in this version"
)


class VisualizationAgentParams(BaseModel):
    """Pydantic param model for the visualization agent."""

    plan: VisualizationOperationPlan


@registry.register
class VisualizationAgent:
    """Visualization agent that produces chart specs from operation results.

    When enabled, delegates to the VisualizationExecutor to generate a
    VisualizationSpec. The spec is returned as part of the AgentResult
    artifacts for downstream persistence and rendering.
    """

    spec = AgentSpec(
        name="visualization_agent",
        description=(
            "Produces a VisualizationSpec from upstream operation results. "
            "Performs zero business calculations — only structural mapping."
        ),
        stage="visualize",
        accepts=["dataframe"],
        produces=["chart_spec"],
        params_schema={
            "plan": {"type": "object"}
        },
    )
    params_model = VisualizationAgentParams

    def execute(self, params: dict, input_data: dict) -> AgentResult:
        """Execute the visualization agent.

        Reads the upstream operation result (or DataFrame), runs it through
        the VisualizationExecutor, and returns the resulting spec.
        The input DataFrame is passed through unchanged (zero-calculation).
        """
        # Pass through the input DataFrame so downstream steps (reporting) get it
        import pandas as pd
        input_df = input_data.get("input_dataframe")

        try:
            from finflow_agent.execution.visualization.executor import VisualizationExecutor
            from finflow_agent.execution.visualization.spec import VisualizationSpec

            # Extract plan params
            plan = params.get("plan", {})
            charts = plan.get("charts", []) if isinstance(plan, dict) else []

            if not charts:
                return AgentResult(
                    status="success",
                    data=input_df,
                    summary="No charts requested in visualization plan.",
                    artifacts={"visualizations": []},
                )

            executor = VisualizationExecutor()
            visualization_specs: list[dict[str, Any]] = []

            # Build an operation_result-like structure from the input DataFrame.
            # Pass chart configs so aggregation metadata can be set on output fields.
            operation_result = self._build_operation_result(input_data, charts=charts)

            for chart_config in charts:
                chart_type = chart_config.get("type", "auto")
                # Map "auto" or missing to let executor handle it
                if not chart_type:
                    chart_type = "auto"

                # Build encoding hints from chart config or auto-detect from fields
                encoding_hints = self._build_encoding_hints(
                    chart_config, chart_type, operation_result
                )

                source_result_id = str(uuid.uuid4())
                operation_id = f"viz_{uuid.uuid4().hex[:8]}"

                spec = executor.execute(
                    operation_result=operation_result,
                    chart_type=chart_type,
                    encoding_hints=encoding_hints,
                    source_result_id=source_result_id,
                    operation_id=operation_id,
                )
                visualization_specs.append(spec.model_dump())

            # Determine overall status — always "success" to avoid blocking
            # the reporting agent downstream (failure isolation per Req 6.1).
            # Visualization failures are recorded in the spec artifacts.
            all_failed = all(s.get("status") == "failed" for s in visualization_specs)
            any_failed = any(s.get("status") in ("failed", "unsupported") for s in visualization_specs)

            if all_failed:
                summary = "All visualization attempts produced unsupported/failed specs."
            elif any_failed:
                summary = f"Generated {len(visualization_specs)} visualization(s), some with warnings."
            else:
                summary = f"Successfully generated {len(visualization_specs)} visualization(s)."

            return AgentResult(
                status="success",
                data=input_df,
                summary=summary,
                artifacts={"visualizations": visualization_specs},
            )

        except Exception as exc:
            logger.exception("Visualization agent failed: %s", exc)
            # Still return success with the DataFrame to not block reporting
            return AgentResult(
                status="success",
                data=input_df,
                summary=f"Visualization failed: {str(exc)[:200]}",
                artifacts={"visualizations": []},
                warnings=[f"Visualization error: {str(exc)[:300]}"],
            )

    @staticmethod
    def _build_operation_result(input_data: dict, charts: list | None = None) -> dict[str, Any]:
        """Build an OperationResult-compatible dict from agent input_data.

        The input_data typically contains a DataFrame under the key
        'input_dataframe' (set by the execution engine). We convert it into
        the OperationResult format that the VisualizationExecutor expects.

        When charts config is provided, output fields from aggregation
        operations will have their aggregation metadata set correctly.
        """
        import pandas as pd

        # Build a set of output fields that have aggregation from chart configs
        aggregated_fields: dict[str, str] = {}  # output_field -> aggregation
        if charts:
            for chart in charts:
                if isinstance(chart, dict):
                    agg = chart.get("aggregation")
                    output_field = chart.get("output_field") or "record_count"
                    if agg:
                        aggregated_fields[output_field] = agg

        df = input_data.get("input_dataframe")
        if df is None:
            df = input_data.get("df")
        if df is None:
            df = input_data.get("dataframe")
        if df is None:
            # Try to find any DataFrame in input_data values
            for v in input_data.values():
                if isinstance(v, pd.DataFrame):
                    df = v
                    break

        if df is None:
            return {"fields": [], "rows": []}

        if isinstance(df, pd.DataFrame):
            # Build field metadata from DataFrame columns
            fields = []
            for col in df.columns:
                dtype = df[col].dtype
                if pd.api.types.is_integer_dtype(dtype):
                    data_type = "integer"
                elif pd.api.types.is_float_dtype(dtype):
                    data_type = "float"
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    data_type = "datetime"
                else:
                    data_type = "string"

                # Infer role from data type and column name
                col_lower = str(col).lower().strip()

                # Identifier detection: columns that are IDs, keys, or numbers
                # should NOT be treated as measures even if they are numeric
                is_identifier = (
                    col_lower == "id"
                    or col_lower.endswith("_id")
                    or col_lower.endswith("_number")
                    or col_lower.endswith("_key")
                    or col_lower.endswith("_no")
                    or col_lower.startswith("id_")
                    or col_lower in ("index", "row_number", "record_id")
                )

                if is_identifier:
                    role = "identifier"
                elif data_type in ("integer", "float"):
                    # Check if the field has aggregation metadata (from
                    # pre-aggregated data coming through calculation_agent)
                    role = "measure"
                elif data_type == "datetime":
                    role = "time"
                else:
                    # String columns with low cardinality → category
                    nunique = df[col].nunique()
                    total = len(df)
                    if total > 0 and nunique / total < 0.5:
                        role = "category"
                    else:
                        role = "dimension"

                fields.append({
                    "id": str(col),
                    "label": str(col),
                    "data_type": data_type,
                    "role": role,
                    "unit": None,
                    "aggregation": aggregated_fields.get(str(col)),
                })

            # Convert rows — ensure native Python types for Pydantic strict mode
            rows = []
            for record in df.head(1000).to_dict(orient="records"):
                clean_row = {}
                for k, v in record.items():
                    if hasattr(v, "item"):
                        # Convert numpy scalars to native Python types
                        clean_row[str(k)] = v.item()
                    elif pd.isna(v):
                        clean_row[str(k)] = None
                    else:
                        clean_row[str(k)] = v
                rows.append(clean_row)

            return {"fields": fields, "rows": rows}

        return {"fields": [], "rows": []}

    @staticmethod
    def _build_encoding_hints(
        chart_config: dict,
        chart_type: str,
        operation_result: dict[str, Any],
    ) -> dict[str, str] | None:
        """Build encoding hints from chart config or auto-detect from fields.

        If the chart config specifies explicit x/y fields (not "auto"),
        use those. Otherwise, auto-detect from the operation result's field
        metadata based on the chart type.

        Fields with role "identifier" are excluded from measure candidates
        to prevent IDs/keys from being selected as chart value axes.
        """
        x_field = chart_config.get("x")
        y_field = chart_config.get("y")

        # If explicit fields provided, use them
        if x_field and x_field != "auto" and y_field and y_field != "auto":
            return {"x": x_field, "y": y_field}

        # Auto-detect encoding from field metadata
        fields = operation_result.get("fields", [])
        if not fields:
            return None

        category_fields = [f for f in fields if f.get("role") in ("category", "dimension")]
        # Exclude identifiers from measure candidates
        measure_fields = [
            f for f in fields
            if f.get("role") == "measure" and f.get("role") != "identifier"
        ]
        time_fields = [f for f in fields if f.get("role") == "time"]

        if chart_type == "pie":
            # Pie needs: category for name, measure for value
            if category_fields and measure_fields:
                return {
                    "category": category_fields[0]["id"],
                    "value": measure_fields[0]["id"],
                }
        elif chart_type == "scatter":
            # Scatter needs: two measure fields
            if len(measure_fields) >= 2:
                return {
                    "x": measure_fields[0]["id"],
                    "y": measure_fields[1]["id"],
                }
        elif chart_type == "line":
            # Line: time/dimension x-axis, measure y-axis
            x = time_fields[0] if time_fields else (category_fields[0] if category_fields else None)
            y = measure_fields[0] if measure_fields else None
            if x and y:
                return {
                    "x": x["id"],
                    "y": y["id"],
                }
        else:
            # Bar, histogram, or auto: category x-axis, measure y-axis
            x = category_fields[0] if category_fields else (time_fields[0] if time_fields else None)
            y = measure_fields[0] if measure_fields else None
            if x and y:
                return {
                    "x": x["id"],
                    "y": y["id"],
                }

        # Fallback: first string-like field as x, first numeric (non-identifier) as y
        string_fields = [f for f in fields if f.get("data_type") == "string"]
        numeric_fields = [
            f for f in fields
            if f.get("data_type") in ("integer", "float") and f.get("role") != "identifier"
        ]
        if string_fields and numeric_fields:
            return {
                "x": string_fields[0]["id"],
                "y": numeric_fields[0]["id"],
            }

        return None
