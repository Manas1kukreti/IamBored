# Requirements Document

## Introduction

This feature enables FinFlow's optional chart visualization capability. Charts are generated only when the user explicitly requests a visualization through specific trigger language. The visualization layer consumes normalized operation results produced by the operation agent without duplicating any calculations. It persists a versioned VisualizationSpec and renders charts via React/Recharts on the frontend.

## Glossary

- **Visualization_Executor**: The backend component that receives a normalized OperationResult and produces a VisualizationSpec for persistence and rendering.
- **OperationResult**: The normalized data payload produced by the operation agent containing field metadata and rows.
- **OperationResultReader**: An adapter interface that decouples the Visualization_Executor from the exact shape of the OperationResult payload.
- **VisualizationSpec**: A versioned JSON contract (schema_version, visualization_id, operation_id, source_result_id, status, chart_type, title, encoding, data, options, warnings, error) shared between backend persistence and frontend rendering.
- **Execution_Engine**: The component that walks the ExecutionPlan topologically and dispatches each PlanStep to the appropriate agent or executor.
- **Intent_Classifier**: The component that parses user prompts into canonical intents including VisualizeIntent.
- **VisualizationRenderer**: The React component that receives a VisualizationSpec and dispatches rendering to the appropriate chart subcomponent.
- **Field_Metadata**: Structured metadata for each field in an OperationResult including id (stable key), label (display name), data_type (string/integer/float/datetime), role (category/measure/time/dimension), unit, and aggregation.
- **DAG_Node**: A discrete operation step in the execution plan with its own step_id, kind, depends_on, and status.
- **Trigger_Language**: The explicit set of words and phrases that activate visualization: chart, graph, plot, visualize, visualise, visualization, visualisation, pie chart, bar chart, line chart, scatter plot, histogram, "as a chart", "as a graph".

## Requirements

### Requirement 1: Explicit Visualization Triggering

**User Story:** As a FinFlow user, I want charts to appear only when I explicitly request a visualization, so that routine data operations are not cluttered with unwanted charts.

#### Acceptance Criteria

1. WHEN the user prompt contains any Trigger_Language term (chart, graph, plot, visualize, visualise, visualization, visualisation, pie chart, bar chart, line chart, scatter plot, histogram, "as a chart", "as a graph") as a whole-word match or exact multi-word phrase match, THE Intent_Classifier SHALL produce a VisualizeIntent action in the canonical intent.
2. WHEN the user prompt contains only analytical terms (trend, distribution, compare, breakdown, summary, overview, analysis) without any Trigger_Language term, THE Intent_Classifier SHALL NOT produce a VisualizeIntent action.
3. THE Intent_Classifier SHALL perform Trigger_Language matching using case-insensitive, whole-word boundary comparison, such that substrings within larger words (e.g., "chart" in "uncharted") do not constitute a match.
4. WHEN the user prompt contains both a Trigger_Language term and analytical terms, THE Intent_Classifier SHALL produce a VisualizeIntent action (Trigger_Language presence takes precedence).
5. WHEN the user prompt contains multi-word Trigger_Language phrases ("as a chart", "as a graph", "pie chart", "bar chart", "line chart", "scatter plot"), THE Intent_Classifier SHALL match these as exact contiguous word sequences only.

### Requirement 2: Visualization as DAG Node

**User Story:** As a system architect, I want each visualization to be an independent operation in the execution plan DAG, so that visualization lifecycle is managed separately from calculation.

#### Acceptance Criteria

1. WHEN a VisualizeIntent is present in the canonical intent, THE Execution_Engine SHALL create a DAG_Node with kind="visualization", a unique step_id, depends_on referencing the source calculation step_id identified by the VisualizeIntent's associated operation_id, and an initial status of "pending".
2. THE Execution_Engine SHALL resolve the depends_on reference before executing the visualization DAG_Node by confirming that the referenced source step has completed with status "success" and its OperationResult is retrievable from PipelineState.
3. IF the depends_on reference cannot be resolved because the source calculation step does not exist or has status "failed", THEN THE Execution_Engine SHALL set the visualization DAG_Node status to "failed" with an error indicating the unresolvable dependency.
4. WHEN multiple visualization operations exist in a single job, THE Execution_Engine SHALL create one DAG_Node per visualization operation, each with its own step_id, depends_on, and status, and SHALL permit concurrent execution of visualization nodes whose respective dependencies are satisfied.

### Requirement 3: Zero Calculation in Visualization

**User Story:** As a data engineer, I want the visualization layer to perform no business calculations, so that data integrity is maintained and logic is not duplicated.

#### Acceptance Criteria

1. THE Visualization_Executor SHALL consume the OperationResult rows and field metadata without performing grouping, summing, averaging, percentage calculation, histogram binning, top-N filtering, or any row mutation.
2. THE Visualization_Executor SHALL use field values from the OperationResult exactly as provided without rounding, truncating, formatting, or transforming values of any data type (numeric, string, or datetime).
3. WHEN the OperationResult does not satisfy the chart compatibility validation rules for the requested chart type, THE Visualization_Executor SHALL set status to "unsupported" with a reason_code that identifies the specific missing or incompatible data element, rather than computing missing values.
4. THE Visualization_Executor SHALL limit its processing to structural mapping operations: selecting fields for axis assignment based on encoding, copying rows into the VisualizationSpec data array, and reading field metadata for validation — without deriving new values, inserting computed columns, or reordering rows by a calculated sort key.

### Requirement 4: Immutable Operation Results

**User Story:** As a data engineer, I want the visualization layer to treat operation results as read-only, so that downstream consumers always see the original calculation output.

#### Acceptance Criteria

1. THE Visualization_Executor SHALL treat the source OperationResult as immutable; after execution completes, the OperationResult values, row order, row count, and field metadata in PipelineState SHALL be identical to their state before the Visualization_Executor was invoked.
2. THE Visualization_Executor SHALL populate the VisualizationSpec data field by reading from the source OperationResult without writing to, removing from, or reordering entries in the source OperationResult payload stored in PipelineState.
3. IF the Visualization_Executor detects that the source OperationResult has been modified during its execution, THEN THE Visualization_Executor SHALL set the VisualizationSpec status to "failed" with reason_code "source_data_mutated" and SHALL NOT persist the VisualizationSpec data field.

### Requirement 5: Multiple Charts Per Job

**User Story:** As a FinFlow user, I want to request multiple charts in a single job, so that I can visualize different aspects of my data in one operation.

#### Acceptance Criteria

1. THE Execution_Engine SHALL support 0, 1, or N visualization DAG_Nodes within a single job execution plan, where N is at most 20.
2. WHEN a job contains no visualization operations, THE Execution_Engine SHALL produce an empty visualizations array in the job result.
3. WHEN a job contains N visualization operations (where N is between 1 and 20 inclusive), THE Execution_Engine SHALL execute each visualization DAG_Node with isolated lifecycle and status, producing one VisualizationSpec per DAG_Node regardless of whether other visualization DAG_Nodes succeed or fail.
4. THE Execution_Engine SHALL return VisualizationSpecs in the job result visualizations array ordered by the topological position of their corresponding DAG_Node in the execution plan.
5. IF a job requests more than 20 visualization operations, THEN THE Execution_Engine SHALL reject the execution plan with an error indicating the visualization limit has been exceeded.

### Requirement 6: Failure Isolation

**User Story:** As a FinFlow user, I want visualization failures to not affect my successful calculations, so that I always receive my data results even if charting fails.

#### Acceptance Criteria

1. IF a visualization DAG_Node throws an unhandled exception, exceeds a 30-second execution timeout, or returns status "unsupported", THEN THE Execution_Engine SHALL NOT change the status of the source calculation step from "success" to "failed".
2. IF one or more visualization DAG_Nodes fail while all calculation steps succeed, THEN THE Execution_Engine SHALL set the overall job status to "completed_with_warnings".
3. IF a visualization DAG_Node fails, THEN THE Execution_Engine SHALL set the corresponding VisualizationSpec status to "failed", populate the error field with a failure reason of no more than 500 characters, and continue executing all remaining DAG_Nodes in the plan.
4. IF one or more calculation steps fail regardless of visualization DAG_Node outcomes, THEN THE Execution_Engine SHALL set the overall job status to "failed".

### Requirement 7: Auto-Selection of Chart Type

**User Story:** As a FinFlow user, I want the system to pick an appropriate chart type when I request a generic visualization, so that I get a useful chart without specifying the exact type.

#### Acceptance Criteria

1. WHEN chart_type is "auto", THE Visualization_Executor SHALL select the chart type deterministically based on data_shape: time_series maps to "line", categorical_series maps to "bar", histogram_bins maps to "histogram", scatter_points maps to "scatter".
2. WHEN chart_type is "auto", THE Visualization_Executor SHALL NOT select "pie" as the automatic default chart type.
3. WHEN chart_type is "auto" and no deterministic rule matches the data_shape, THE Visualization_Executor SHALL default to "bar" chart type.
4. WHEN chart_type is "auto" and a chart type has been selected, THE Visualization_Executor SHALL record the resolved chart type (not "auto") in the VisualizationSpec chart_type field.
5. IF chart_type is "auto" and the auto-selected chart type fails chart compatibility validation, THEN THE Visualization_Executor SHALL set status to "unsupported" with a reason_code identifying the incompatibility rather than attempting a fallback selection.

### Requirement 8: Chart Compatibility Validation

**User Story:** As a FinFlow user, I want to be informed when my data is incompatible with the requested chart type, so that I understand why a chart cannot be rendered.

#### Acceptance Criteria

1. WHEN chart_type is "line", THE Visualization_Executor SHALL validate that the encoding contains an x-axis field with role "time" or role "dimension" and that at least 2 distinct x-axis values exist in the data rows.
2. WHEN chart_type is "bar", THE Visualization_Executor SHALL validate that the encoding contains at least one field with role "category" or "dimension" and at least one field with data_type "integer" or "float", and that at least 1 data row exists.
3. WHEN chart_type is "pie", THE Visualization_Executor SHALL validate that the encoding contains exactly 1 field with role "category" or "dimension" and exactly 1 field with data_type "integer" or "float", that all non-null values in the measure field are greater than or equal to zero, and that the number of distinct categories does not exceed the configured maximum (default 12, minimum configurable value 2, maximum configurable value 50).
4. WHEN chart_type is "scatter", THE Visualization_Executor SHALL validate that the encoding contains 2 fields each with data_type "integer" or "float" and that at least 2 data rows with non-null values in both fields exist.
5. WHEN chart_type is "histogram", THE Visualization_Executor SHALL validate that the OperationResult contains at least one field with role "measure" representing frequencies (data_type "integer" or "float") and that at least 1 row of bin data exists.
6. IF any compatibility validation rule defined in criteria 1–5 fails, THEN THE Visualization_Executor SHALL set status to "unsupported" with a reason_code that identifies the specific chart type and the failed condition, and SHALL leave the data array empty in the resulting VisualizationSpec.
7. IF the data rows contain null values in required measure or axis fields, THEN THE Visualization_Executor SHALL exclude those rows from the minimum-row-count checks but SHALL NOT treat null presence alone as a validation failure.

### Requirement 9: VisualizationSpec Contract

**User Story:** As a frontend developer, I want a stable, versioned contract for visualization data, so that the UI can reliably render charts from backend output.

#### Acceptance Criteria

1. THE Visualization_Executor SHALL produce a VisualizationSpec containing: schema_version (string), visualization_id (UUID), operation_id (string), source_result_id (string), status (one of "ready", "unsupported", "failed"), chart_type (string), title (string, maximum 200 characters), encoding (object mapping axis roles to field IDs), data (array of row objects), options (object for chart-specific settings), warnings (array of strings, maximum 20 entries), and error (string or null).
2. THE Visualization_Executor SHALL set schema_version to "1.0" for the initial release.
3. WHEN status is "ready", THE VisualizationSpec SHALL contain a data array with at least 1 row and an encoding object that maps at least one axis role to a field ID present in the source OperationResult field metadata.
4. WHEN status is "unsupported" or "failed", THE VisualizationSpec SHALL contain an error string describing the reason, set the data field to an empty array, and set the encoding field to an empty object.
5. THE Visualization_Executor SHALL generate the title field from the chart_type and the label of the primary measure field in the encoding, producing a non-empty string for all status values.

### Requirement 10: Backend Persistence

**User Story:** As a system architect, I want visualization specs persisted in their own database table, so that they can be queried and served independently of the main job result.

#### Acceptance Criteria

1. THE System SHALL store each VisualizationSpec in a `job_visualizations` table with columns: id (UUID primary key), job_id (foreign key to submissions with CASCADE on delete), operation_id (VARCHAR(255), not null), spec (JSONB, not null), data (JSONB, nullable), created_at (timestamp with time zone, not null, server-defaulting to now).
2. THE System SHALL enforce a unique constraint on (job_id, operation_id) in the `job_visualizations` table.
3. IF an insert into `job_visualizations` violates the unique constraint on (job_id, operation_id), THEN THE System SHALL update the existing row's spec, data, and created_at columns with the new values rather than raising an error.
4. THE System SHALL create the `job_visualizations` table via a reversible Alembic migration that includes both upgrade and downgrade functions.

### Requirement 11: API Integration

**User Story:** As a frontend developer, I want visualizations served through the existing job-detail endpoint, so that the UI can fetch charts alongside other job results without a separate API call.

#### Acceptance Criteria

1. WHEN the `/uploads/{id}/job-detail` endpoint is called, THE System SHALL include a `visualizations` array in the response where each element contains the full VisualizationSpec fields: schema_version, visualization_id, operation_id, source_result_id, status, chart_type, title, encoding, data, options, warnings, and error.
2. WHEN a job has no associated visualizations, THE System SHALL return `visualizations` as an empty array (`[]`).
3. THE System SHALL NOT remove, rename, or change the type of any existing fields in the job-detail response for jobs created before visualization support was added; those jobs SHALL return `visualizations` as an empty array.
4. IF the retrieval of visualization data from the `job_visualizations` table fails, THEN THE System SHALL return `visualizations` as an empty array and include a warning in the response rather than failing the entire job-detail request.

### Requirement 12: Recharts Frontend Rendering

**User Story:** As a FinFlow user, I want charts rendered in the job results UI using Recharts, so that I can see visual representations of my data analysis.

#### Acceptance Criteria

1. WHEN VisualizationSpec status is "ready", THE VisualizationRenderer component SHALL dispatch rendering to the appropriate subcomponent based on chart_type: LineVisualization for "line", BarVisualization for "bar", PieVisualization for "pie", ScatterVisualization for "scatter", HistogramVisualization for "histogram".
2. THE VisualizationRenderer component SHALL use field IDs from the encoding object as Recharts dataKey values for data binding, and SHALL use the corresponding field labels from the encoding object for axis labels, legend entries, and tooltip headers.
3. WHEN VisualizationSpec status is "unsupported", THE VisualizationRenderer SHALL display the error string from the VisualizationSpec in place of a chart, without rendering any chart subcomponent.
4. WHEN VisualizationSpec status is "failed", THE VisualizationRenderer SHALL display the error string from the VisualizationSpec in an error-state container, without rendering any chart subcomponent.
5. THE VisualizationRenderer component SHALL follow the existing FinFlow dark/glassmorphism UI theme using ff-* class prefixes.
6. IF the VisualizationSpec chart_type value does not match any supported subcomponent ("line", "bar", "pie", "scatter", "histogram"), THEN THE VisualizationRenderer SHALL display a message indicating the chart type is not supported, without rendering any chart subcomponent.

### Requirement 13: Backward Compatibility

**User Story:** As a FinFlow user, I want my existing jobs to continue working without changes after visualization support is added.

#### Acceptance Criteria

1. THE System SHALL NOT modify the output values, status transitions, execution ordering, or response schema of jobs that contain only cleaning, filtering, or calculation operations and no visualization operations.
2. WHEN a job execution plan contains no visualization DAG_Nodes, THE System SHALL produce `visualizations: []` in the job-detail response without altering the values or structure of the status, results, or operations fields already present in the response.
3. WHEN the `/uploads/{id}/job-detail` endpoint is called for a job created before the visualization migration was applied, THE System SHALL return the same response fields and values as before with `visualizations: []` appended.
4. THE System SHALL implement visualization support using additive-only database migrations that create new tables or columns without dropping, renaming, or altering existing tables, columns, or constraints.

### Requirement 14: OperationResultReader Adapter

**User Story:** As a system architect, I want an adapter interface between operation results and the visualization executor, so that changes to the operation result schema do not require changes throughout the visualization code.

#### Acceptance Criteria

1. THE OperationResultReader SHALL provide methods to access field metadata (id, label, data_type, role, unit, aggregation), retrieve rows as a list of dictionaries (which may be empty), and determine the data_shape based on field roles: if any field has role "time" the data_shape is time_series; if fields include at least one "category" role and one "measure" role the data_shape is categorical_series; if fields represent precomputed bin boundaries and frequencies the data_shape is histogram_bins; if exactly two numeric measure fields exist and no category field is present the data_shape is scatter_points; otherwise the data_shape is scalar.
2. THE OperationResultReader SHALL validate that the source OperationResult contains at least one field with non-null id, data_type, and role attributes before the Visualization_Executor processes the data.
3. IF the OperationResult lacks required field metadata (no fields present, or all fields are missing id, data_type, or role), THEN THE OperationResultReader SHALL raise a validation error that the Visualization_Executor handles by setting status to "failed" with reason_code "invalid_source_data".
4. IF the OperationResult contains valid field metadata but zero data rows, THEN THE OperationResultReader SHALL return an empty row list and a valid data_shape, allowing the Visualization_Executor to proceed with its own compatibility checks.

### Requirement 15: Supported Chart Types

**User Story:** As a product manager, I want the initial chart type scope defined clearly, so that development is bounded to a deliverable set.

#### Acceptance Criteria

1. THE Visualization_Executor SHALL support exactly the following chart_type values in version 1: "auto", "bar", "line", "pie", "scatter", "histogram".
2. THE Visualization_Executor SHALL perform chart_type matching using case-sensitive comparison against the supported set (only lowercase values are valid).
3. WHEN a chart_type value outside the supported set is requested, THE Visualization_Executor SHALL set status to "unsupported" with reason_code "unsupported_chart_type".
4. IF the chart_type value is null, empty, or missing from the request, THEN THE Visualization_Executor SHALL treat the chart_type as "auto".
5. THE Visualization_Executor SHALL NOT support pictogram chart type in version 1.

### Requirement 16: Single Grouped Calculation Per Chart

**User Story:** As a data engineer, I want one grouped aggregation operation to produce all rows for a chart, so that the visualization layer does not need to combine or re-aggregate multiple result sets.

#### Acceptance Criteria

1. THE Execution_Engine SHALL produce exactly one grouped aggregation DAG_Node per visualization DAG_Node, where that single operation's OperationResult contains all rows needed to satisfy the chart's encoding fields and group-by keys.
2. THE Visualization_Executor SHALL consume exclusively the single OperationResult referenced by its source_result_id and SHALL NOT read from, merge, or combine data from any other OperationResult in the PipelineState.
3. IF the Visualization_Executor cannot locate an OperationResult for the source_result_id referenced by its DAG_Node, THEN THE Visualization_Executor SHALL return a VisualizationSpec with status "failed" and reason_code "source_result_missing".
4. IF the Execution_Engine detects that a visualization DAG_Node's depends_on references more than one calculation step, THEN THE Execution_Engine SHALL reject the plan with an error identifying the visualization step_id and the conflicting dependencies.

### Requirement 17: Field Selection Validation

**User Story:** As a data engineer, I want chart field references validated against the operation result schema, so that rendering failures due to missing or incompatible fields are caught early.

#### Acceptance Criteria

1. THE Visualization_Executor SHALL validate that every field ID referenced in the encoding object (across all axis roles) exists in the OperationResult field metadata before proceeding with chart rendering.
2. THE Visualization_Executor SHALL validate that fields mapped to a measure axis role (such as y-axis or value) in the encoding object have data_type of "integer" or "float" in the OperationResult field metadata.
3. THE Visualization_Executor SHALL validate that fields mapped to a time axis role in the encoding object have data_type of "datetime" or role of "time" in the OperationResult field metadata.
4. THE Visualization_Executor SHALL validate that fields mapped to a category axis role in the encoding object have role of "category" or "dimension" in the OperationResult field metadata.
5. IF one or more field validations fail, THEN THE Visualization_Executor SHALL set status to "unsupported" with reason_code "invalid_field_reference" and include all failing field IDs in the error message.
6. THE Visualization_Executor SHALL complete all field validation checks (existence, data_type, and role) before performing chart compatibility validation as defined in Requirement 8.

### Requirement 18: Unsupported State Handling

**User Story:** As a FinFlow user, I want clear feedback when my chart request cannot be fulfilled, so that I understand the limitation without the job being marked as failed.

#### Acceptance Criteria

1. WHEN the requested chart type is incompatible with the operation result data shape (for example a scalar result with a line chart request), THE Visualization_Executor SHALL return a VisualizationSpec with status "unsupported", a reason_code identifying the specific incompatibility, and a non-empty error string of 1 to 500 characters that describes the incompatibility in plain language without exposing internal codes or stack traces.
2. THE Visualization_Executor SHALL NOT fabricate data, insert placeholder values, or generate synthetic rows to satisfy an incompatible chart request.
3. WHEN a VisualizationSpec has status "unsupported", THE System SHALL persist the spec in the `job_visualizations` table so the frontend can display the reason to the user.
4. WHEN a VisualizationSpec has status "unsupported", THE Visualization_Executor SHALL set the data field to an empty array and the encoding field to an empty object in the returned VisualizationSpec.
