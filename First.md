You are refactoring the FinFlow project from a fragmented prompt-driven architecture into a single canonical-intent-driven architecture.

This is a production architecture refactor, not a superficial patch.

Do not solve individual prompt failures using new keyword checks, aliases, regex patches, or agent-specific prompt logic.

The current problem is that the same raw user instruction may be interpreted by multiple independent components:

* backend action-schema parsing
* backend constraint/rule extraction
* agent-service orchestrator
* cleaning-agent LLM planning
* filter-agent LLM planning
* calculation-agent LLM planning
* reporting-agent LLM planning
* column resolver fallback
* predicate grounder fallback

This creates competing sources of truth.

The target architecture must interpret the complete user request exactly once and persist that interpretation as a canonical intent.

After canonical intent creation, no downstream component may reinterpret the original prompt.

============================================================
PRIMARY GOAL
============

Replace this fragmented architecture:

```text
Raw user prompt
→ backend heuristics/LLM
→ backend action schema
→ backend rule extractor
→ agent-service orchestrator LLM
→ optional agent-local LLM planners
→ compiler
→ execution
```

with:

```text
Raw user prompt
→ one authoritative intent processor
→ CanonicalIntent
→ semantic column grounding
→ validation
→ one targeted repair attempt when required
→ canonical intent persistence
→ canonical intent job payload
→ deterministic compiler
→ typed agent plans
→ deterministic agents
→ deterministic handlers
→ reporting
→ callback persistence
```

The complete meaning of the user request must be represented by one versioned `CanonicalIntent`.

The raw prompt must become audit data after canonical intent creation.

============================================================
FIRST: INSPECT THE REPOSITORY
=============================

Do not start deleting code immediately.

Inspect the complete backend and agent-service repository.

Search for all places where raw prompt text influences execution.

Search for:

```text
instruction
prompt
raw_prompt
user_prompt
action_schema
rule_extractor
build_plan
parse_instruction
extract_constraints
intent
normalize_intent
repair_intent
call_groq
ChatGroq
with_structured_output
invoke
GROQ_API_KEY
params.get("instruction")
params["instruction"]
if "only"
if "remove"
if "show"
if "filter"
if "column"
if "field"
```

Pay special attention to files equivalent to:

```text
backend/app/services/action_schema.py
backend/app/services/rule_extractor.py

agent-framework/.../src/finflow_agent/llm.py

agent-framework/.../src/finflow_agent/planning/orchestrator.py
agent-framework/.../src/finflow_agent/planning/intent_schema.py
agent-framework/.../src/finflow_agent/planning/normalizer.py
agent-framework/.../src/finflow_agent/planning/repair.py
agent-framework/.../src/finflow_agent/planning/compiler.py
agent-framework/.../src/finflow_agent/planning/validators.py

agent-framework/.../src/finflow_agent/agents/cleaning_agent.py
agent-framework/.../src/finflow_agent/agents/filter_agent.py
agent-framework/.../src/finflow_agent/agents/calculation_agent.py
agent-framework/.../src/finflow_agent/agents/visualization_agent.py
agent-framework/.../src/finflow_agent/agents/reporting_agent.py

agent-framework/.../src/finflow_agent/tools/column_resolver.py
agent-framework/.../src/finflow_agent/tools/predicate_grounder.py

agent-framework/.../src/finflow_agent/job_runner.py
agent-framework/.../src/finflow_agent/api.py
agent-framework/.../src/finflow_agent/engine.py
```

The exact paths may differ.

Create an internal inventory containing:

* file
* function
* whether it calls an LLM
* whether it reads the raw prompt
* whether it changes execution meaning
* whether it is production, fallback, standalone, test-only, or dead code
* current callers
* replacement path

Classify each prompt-related path as:

```text
authoritative intent extraction
backend heuristic interpretation
legacy fallback
agent-local planning
semantic column fallback
predicate grounding
audit-only
test-only
dead code
```

Do not delete a path until all of its active callers have been migrated.

============================================================
ARCHITECTURAL OWNERSHIP
=======================

There must be only one production owner of complete prompt interpretation.

Recommended owner:

```text
agent-service canonical intent processor
```

This component is responsible for:

* understanding the full user request
* separating different action types
* resolving poor or incomplete wording
* producing canonical actions
* grounding requested fields against the dataframe schema
* validating the result
* performing one targeted repair attempt
* returning a versioned canonical intent envelope

The backend should remain responsible for:

* authentication
* upload handling
* submission persistence
* job creation
* queueing
* status
* callback persistence
* audit display

The backend must not independently build a competing execution interpretation.

The compiler must not interpret natural language.

Agents must not interpret natural language in normal production execution.

Handlers must never receive the raw prompt.

============================================================
CANONICAL INTENT MODEL
======================

Create or consolidate one authoritative versioned canonical intent schema.

Do not maintain multiple competing intent models.

Prefer a discriminated action union.

Adapt this example to existing project models instead of unnecessarily duplicating compatible schemas:

```python
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field


class ColumnReference(BaseModel):
    raw_reference: str
    resolved_column: str | None = None
    resolution_method: str | None = None
    evidence: list[str] = Field(default_factory=list)


class FilterConditionIntent(BaseModel):
    field: ColumnReference

    operator: Literal[
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains",
        "not_contains",
        "starts_with",
        "ends_with",
        "between",
        "in",
        "not_in",
        "is_null",
        "is_not_null",
    ]

    value: Any | None = None
    value_to: Any | None = None


class CleanIntentAction(BaseModel):
    kind: Literal["clean"]
    operations: list[dict[str, Any]]


class FilterRowsIntentAction(BaseModel):
    kind: Literal["filter_rows"]
    conditions: list[FilterConditionIntent]
    logic: Literal["and", "or"] = "and"


class ProjectColumnsIntentAction(BaseModel):
    kind: Literal["project_columns"]
    columns: list[ColumnReference]


class DropColumnsIntentAction(BaseModel):
    kind: Literal["drop_columns"]
    columns: list[ColumnReference]


class RenameColumnsIntentAction(BaseModel):
    kind: Literal["rename_columns"]
    mappings: list[dict[str, str]]


class SortRowsIntentAction(BaseModel):
    kind: Literal["sort_rows"]
    columns: list[ColumnReference]
    ascending: list[bool]


class LimitRowsIntentAction(BaseModel):
    kind: Literal["limit_rows"]
    limit: int


class CalculateIntentAction(BaseModel):
    kind: Literal["calculate"]
    operations: list[dict[str, Any]]


class VisualizeIntentAction(BaseModel):
    kind: Literal["visualize"]
    operations: list[dict[str, Any]]


class ReportIntentAction(BaseModel):
    kind: Literal["report"]
    output_format: Literal["xlsx", "csv", "json", "txt"]
    options: dict[str, Any] = Field(default_factory=dict)


IntentAction = Annotated[
    CleanIntentAction
    | FilterRowsIntentAction
    | ProjectColumnsIntentAction
    | DropColumnsIntentAction
    | RenameColumnsIntentAction
    | SortRowsIntentAction
    | LimitRowsIntentAction
    | CalculateIntentAction
    | VisualizeIntentAction
    | ReportIntentAction,
    Field(discriminator="kind"),
]


class CanonicalIntent(BaseModel):
    schema_version: str

    actions: list[IntentAction]

    status: Literal[
        "resolved",
        "repaired",
        "ambiguous",
        "needs_clarification",
        "unsupported",
        "rejected",
    ]

    output_format: Literal["xlsx", "csv", "json", "txt"]

    assumptions: list[str] = Field(default_factory=list)
    repair_notes: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
```

The action list must become the authoritative representation.

Legacy booleans such as:

```text
needs_cleaning
needs_filtering
needs_reporting
```

may remain temporarily for compatibility, but they must be derived from the canonical actions and must not be an independent source of truth.

============================================================
CANONICAL INTENT ENVELOPE
=========================

Create a transport and persistence envelope:

```python
from datetime import datetime
from pydantic import BaseModel, Field


class CanonicalIntentEnvelope(BaseModel):
    envelope_version: str
    intent: CanonicalIntent

    original_instruction: str | None = None

    extractor_version: str
    normalizer_version: str
    grounding_version: str

    assumptions: list[str] = Field(default_factory=list)
    repair_notes: list[str] = Field(default_factory=list)

    created_at: datetime
```

The `original_instruction` is audit-only after the envelope is created.

Do not allow downstream execution to derive operations from it.

============================================================
INTENT PROCESSING PIPELINE
==========================

Implement one explicit canonical intent pipeline:

```text
raw prompt
→ initial structured extraction
→ conservative normalization
→ structural validation
→ dataframe/schema grounding
→ semantic validation
→ one targeted repair attempt
→ final strict validation
→ CanonicalIntentEnvelope
```

The intent extractor must receive enough context to understand the request:

* available dataframe columns
* normalized column names
* data types
* semantic column descriptions
* bounded representative values
* supported action kinds
* supported operators
* supported output formats

Do not send the complete dataframe to the LLM.

Use strict structured output and temperature zero.

============================================================
BAD USER PROMPT REPAIR
======================

The intent processor must handle poor user language without downstream patches.

Examples:

```text
return only customer id
customer id only
just give customer id
only customer identifier please
```

All should resolve to:

```text
project_columns → Customer_ID
```

These requests are different and must remain different:

```text
remove customer id
→ drop_columns

customer id equals 1002
→ filter_rows

return only customer id
→ project_columns
```

Do not implement this using scattered phrase checks inside the backend or agents.

The intent processor may use linguistic evidence, schema evidence, and the LLM to produce the canonical action.

============================================================
INTENT REPAIR RULES
===================

Use only one automatic repair attempt.

Do not use blind retries.

Do not ask the LLM to regenerate everything repeatedly without diagnostics.

The repair prompt must receive:

* original user prompt
* invalid canonical intent
* exact validation errors
* available dataframe columns
* semantic column profiles
* supported actions
* supported operators
* instruction to preserve valid actions
* instruction not to invent columns
* instruction not to invent filter values
* instruction not to return execution steps

After repair:

```text
validate again
```

If the intent still cannot be safely resolved, return one of:

```text
ambiguous
needs_clarification
unsupported
rejected
```

Do not force it into execution.

============================================================
SEMANTIC COLUMN GROUNDING
=========================

The semantic resolver and predicate grounder may continue to use constrained LLM fallback, but their authority must be narrowed.

They may answer questions such as:

```text
Does "customer id" refer to Customer_ID?
Does "Laptop" belong to Product_Name or Product_Description?
Does "credited" refer to Transaction_Type or Credit_Amount?
```

They must not reinterpret the complete user request.

They must receive canonical unresolved references or clauses, not the full raw prompt.

They must choose only from actual available columns.

They must be allowed to return:

```text
resolved
ambiguous
unresolved
pending_review
rejected
```

They must not invent columns.

They must not create arbitrary new actions.

============================================================
BACKEND REMOVAL
===============

Inspect:

```text
backend/app/services/action_schema.py
backend/app/services/rule_extractor.py
```

and equivalent modules.

Determine which responsibilities are:

* upload/schema inspection
* audit metadata
* constraint validation
* execution interpretation
* legacy prompt parsing

Keep genuine upload/schema validation if needed.

Remove or retire independent execution interpretation once the canonical intent service is authoritative.

Examples of behavior to remove:

```python
if "only" in prompt:
    ...

if "column" in prompt:
    ...

if "field" in prompt:
    ...

if "remove" in prompt:
    ...

if "show" in prompt:
    ...
```

Do not replace these with more extensive keyword lists.

The backend may call the authoritative canonical intent endpoint/module, but it must not independently derive a second intent.

============================================================
JOB PAYLOAD
===========

Thread the canonical intent envelope through the complete job boundary.

Target request model:

```python
class AgentJobRequest(BaseModel):
    job_id: str
    submission_id: str

    file_id: str
    file_name: str
    resolved_file_path: str

    canonical_intent: CanonicalIntentEnvelope

    # Audit-only compatibility field.
    instruction: str | None = None
```

Use JSON-safe serialization:

```python
payload = request.model_dump(mode="json")
```

On the worker:

```python
job = AgentJobRequest.model_validate(payload)
```

Do not enqueue Pydantic objects, pandas objects, raw enums, or non-serialized datetimes directly.

============================================================
PERSISTENCE
===========

Persist canonical intent before execution.

Create additive Alembic migrations.

Do not modify previously applied migrations.

Persist:

```text
canonical_intent JSONB
canonical_intent_schema_version
canonical_intent_status
original_instruction
intent_extractor_version
intent_normalizer_version
intent_grounding_version
canonical_intent_created_at
```

During the transition, keep `canonical_intent` nullable for old rows.

Do not immediately add a non-null database constraint.

Use a later migration only after all job producers write canonical intent.

Add PostgreSQL migration parity tests.

============================================================
WORKER/JOB RUNNER
=================

Replace production behavior such as:

```python
execution_plan = orchestrator.build_plan(job.instruction)
```

with:

```python
intent_envelope = CanonicalIntentEnvelope.model_validate(
    job.canonical_intent
)

execution_plan = compile_canonical_intent(
    intent_envelope.intent,
    resolved_file_path=job.resolved_file_path,
    ...
)
```

The worker must be capable of executing with:

```text
instruction = None
```

when canonical intent is present.

The worker must not reinterpret the raw prompt.

============================================================
COMPILER CONTRACT
=================

Create one strict compiler entry point:

```python
def compile_canonical_intent(
    intent: CanonicalIntent,
    *,
    resolved_file_path: str,
    file_type: str,
    output_dir: str,
    artifact_prefix: str,
) -> ExecutionPlan:
    ...
```

The compiler must not accept:

* raw strings
* raw prompts
* unvalidated dictionaries
* LLM responses
* unresolved column references

The compiler must:

* preserve canonical action order
* map actions to agent steps
* validate dependencies
* validate artifact routing
* map grounded fields to operation plans
* reject unsupported actions
* reject unresolved fields
* produce deterministic output
* make zero LLM calls

The same canonical intent must always produce the same execution plan.

============================================================
AGENT CONTRACT
==============

Production agents must receive typed plans only.

Examples:

```text
cleaning_agent
→ CleaningOperationPlan

filter_agent
→ FilterOperationPlan

calculation_agent
→ CalculationOperationPlan

visualization_agent
→ VisualizationOperationPlan

reporting_agent
→ ReportingOperationPlan
```

Remove automatic production behavior such as:

```python
if params.get("instruction"):
    plan = create_plan_with_llm(...)
```

Replace it with:

```python
if params.get("plan") is not None:
    validate_and_execute_plan()

elif (
    settings.ENABLE_STANDALONE_AGENT_PLANNING
    and params.get("mode") == "standalone_planning"
):
    create_plan_for_explicit_development_use()

else:
    return controlled_missing_plan_error()
```

Rules:

* standalone planning defaults to disabled
* `GROQ_API_KEY` alone must never activate agent planning
* normal jobs must never invoke agent-local planning
* standalone planning must be explicitly requested
* production integration tests must assert zero agent-local LLM calls

After migration, consider moving standalone planning into separate development utilities.

============================================================
SHARED LLM CLIENT
=================

Keep the shared LLM client as infrastructure.

Do not remove it merely because multiple callers are removed.

The shared LLM client may be used by:

```text
canonical intent extraction
targeted canonical intent repair
semantic column profiling
constrained column grounding
constrained predicate disambiguation
```

It must no longer be used by normal production agents to reinterpret the whole request.

Add explicit operation labels to LLM calls:

```text
intent_extract
intent_repair
semantic_profile
column_grounding
predicate_disambiguation
```

Log only safe metadata.

============================================================
LEGACY FEATURE FLAG
===================

Add a temporary feature flag:

```text
ALLOW_LEGACY_PROMPT_PLANNING
```

Transition behavior:

```python
if job.canonical_intent is not None:
    use_canonical_path()

elif settings.ALLOW_LEGACY_PROMPT_PLANNING:
    log_legacy_usage()
    use_legacy_path()

else:
    reject_missing_canonical_intent()
```

Never silently fall back to legacy prompt planning.

Log:

```text
event=legacy_prompt_planning_used
job_id
submission_id
```

After all producers and consumers are migrated:

1. disable the flag in tests
2. disable it in development
3. disable it in production
4. verify no legacy usage logs occur
5. delete the legacy branch
6. delete the flag

============================================================
SAFE MIGRATION PHASES
=====================

Perform the refactor in these phases.

---

## PHASE 1 — INVENTORY

Identify:

* all LLM callers
* all raw-prompt readers
* all prompt heuristics
* all compiler callers
* all job payload producers
* all job payload consumers
* all agent-local planners
* all legacy intent models
* all related tests

Do not change runtime behavior yet.

---

## PHASE 2 — ADD NEW CONTRACTS

Add:

* CanonicalIntent
* CanonicalIntentEnvelope
* canonical validation
* canonical compiler entry point
* job payload field
* persistence fields
* version metadata
* serialization tests

Do not remove the old path yet.

---

## PHASE 3 — AUTHORITATIVE INTENT PROCESSOR

Implement or consolidate:

```text
extract
→ normalize
→ ground
→ validate
→ targeted repair
→ final intent
```

Ensure it is the only full-prompt interpretation path.

---

## PHASE 4 — MIGRATE JOB PRODUCERS

Update every backend/API producer to:

1. obtain canonical intent
2. persist canonical intent
3. enqueue canonical intent
4. retain raw prompt only for audit

All new jobs must include canonical intent.

---

## PHASE 5 — MIGRATE CONSUMERS

Update:

* worker
* job runner
* compiler
* engine
* retry logic
* replay logic
* callbacks
* agents

No production consumer should need the raw prompt.

---

## PHASE 6 — DISABLE LEGACY PATHS

Set:

```text
ALLOW_LEGACY_PROMPT_PLANNING=false
ENABLE_STANDALONE_AGENT_PLANNING=false
```

Run all tests and real end-to-end scenarios.

Verify no old prompt parser is called.

---

## PHASE 7 — DELETE OLD STRUCTURE

Only after migration verification:

* remove backend execution heuristics
* remove duplicate action-schema interpretation
* remove duplicate rule extraction used for execution
* remove legacy orchestrator prompt-to-plan path
* remove automatic agent-local LLM planning
* remove raw-prompt compiler fallbacks
* remove duplicate intent models
* remove obsolete prompts
* remove dead imports
* remove stale configuration
* update tests and documentation

Do not delete original prompt audit storage.

============================================================
TEST REQUIREMENTS
=================

Add tests at all architectural boundaries.

### Canonical intent unit tests

Verify:

* discriminated action parsing
* invalid action rejection
* stable serialization
* stable deserialization
* unsupported schema-version rejection
* unresolved column rejection before compilation

### Intent interpretation tests

These must become `project_columns`:

```text
return only customer id
customer id only
just give customer id
keep only customer identifier
output customer id and nothing else
```

These must become `drop_columns`:

```text
remove customer id
drop customer id
exclude customer id from output
```

These must become `filter_rows`:

```text
customer id equals 1002
show customer 1002
rows where customer id is 1002
```

### Mixed request tests

```text
clean the data and return only customer id and name
```

Expected canonical action order:

```text
clean
→ project_columns
→ report
```

### Semantic grounding tests

Dataset:

```text
Product_Name:
iPad
iPhone
Desktop
Mobile

Payment_Method:
UPI
Cash
Card
```

Prompt:

```text
show Laptop
```

Expected:

```text
filter_rows
Product_Name == Laptop
```

`Laptop` must not map to `Payment_Method`.

Zero output rows must be valid if Laptop is absent.

### Compiler tests

Verify:

* compiler accepts only CanonicalIntent
* raw strings are rejected
* unresolved references are rejected
* no LLM call occurs
* identical intent produces identical execution plan
* action ordering is preserved

### Agent tests

Verify:

* typed plans execute
* missing plans return controlled errors
* normal execution makes zero agent-local LLM calls
* `GROQ_API_KEY` does not activate planning
* standalone mode requires explicit configuration and mode

### Job payload tests

Verify:

* backend serialization round-trip
* queue serialization round-trip
* worker validation
* canonical intent survives transport unchanged
* worker executes with no raw instruction
* malformed envelope is rejected

### Persistence tests

Verify:

* canonical intent JSONB persistence
* version persistence
* original prompt audit persistence
* old nullable rows remain valid
* PostgreSQL migration upgrade and downgrade where supported

### Legacy feature-flag tests

Verify:

```text
canonical_intent present
→ canonical path always used

canonical_intent absent + legacy enabled
→ legacy path with warning

canonical_intent absent + legacy disabled
→ controlled rejection
```

### End-to-end tests

Run:

```text
return only customer id
remove customer id
customer id equals 1002
clean and return only customer id
show female customers aged 45
show credited transactions above 40000
show UPI transactions
show Laptop
```

For every case verify:

* correct canonical intent
* correct grounded columns
* correct compiled plan
* correct output
* correct callback state
* no duplicated prompt interpretation
* no agent-local planning
* audit trail preserved

### Replay test

Persist a canonical intent and replay it without the raw prompt.

Verify:

```text
same canonical intent
→ same execution plan
→ same deterministic operations
```

============================================================
OBSERVABILITY
=============

Add structured logs for:

```text
intent_extraction_started
intent_extracted
intent_normalized
intent_grounded
intent_repair_started
intent_repaired
intent_validation_failed
canonical_intent_persisted
canonical_job_enqueued
canonical_job_started
canonical_job_compiled
legacy_prompt_planning_used
agent_typed_plan_executed
```

Include:

```text
job_id
submission_id
intent_schema_version
extractor_version
normalizer_version
grounding_version
compiler_version
action kinds
intent status
repair used
legacy path used
```

Do not log:

* complete spreadsheets
* sensitive cell values
* API keys
* callback tokens
* account numbers
* card numbers
* secrets

============================================================
HEALTH AND BUILD METADATA
=========================

Extend the health endpoint with:

```json
{
  "status": "ok",
  "git_commit": "...",
  "canonical_intent_schema_version": "...",
  "intent_extractor_version": "...",
  "intent_normalizer_version": "...",
  "intent_grounding_version": "...",
  "compiler_version": "...",
  "legacy_prompt_planning_enabled": false,
  "standalone_agent_planning_enabled": false
}
```

This must reflect the running container, not only local source.

============================================================
NON-NEGOTIABLE RULES
====================

* Do not perform a big-bang deletion.
* Do not add more prompt-specific backend heuristics.
* Do not maintain two permanent full-intent authorities.
* Do not let backend and agent-service independently interpret the same request.
* Do not let the compiler parse natural language.
* Do not let normal agents plan from raw instructions.
* Do not let handlers read raw prompts.
* Do not silently use legacy fallback.
* Do not let an API key automatically enable planning.
* Do not allow unresolved columns into the compiler.
* Do not use untyped dictionaries at architecture boundaries.
* Do not edit already-applied Alembic migrations.
* Do not remove callback idempotency.
* Do not remove original prompt audit data.
* Do not claim completion without running tests.
* Do not delete legacy code until all callers are migrated and verified.

============================================================
DELETION CHECKLIST
==================

Before deleting the old architecture, prove:

```text
[ ] Every new job contains canonical_intent
[ ] Canonical intent is persisted
[ ] Canonical intent survives queue serialization
[ ] Worker executes without raw instruction
[ ] Compiler accepts only CanonicalIntent
[ ] All column references are grounded
[ ] Agents receive typed plans only
[ ] Normal execution makes zero agent-local LLM calls
[ ] Backend prompt heuristics no longer affect execution
[ ] Legacy mode is disabled
[ ] Repository-wide search finds no active legacy caller
[ ] Replay produces the same execution plan
[ ] Callback tests pass
[ ] PostgreSQL migrations pass
[ ] Complete test suite passes
[ ] Docker containers run the current Git revision
```

Only then delete:

```text
legacy backend execution parser
legacy action-schema interpretation
legacy rule-extraction execution path
legacy orchestrator prompt-planning path
automatic agent-local planners
raw-prompt compiler fallbacks
duplicate intent models
obsolete prompts
obsolete feature flags
dead imports
dead tests
```

============================================================
REQUIRED DELIVERY REPORT
========================

At completion, provide:

1. Architecture before the refactor.
2. Architecture after the refactor.
3. Full inventory of prompt interpretation paths found.
4. LLM callers retained.
5. LLM callers removed.
6. Files created.
7. Files modified.
8. Files deleted.
9. Migrations created.
10. CanonicalIntent schema.
11. CanonicalIntentEnvelope schema.
12. Job payload changes.
13. Compiler signature changes.
14. Worker/job-runner changes.
15. Backend heuristic paths removed.
16. Agent-local planning paths removed or isolated.
17. Semantic resolver authority after refactor.
18. Feature flags introduced.
19. Feature flags removed.
20. Tests added.
21. Tests passed.
22. Tests skipped.
23. Tests failing.
24. Docker services rebuilt.
25. Health metadata output.
26. Remaining legacy references.
27. Remaining risks.
28. Rollback procedure.

============================================================
DEFINITION OF DONE
==================

The refactor is complete only when:

1. The complete raw prompt is interpreted exactly once in production.
2. That interpretation produces one validated CanonicalIntent.
3. CanonicalIntent is grounded against the dataframe schema.
4. CanonicalIntent is persisted before execution.
5. CanonicalIntent is included in the job payload.
6. The worker does not require the raw prompt.
7. The compiler accepts CanonicalIntent only.
8. The compiler makes no LLM calls.
9. Agents consume typed plans only.
10. Agents make no LLM calls during normal execution.
11. Handlers never receive raw prompt text.
12. Backend heuristics no longer determine execution.
13. Semantic fallback tools answer only narrow grounding questions.
14. The same CanonicalIntent produces the same ExecutionPlan.
15. Legacy mode is disabled.
16. All active callers of the old structure are removed.
17. Existing cleaning, filtering, projection, calculation, visualization, and reporting behavior remains functional.
18. Unit, integration, migration, worker, callback, replay, and end-to-end tests pass.
