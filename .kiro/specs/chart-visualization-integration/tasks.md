# Implementation Plan: Chart Visualization Integration

## Overview

This plan implements FinFlow's optional chart visualization layer across the agent-framework (Python), backend (Python/FastAPI), and frontend (React/Recharts). Tasks proceed from core data interfaces through backend logic, persistence, API integration, and finally frontend rendering — each step building on previous outputs.

## Tasks

- [x] 1. Core data models and interfaces
  - [x] 1.1 Create VisualizationSpec model and FieldMetadata dataclass
    - Create `finflow_agent/execution/visualization/spec.py`
    - Define `VisualizationSpec` Pydantic model with schema_version, visualization_id, operation_id, source_result_id, status, chart_type, title (max 200 chars), encoding, data, options, warnings (max 20), error
    - Define `FieldMetadata` dataclass with id, label, data_type, role, unit, aggregation
    - Define `DataShape` enum (time_series, categorical_series, histogram_bins, scatter_points, scalar)
    - _Requirements: 9.1, 9.2, 14.1_

  - [x] 1.2 Create OperationResultReader adapter
    - Create `finflow_agent/execution/visualization/operation_result_reader.py`
    - Implement `get_fields()` returning list of FieldMetadata
    - Implement `get_rows()` returning list of dicts
    - Implement `get_data_shape()` classifying fields into DataShape enum
    - Implement `_validate()` ensuring at least one field with non-null id, data_type, and role
    - Raise validation error if field metadata is missing/invalid
    - Return empty row list with valid data_shape when zero data rows exist
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [x] 1.3 Create TriggerDetector for visualization trigger language
    - Create `finflow_agent/planning/trigger_detector.py`
    - Define TRIGGER_TERMS set (chart, graph, plot, visualize, visualise, visualization, visualisation)
    - Define TRIGGER_PHRASES list (pie chart, bar chart, line chart, scatter plot, histogram, "as a chart", "as a graph")
    - Define ANALYTICAL_ONLY_TERMS set (trend, distribution, compare, breakdown, summary, overview, analysis)
    - Implement `detect()` with case-insensitive, whole-word boundary matching
    - Return `TriggerResult` with triggered flag, matched_term, chart_type_hint
    - Ensure substrings within larger words do not trigger (e.g., "uncharted")
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.4 Write property tests for TriggerDetector
    - **Property 1: Trigger Language Detection** — For any prompt containing a Trigger_Language term as whole-word or exact phrase, detect() returns triggered=True
    - **Property 2: No False Trigger from Analytical-Only Prompts** — For prompts composed exclusively of analytical terms, detect() returns triggered=False
    - **Property 3: Whole-Word Boundary Matching** — For prompts where trigger terms appear only as substrings within larger words, detect() returns triggered=False
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

  - [ ]* 1.5 Write property test for OperationResultReader data shape classification
    - **Property 13: OperationResultReader Data Shape Classification** — For any valid OperationResult, data_shape is classified correctly based on field roles
    - **Validates: Requirements 14.1**

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Chart validators and visualization executor
  - [x] 3.1 Implement chart compatibility validators
    - Create `finflow_agent/execution/visualization/validators.py`
    - Implement `LineChartValidator`: x-axis must be time/dimension role with ≥2 distinct x values
    - Implement `BarChartValidator`: at least one category/dimension + one numeric field, ≥1 row
    - Implement `PieChartValidator`: exactly 1 category + 1 numeric, all values ≥0, ≤max categories (default 12)
    - Implement `ScatterChartValidator`: 2 numeric fields, ≥2 rows with non-null values in both
    - Implement `HistogramChartValidator`: at least one measure field with frequencies, ≥1 bin row
    - Exclude rows with null values in required fields from minimum-row-count checks
    - Return `ValidationResult` with valid flag, reason_code, and error_message
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 3.2 Implement VisualizationExecutor
    - Create `finflow_agent/execution/visualization/executor.py`
    - Normalize chart_type: null/empty/missing → "auto"
    - Validate chart_type against supported set {"auto", "bar", "line", "pie", "scatter", "histogram"} (case-sensitive)
    - Read via OperationResultReader adapter
    - Validate field references in encoding (existence, data_type, role)
    - Run chart compatibility validation
    - Implement auto chart type selection: time_series→line, categorical_series→bar, histogram_bins→histogram, scatter_points→scatter, no match→bar; never auto-select pie
    - Build VisualizationSpec with mapped data (zero-calculation: copy rows verbatim)
    - Generate title from chart_type + primary measure field label (max 200 chars)
    - Set status "unsupported" with appropriate reason_code on validation failure
    - Set status "failed" on source data issues or unhandled exceptions
    - Error messages: plain-language, 1-500 chars, no stack traces
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 7.1, 7.2, 7.3, 7.4, 7.5, 9.3, 9.4, 9.5, 15.1, 15.2, 15.3, 15.4, 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 18.1, 18.2, 18.4_

  - [ ]* 3.3 Write property tests for chart compatibility and executor
    - **Property 4: Zero-Calculation Invariant** — Every value in VisualizationSpec data exists verbatim in source OperationResult rows
    - **Property 5: Source Immutability** — OperationResult values/rows/metadata unchanged after executor runs
    - **Property 8: Auto Chart Type Selection Determinism** — Auto selection follows data_shape mapping, never selects pie, records resolved type
    - **Property 9: Chart Compatibility Validation** — Validators correctly accept/reject per chart-specific rules
    - **Property 10: VisualizationSpec Structural Contract** — Spec structure matches contract for all status values
    - **Property 11: Chart Type Acceptance** — Executor accepts only supported set, treats null/empty as auto
    - **Property 12: Field Validation Correctness** — Field validation checks existence, data_type, and role
    - **Property 16: Error Message Format** — Error field is 1-500 chars plain-language without internal codes
    - **Validates: Requirements 3.1, 3.2, 3.4, 4.1, 4.2, 7.1-7.4, 8.1-8.7, 9.1-9.5, 15.1-15.4, 17.1-17.5, 18.1, 18.2, 18.4**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Execution engine integration
  - [x] 5.1 Extend execution engine with visualization DAG node support
    - Modify the execution engine to handle `kind="visualization"` DAG nodes
    - Create visualization DAG_Node with unique step_id, depends_on referencing source calc step, initial status "pending"
    - Resolve depends_on by confirming source step completed with status "success"
    - Set node status "failed" with error if dependency unresolvable
    - Permit concurrent execution of visualization nodes whose dependencies are satisfied
    - Add MAX_VISUALIZATIONS_PER_JOB = 20 constant
    - Reject plans with >20 visualization nodes before execution
    - Reject plans where visualization depends_on >1 calc step
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 5.1, 5.5, 16.1, 16.4_

  - [x] 5.2 Implement failure isolation and job status logic
    - Ensure calc step status remains "success" when viz node fails/times out
    - Set job status "completed_with_warnings" when all calc succeed but ≥1 viz fails
    - Set job status "failed" when any calc step fails regardless of viz outcomes
    - Set failed viz node VisualizationSpec status to "failed" with error (≤500 chars)
    - Continue executing remaining DAG nodes after viz failure
    - Produce one VisualizationSpec per viz node regardless of other nodes' outcomes
    - Return specs ordered by topological position in execution plan
    - Implement 30-second execution timeout for visualization nodes
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 5.3, 5.4_

  - [x] 5.3 Integrate TriggerDetector with Intent Classifier and Plan Compiler
    - Wire TriggerDetector into the intent classification pipeline
    - When trigger detected, produce VisualizeIntent action in canonical intent
    - Plan Compiler creates calc + viz DAG nodes from VisualizeIntent
    - Ensure jobs without visualization intent produce empty visualizations array
    - _Requirements: 1.1, 1.4, 2.1, 5.2, 13.1, 13.2_

  - [ ]* 5.4 Write property tests for execution engine visualization logic
    - **Property 6: Failure Isolation — Calculation Status Preserved** — Calc step status remains "success" when dependent viz fails
    - **Property 7: Job Status Rules** — Job status follows defined rules for calc+viz outcome combinations
    - **Property 14: Visualization Count Limit** — Plans with 0-20 viz nodes accepted, >20 rejected
    - **Property 15: Per-Node Isolation and Ordering** — Each viz node produces a spec regardless of others, ordered topologically
    - **Validates: Requirements 2.1-2.4, 5.1-5.5, 6.1-6.4**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Database persistence
  - [x] 7.1 Create Alembic migration for job_visualizations table
    - Create a reversible Alembic migration with upgrade and downgrade functions
    - Create `job_visualizations` table: id (UUID PK), job_id (FK→submissions CASCADE), operation_id (VARCHAR 255 NOT NULL), spec (JSONB NOT NULL), data (JSONB nullable), created_at (TIMESTAMPTZ NOT NULL server default now)
    - Add unique constraint on (job_id, operation_id) named "uq_job_viz_job_op"
    - Migration must be additive-only (no dropping/altering existing tables)
    - _Requirements: 10.1, 10.2, 10.4, 13.4_

  - [x] 7.2 Create JobVisualization SQLAlchemy model and repository
    - Create `backend/app/models/visualization.py` with JobVisualization model
    - Implement upsert logic: on unique constraint conflict, update spec, data, created_at
    - Implement query by job_id returning ordered visualization specs
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ]* 7.3 Write unit tests for database persistence
    - Test insert and query round-trip
    - Test upsert on conflict updates spec/data/created_at
    - Test cascade delete when parent submission is removed
    - _Requirements: 10.1, 10.2, 10.3_

- [x] 8. API integration
  - [x] 8.1 Extend job-detail API endpoint with visualizations
    - Add `VisualizationSpecRead` Pydantic schema to `backend/app/schemas/`
    - Add `visualizations: list[VisualizationSpecRead]` field to `JobDetailRead` with default empty list
    - Query `job_visualizations` table in the job-detail endpoint handler
    - Return `visualizations: []` for jobs with no visualizations
    - Return `visualizations: []` with warning if DB query fails (do not fail request)
    - Ensure existing response fields unchanged for pre-viz jobs
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 13.2, 13.3_

  - [ ]* 8.2 Write unit tests for API integration
    - Test job-detail response includes visualizations array
    - Test empty visualizations for pre-viz jobs
    - Test backward compatibility of existing response fields
    - Test graceful handling of DB query failure
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Frontend visualization components
  - [x] 10.1 Create VisualizationRenderer dispatcher component
    - Create `frontend/src/components/visualization/VisualizationRenderer.jsx`
    - Dispatch to correct subcomponent based on spec.chart_type (line→LineVisualization, bar→BarVisualization, pie→PieVisualization, scatter→ScatterVisualization, histogram→HistogramVisualization)
    - Handle status "unsupported": display error in info-state container
    - Handle status "failed": display error in error-state container
    - Handle unknown chart_type: display "chart type not supported" message
    - Create `frontend/src/components/visualization/UnsupportedState.jsx` for error/unsupported display
    - Create `frontend/src/components/visualization/index.js` barrel export
    - Follow FinFlow dark/glassmorphism theme with ff-* class prefixes
    - _Requirements: 12.1, 12.3, 12.4, 12.5, 12.6_

  - [x] 10.2 Implement LineVisualization and BarVisualization components
    - Create `frontend/src/components/visualization/LineVisualization.jsx`
    - Create `frontend/src/components/visualization/BarVisualization.jsx`
    - Use Recharts LineChart and BarChart respectively
    - Bind encoding field IDs as Recharts dataKey values
    - Use field labels for axis labels, legend entries, tooltip headers
    - Apply ff-* class prefixes for theming
    - _Requirements: 12.1, 12.2, 12.5_

  - [x] 10.3 Implement PieVisualization, ScatterVisualization, and HistogramVisualization components
    - Create `frontend/src/components/visualization/PieVisualization.jsx`
    - Create `frontend/src/components/visualization/ScatterVisualization.jsx`
    - Create `frontend/src/components/visualization/HistogramVisualization.jsx` (BarChart in histogram mode)
    - Use encoding field IDs as Recharts dataKey values
    - Use field labels for labels and tooltips
    - Apply ff-* class prefixes for theming
    - _Requirements: 12.1, 12.2, 12.5_

  - [x] 10.4 Integrate VisualizationRenderer into job results view
    - Import VisualizationRenderer in the job results page
    - Map over `visualizations` array from job-detail response
    - Render a VisualizationRenderer for each spec
    - Handle empty visualizations array gracefully (render nothing)
    - _Requirements: 12.1, 13.2_

  - [ ]* 10.5 Write frontend tests for visualization components
    - **Property 17: Frontend Dispatch Correctness** — VisualizationRenderer dispatches to correct subcomponent for each chart_type and uses encoding field IDs as dataKey
    - Test each chart subcomponent renders with valid spec data
    - Test UnsupportedState renders for status "unsupported" and "failed"
    - Test ff-* class prefixes are applied
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6**

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend uses Python (Pydantic, SQLAlchemy, Alembic); frontend uses React with Recharts
- The Visualization_Executor performs zero calculations — only structural mapping

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["1.4", "1.5", "3.1"] },
    { "id": 3, "tasks": ["3.2"] },
    { "id": 4, "tasks": ["3.3", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3"] },
    { "id": 6, "tasks": ["5.4", "7.1"] },
    { "id": 7, "tasks": ["7.2", "8.1"] },
    { "id": 8, "tasks": ["7.3", "8.2"] },
    { "id": 9, "tasks": ["10.1"] },
    { "id": 10, "tasks": ["10.2", "10.3"] },
    { "id": 11, "tasks": ["10.4"] },
    { "id": 12, "tasks": ["10.5"] }
  ]
}
```
