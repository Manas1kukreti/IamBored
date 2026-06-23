"""Tests for pie chart aggregation architecture.

Verifies that:
1. Explicit pie chart intent remains a pie chart (not downgraded)
2. Compiler inserts calculation_agent step for pie charts with group_by
3. Identifier fields are excluded from measure selection
4. Aggregated data passes pie chart validation
5. Raw unaggregated row-level data fails pie chart validation
6. Visualization agent performs no calculation (zero-calculation principle)
7. ChartSpec carries group_by/aggregation/measure/output_field fields
"""

import os
import sys
import uuid

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from finflow_agent.operations.schemas import ChartSpec, VisualizationOperationPlan
from finflow_agent.planning.canonical_intent import (
    CanonicalIntent,
    VisualizeIntent,
)
from finflow_agent.planning.compiler import (
    compile_canonical_intent,
    compile_intent_to_plan,
    CANONICAL_OUTPUT_KEYS,
)
from finflow_agent.planning.intent_schema import PlanIntent
from finflow_agent.execution.visualization.validators import (
    PieChartValidator,
    ValidationResult,
)
from finflow_agent.execution.visualization.operation_result_reader import (
    OperationResultReader,
)
from finflow_agent.execution.visualization.spec import FieldMetadata
from finflow_agent.agents.visualization_agent import VisualizationAgent


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def enable_visualization(monkeypatch):
    """Enable visualization for all tests in this module."""
    monkeypatch.setattr(
        "finflow_agent.planning.compiler.get_enable_visualization", lambda: True
    )


def _make_plan_intent_with_pie(group_by=None, aggregation=None, measure=None, output_field=None):
    """Create a PlanIntent with a pie chart visualization plan."""
    chart = ChartSpec(
        type="pie",
        x="auto",
        y="auto",
        title="Test Pie Chart",
        group_by=group_by,
        measure=measure,
        aggregation=aggregation,
        output_field=output_field,
    )
    return PlanIntent(
        needs_visualization=True,
        visualization_plan=VisualizationOperationPlan(charts=[chart]),
    )


def _make_canonical_intent_with_pie(
    chart_type="pie",
    group_by=None,
    aggregation=None,
    measure=None,
    output_field=None,
    source_columns=None,
):
    """Create a CanonicalIntent with a VisualizeIntent action."""
    return CanonicalIntent(
        schema_version="2.0",
        resolution_status="resolved",
        output_format="xlsx",
        dataframe_profile={
            "source_columns": source_columns or ["gender", "age", "customer_id", "income"],
        },
        actions=[
            VisualizeIntent(
                kind="visualize",
                chart_type=chart_type,
                group_by=group_by,
                aggregation=aggregation,
                measure=measure,
                output_field=output_field,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Test 1: Explicit pie chart intent stays as pie
# ---------------------------------------------------------------------------


class TestExplicitPieRemainsPie:
    """Verify pie chart type is preserved through compilation."""

    def test_chart_type_preserved_in_plan(self):
        intent = _make_plan_intent_with_pie(group_by=["gender"], aggregation="count")
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        viz_step = next(s for s in plan.steps if s.agent == "visualization_agent")
        charts = viz_step.params["plan"]["charts"]
        assert charts[0]["type"] == "pie"

    def test_canonical_pie_intent_produces_pie_chart(self):
        intent = _make_canonical_intent_with_pie(
            chart_type="pie",
            group_by=["gender"],
            aggregation="count",
        )
        plan = compile_canonical_intent(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            artifact_prefix="test",
        )
        viz_step = next(s for s in plan.steps if s.agent == "visualization_agent")
        charts = viz_step.params["plan"]["charts"]
        assert charts[0]["type"] == "pie"


# ---------------------------------------------------------------------------
# Test 2: Compiler inserts calculation_agent step for pie with group_by
# ---------------------------------------------------------------------------


class TestCompilerInsertsCalculationStep:
    """Verify the compiler inserts a calculation_agent step when group_by is set."""

    def test_calc_step_inserted_before_visualization(self):
        intent = _make_plan_intent_with_pie(
            group_by=["gender"], aggregation="count", output_field="record_count"
        )
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        agents = [s.agent for s in plan.steps]
        assert "calculation_agent" in agents
        calc_idx = agents.index("calculation_agent")
        viz_idx = agents.index("visualization_agent")
        assert calc_idx < viz_idx, "calculation_agent must precede visualization_agent"

    def test_calc_step_uses_group_count_operation(self):
        intent = _make_plan_intent_with_pie(
            group_by=["gender"], aggregation="count", output_field="gender_count"
        )
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        calc_step = next(s for s in plan.steps if s.agent == "calculation_agent")
        ops = calc_step.params["operations"]
        assert len(ops) == 1
        assert ops[0]["type"] == "group_count"
        assert ops[0]["group_by"] == ["gender"]
        assert ops[0]["output_column"] == "gender_count"

    def test_calc_step_uses_group_sum_for_sum_aggregation(self):
        intent = _make_plan_intent_with_pie(
            group_by=["category"],
            aggregation="sum",
            measure="revenue",
            output_field="total_revenue",
        )
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        calc_step = next(s for s in plan.steps if s.agent == "calculation_agent")
        ops = calc_step.params["operations"]
        assert ops[0]["type"] == "group_sum"
        assert ops[0]["column"] == "revenue"
        assert ops[0]["output_column"] == "total_revenue"

    def test_calc_step_uses_group_mean_for_mean_aggregation(self):
        intent = _make_plan_intent_with_pie(
            group_by=["region"],
            aggregation="mean",
            measure="salary",
            output_field="avg_salary",
        )
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        calc_step = next(s for s in plan.steps if s.agent == "calculation_agent")
        ops = calc_step.params["operations"]
        assert ops[0]["type"] == "group_mean"
        assert ops[0]["column"] == "salary"

    def test_visualization_depends_on_calc_step(self):
        intent = _make_plan_intent_with_pie(
            group_by=["gender"], aggregation="count"
        )
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        viz_step = next(s for s in plan.steps if s.agent == "visualization_agent")
        assert "calc_viz" in viz_step.depends_on
        assert viz_step.input_from == ["df_calc_viz"]

    def test_no_calc_step_when_no_group_by(self):
        """Without group_by, no calculation step should be inserted."""
        intent = _make_plan_intent_with_pie()
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        agents = [s.agent for s in plan.steps]
        assert "calculation_agent" not in agents

    def test_calc_step_output_key_is_canonical(self):
        intent = _make_plan_intent_with_pie(
            group_by=["gender"], aggregation="count"
        )
        plan = compile_intent_to_plan(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            file_prefix="test",
        )
        calc_step = next(s for s in plan.steps if s.agent == "calculation_agent")
        assert calc_step.output_key in CANONICAL_OUTPUT_KEYS


# ---------------------------------------------------------------------------
# Test 3: Identifier fields excluded from measure selection
# ---------------------------------------------------------------------------


class TestIdentifierFieldsExcluded:
    """Verify identifier columns are not selected as measures."""

    def test_customer_id_gets_identifier_role(self):
        """Columns ending with _id should be classified as identifier."""
        df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "gender": ["M", "F", "M"],
            "income": [50000, 60000, 70000],
        })
        agent = VisualizationAgent()
        result = agent._build_operation_result({"input_dataframe": df})
        fields = result["fields"]

        id_field = next(f for f in fields if f["id"] == "customer_id")
        assert id_field["role"] == "identifier"

    def test_id_column_gets_identifier_role(self):
        """Column named 'id' should be classified as identifier."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "category": ["A", "B", "C"],
            "value": [10.0, 20.0, 30.0],
        })
        agent = VisualizationAgent()
        result = agent._build_operation_result({"input_dataframe": df})
        fields = result["fields"]

        id_field = next(f for f in fields if f["id"] == "id")
        assert id_field["role"] == "identifier"

    def test_order_number_gets_identifier_role(self):
        """Columns ending with _number should be identifier."""
        df = pd.DataFrame({
            "order_number": [1001, 1002, 1003],
            "product": ["A", "B", "A"],
            "amount": [99.0, 149.0, 199.0],
        })
        agent = VisualizationAgent()
        result = agent._build_operation_result({"input_dataframe": df})
        fields = result["fields"]

        num_field = next(f for f in fields if f["id"] == "order_number")
        assert num_field["role"] == "identifier"

    def test_encoding_hints_skip_identifiers(self):
        """_build_encoding_hints should not pick identifier fields as measures."""
        operation_result = {
            "fields": [
                {"id": "customer_id", "label": "customer_id", "data_type": "integer", "role": "identifier", "unit": None, "aggregation": None},
                {"id": "gender", "label": "gender", "data_type": "string", "role": "category", "unit": None, "aggregation": None},
                {"id": "count", "label": "Count", "data_type": "integer", "role": "measure", "unit": None, "aggregation": "count"},
            ],
            "rows": [
                {"customer_id": 1, "gender": "M", "count": 500},
                {"customer_id": 2, "gender": "F", "count": 500},
            ],
        }
        hints = VisualizationAgent._build_encoding_hints(
            {"type": "pie", "x": "auto", "y": "auto", "title": "Test"},
            "pie",
            operation_result,
        )
        # Should select gender as category and count as value, NOT customer_id
        assert hints is not None
        assert hints.get("value") == "count"
        assert hints.get("category") == "gender"


# ---------------------------------------------------------------------------
# Test 4: Aggregated count passes pie validation
# ---------------------------------------------------------------------------


class TestAggregatedDataPassesPieValidation:
    """Aggregated data with proper aggregation metadata should pass validation."""

    def test_aggregated_count_passes(self):
        """Pre-aggregated data with aggregation='count' should be valid."""
        operation_result = {
            "fields": [
                {"id": "gender", "label": "Gender", "data_type": "string", "role": "category", "unit": None, "aggregation": None},
                {"id": "record_count", "label": "Count", "data_type": "integer", "role": "measure", "unit": None, "aggregation": "count"},
            ],
            "rows": [
                {"gender": "Male", "record_count": 600},
                {"gender": "Female", "record_count": 400},
            ],
        }
        reader = OperationResultReader(operation_result)
        encoding = {"category": "gender", "value": "record_count"}
        validator = PieChartValidator(require_aggregation=True)
        result = validator.validate(reader, encoding)
        assert result.valid is True

    def test_aggregated_sum_passes(self):
        """Pre-aggregated data with aggregation='sum' should be valid."""
        operation_result = {
            "fields": [
                {"id": "region", "label": "Region", "data_type": "string", "role": "category", "unit": None, "aggregation": None},
                {"id": "total_revenue", "label": "Revenue", "data_type": "float", "role": "measure", "unit": "USD", "aggregation": "sum"},
            ],
            "rows": [
                {"region": "North", "total_revenue": 100000.0},
                {"region": "South", "total_revenue": 80000.0},
                {"region": "East", "total_revenue": 120000.0},
            ],
        }
        reader = OperationResultReader(operation_result)
        encoding = {"category": "region", "value": "total_revenue"}
        validator = PieChartValidator(require_aggregation=True)
        result = validator.validate(reader, encoding)
        assert result.valid is True


# ---------------------------------------------------------------------------
# Test 5: Raw unaggregated data fails pie validation
# ---------------------------------------------------------------------------


class TestRawDataFailsPieValidation:
    """Raw row-level data without aggregation should fail pie validation."""

    def test_raw_integer_without_aggregation_fails(self):
        """A numeric field without aggregation metadata should fail."""
        operation_result = {
            "fields": [
                {"id": "gender", "label": "Gender", "data_type": "string", "role": "category", "unit": None, "aggregation": None},
                {"id": "income", "label": "Income", "data_type": "integer", "role": "measure", "unit": None, "aggregation": None},
            ],
            "rows": [
                {"gender": "Male", "income": 50000},
                {"gender": "Female", "income": 60000},
                {"gender": "Male", "income": 55000},
            ],
        }
        reader = OperationResultReader(operation_result)
        encoding = {"category": "gender", "value": "income"}
        validator = PieChartValidator(require_aggregation=True)
        result = validator.validate(reader, encoding)
        assert result.valid is False
        assert result.reason_code == "pie_incompatible_aggregation_required"

    def test_validation_passes_when_aggregation_check_disabled(self):
        """With require_aggregation=False, raw data passes (for backwards compat)."""
        operation_result = {
            "fields": [
                {"id": "gender", "label": "Gender", "data_type": "string", "role": "category", "unit": None, "aggregation": None},
                {"id": "income", "label": "Income", "data_type": "integer", "role": "measure", "unit": None, "aggregation": None},
            ],
            "rows": [
                {"gender": "Male", "income": 50000},
                {"gender": "Female", "income": 60000},
            ],
        }
        reader = OperationResultReader(operation_result)
        encoding = {"category": "gender", "value": "income"}
        validator = PieChartValidator(require_aggregation=False)
        result = validator.validate(reader, encoding)
        assert result.valid is True


# ---------------------------------------------------------------------------
# Test 6: Visualization agent performs no calculation
# ---------------------------------------------------------------------------


class TestVisualizationNoCalculation:
    """Verify the visualization agent does not perform data aggregation."""

    def test_no_prepare_pie_data_method(self):
        """The _prepare_pie_data method should have been removed."""
        assert not hasattr(VisualizationAgent, "_prepare_pie_data")

    def test_raw_data_passed_through_unchanged(self):
        """The visualization agent should pass input DataFrame through unchanged."""
        df = pd.DataFrame({
            "gender": ["M", "F", "M", "F"],
            "count": [100, 200, 150, 250],
        })
        agent = VisualizationAgent()
        result = agent.execute(
            params={"plan": {"charts": []}},
            input_data={"input_dataframe": df},
        )
        # With no charts, it should return the df unchanged
        assert result.status == "success"
        pd.testing.assert_frame_equal(result.data, df)


# ---------------------------------------------------------------------------
# Test 7: ChartSpec schema carries new fields
# ---------------------------------------------------------------------------


class TestChartSpecSchema:
    """Verify ChartSpec can carry aggregation configuration."""

    def test_chart_spec_with_group_by(self):
        spec = ChartSpec(
            type="pie",
            x="auto",
            y="auto",
            title="Gender Distribution",
            group_by=["gender"],
            aggregation="count",
            output_field="record_count",
        )
        assert spec.group_by == ["gender"]
        assert spec.aggregation == "count"
        assert spec.output_field == "record_count"
        assert spec.measure is None

    def test_chart_spec_with_sum_aggregation(self):
        spec = ChartSpec(
            type="pie",
            x="auto",
            y="auto",
            title="Revenue by Region",
            group_by=["region"],
            aggregation="sum",
            measure="revenue",
            output_field="total_revenue",
        )
        assert spec.aggregation == "sum"
        assert spec.measure == "revenue"

    def test_chart_spec_serializes_new_fields(self):
        spec = ChartSpec(
            type="pie",
            x="auto",
            y="auto",
            title="Test",
            group_by=["status"],
            aggregation="mean",
            measure="salary",
            output_field="avg_salary",
        )
        dumped = spec.model_dump()
        assert dumped["group_by"] == ["status"]
        assert dumped["aggregation"] == "mean"
        assert dumped["measure"] == "salary"
        assert dumped["output_field"] == "avg_salary"

    def test_chart_spec_defaults_new_fields_to_none(self):
        spec = ChartSpec(
            type="bar",
            x="month",
            y="revenue",
            title="Monthly Revenue",
        )
        assert spec.group_by is None
        assert spec.aggregation is None
        assert spec.measure is None
        assert spec.output_field is None


# ---------------------------------------------------------------------------
# Test 8: Canonical intent pie chart defaults to count aggregation
# ---------------------------------------------------------------------------


class TestCanonicalIntentPieDefaults:
    """Verify canonical pie chart intent gets default count aggregation."""

    def test_pie_without_explicit_aggregation_gets_count(self):
        """A pie VisualizeIntent without aggregation should get count by default."""
        intent = _make_canonical_intent_with_pie(
            chart_type="pie",
            group_by=["gender"],
            # No aggregation specified
        )
        plan = compile_canonical_intent(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            artifact_prefix="test",
        )
        calc_step = next(
            (s for s in plan.steps if s.agent == "calculation_agent"), None
        )
        assert calc_step is not None
        ops = calc_step.params["operations"]
        assert ops[0]["type"] == "group_count"

    def test_pie_with_explicit_sum_uses_sum(self):
        """A pie VisualizeIntent with explicit sum should use group_sum."""
        intent = _make_canonical_intent_with_pie(
            chart_type="pie",
            group_by=["region"],
            aggregation="sum",
            measure="revenue",
        )
        plan = compile_canonical_intent(
            intent,
            resolved_file_path="test.csv",
            file_type="csv",
            output_dir="outputs",
            artifact_prefix="test",
        )
        calc_step = next(
            (s for s in plan.steps if s.agent == "calculation_agent"), None
        )
        assert calc_step is not None
        ops = calc_step.params["operations"]
        assert ops[0]["type"] == "group_sum"
        assert ops[0]["column"] == "revenue"


# ---------------------------------------------------------------------------
# Test 9: VisualizeIntent schema carries new fields
# ---------------------------------------------------------------------------


class TestVisualizeIntentSchema:
    """Verify VisualizeIntent model accepts new fields."""

    def test_visualize_intent_with_group_by(self):
        vi = VisualizeIntent(
            kind="visualize",
            chart_type="pie",
            group_by=["gender"],
            aggregation="count",
            output_field="gender_count",
        )
        assert vi.group_by == ["gender"]
        assert vi.aggregation == "count"
        assert vi.output_field == "gender_count"

    def test_visualize_intent_defaults_none(self):
        vi = VisualizeIntent(kind="visualize", chart_type="bar")
        assert vi.group_by is None
        assert vi.aggregation is None
        assert vi.measure is None
        assert vi.output_field is None

    def test_visualize_intent_extra_fields_ignored(self):
        """Extra fields should be ignored (model_config extra='ignore')."""
        vi = VisualizeIntent(
            kind="visualize",
            chart_type="pie",
            group_by=["gender"],
            unknown_field="should be ignored",
        )
        assert vi.group_by == ["gender"]


# ---------------------------------------------------------------------------
# Test 10: df_calc_viz is a canonical output key
# ---------------------------------------------------------------------------


class TestCanonicalOutputKeys:
    """Verify df_calc_viz is now in the canonical output keys set."""

    def test_df_calc_viz_is_canonical(self):
        assert "df_calc_viz" in CANONICAL_OUTPUT_KEYS
