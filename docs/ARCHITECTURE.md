# FinFlow Architecture

## System Overview

FinFlow is a finance workflow console with three parts that work together:

- React frontend for upload, review, dashboard, and settings pages
- FastAPI backend for auth, persistence, upload coordination, download, alerts, analytics, and admin workflows
- Separate agent service for workflow execution, output generation, and callback updates

The current product direction is job-driven rather than GL-schema driven. Users submit a file plus an instruction and choose an output format. The backend stores the submission, sends it to the agent service, and later serves the generated artifact through a download endpoint.

## High-Level Flow

```text
Browser
  React + Vite SPA
    Auth pages
    Upload Center
    Submissions / Dashboard / Manager / Admin / Audit
        |
        v
FastAPI backend
  Auth
  Uploads
  Downloads
  Alerts
  Analytics
  Admin
  Agent callback

The current product direction is job-driven rather than GL-schema driven. Users submit a file plus an instruction and choose an output format. The backend stores the submission, sends it to the agent service, and later serves the generated artifact through a download endpoint.

## High-Level Flow

```text
Browser
  React + Vite SPA
    Auth pages
    Upload Center
    Submissions / Dashboard / Manager / Admin / Audit
        |
        v
FastAPI backend
  Auth
  Uploads
  Downloads
  Alerts
  Analytics
  Admin
  Agent callback
        |
        +--> PostgreSQL
        +--> Redis dispatch queue
        +--> Agent service on port 8001
```

### Core Workflow

1. A user uploads a file and enters an instruction.
2. The backend stores a `submissions` row and marks it `processing`.
3. **Schema Proposal Phase**: The backend extracts a data sample and uses semantic analysis (powered by Llama-3.3-70B via `semantic_schema.py`) to infer semantic constraints and roles, building a schema proposal. 
4. The job enters `awaiting_schema_approval`, pausing execution.
5. The user reviews the proposed rules (e.g. non-negative numeric ranges, forbidden substrings) and clicks Approve.
6. The backend first builds a `CanonicalIntent` in `canonical_intent.py`, then derives the legacy `ActionSchema` view for compatibility.
7. The backend enqueues the submission id into Redis, along with the approved canonical intent and its compatibility action schema.
8. The agent service consumes the queue item, runs the validated plan derived from the canonical intent via its execution engine, handling any robust data recovery (e.g. PDF tables via `table_recovery`), and generates an output artifact in the requested format.
9. The agent service posts the generated file back to `POST /api/agent/callback` as `multipart/form-data`.
10. The backend stores the output file in its local `/app/storage/outputs` directory, updates status to `complete`, and emits live refresh events.
11. The frontend fetches job details and the user can download the generated file securely.

Operational safeguards:

- Redis-backed dispatch retries are scheduled with exponential backoff.
- Failed dispatches are recorded in a dead-letter queue after the final retry.
- `/health` reports queue depth and dispatcher state for basic observability.

## Status Model

Current submission states are:

- `pending`
- `processing`
- `awaiting_schema_approval`
- `complete`
- `failed`

## Data Model

### Primary tables

- `users`: app users, roles, and manager assignments
- `refresh_tokens`: hashed refresh tokens for session rotation
- `submissions`: upload metadata, instruction, output format, agent task id, output path, status, timestamps
- `submission_records`: flexible structured records persisted from agent output
- `reviews`: manager decisions for approvals and declines
- `submission_comments`: thread-style comments tied to a submission
- `alerts`: manual or system alerts
- `audit_logs`: immutable audit trail
- `registered_agents`: registry of agent capabilities, formats, and status

## Frontend Structure

```text
frontend/src/
  api/
    client.js
    finflow.js
  auth/
    AuthContext.jsx
    ProtectedRoute.jsx
  components/
    PageHero.jsx
    StatCard.jsx
    StatusPill.jsx
    ProgressMilestones.jsx
    CommentThread.jsx
  hooks/
    useLiveJobRefresh.js
  pages/
    AuthPage.jsx
    VerifyPasswordPage.jsx
    LandingPage.jsx
    UploadCenter.jsx
    SubmissionsPage.jsx
    Dashboard.jsx
    ManagerDashboard.jsx
    AdminDashboard.jsx
    AuditPage.jsx
    SettingsPage.jsx
  shell/
    AppShell.jsx
```

The frontend no longer stores tokens in `localStorage`. Authentication is fully cookie-based. The application verifies the session on load via the `/api/auth/me` endpoint and relies on the browser to pass secure HTTP-only cookies. Password changes rely on a secure email verification flow (`VerifyPasswordPage.jsx`) where sessions are globally revoked upon completion.

## Backend Structure

```text
backend/app/
  api/
    auth.py
    uploads.py
    comments.py
    approvals.py
    alerts.py
    admin.py
    audit.py
    agent.py
    analytics.py
  core/
    config.py
    security.py
  models.py
  schemas.py
  services/
    canonical_intent.py
    action_schema.py
    structured_output.py
    semantic_schema.py
    agent_dispatcher.py
    excel_parser.py
    rule_engine.py
    rule_extractor.py
    schema_proposal.py
    submission_results.py
    websocket_manager.py
    audit.py
```

## Upload API

Important upload endpoints:

- `POST /api/uploads` creates a submission
- `GET /api/uploads` lists jobs with filtering
- `GET /api/uploads/{upload_id}` returns preview and version history
- `GET /api/uploads/{upload_id}/job-detail` returns the card-ready job detail payload
- `POST /api/uploads/{upload_id}/schema-approve` approves the schema and triggers agent dispatch
- `POST /api/uploads/{upload_id}/schema-decline` rejects the schema proposal
- `POST /api/uploads/{upload_id}/retry` requeues the workflow
- `GET /api/uploads/{upload_id}/download` securely serves the generated artifact from `storage/outputs`

## Agent Service, Schema Proposal, & Quarantine

The backend handles the heavy lifting of inferring rules and deciding actions using Llama-3.3-70B. This moves unpredictability away from the agent container into a supervised backend UI loop.

Once a schema proposal is approved by the user, the agent service behaves like a deterministic workflow executor augmented with robust unstructured data extraction. It receives the explicit `ActionSchema` and constraints and applies them using its execution runner.

If a job fails routing (e.g. unsupported domain or capability mismatch), it is placed in the **Quarantine Queue**. From the Admin Dashboard, administrators can:
- View all quarantined jobs
- Select a specific registered agent from a dropdown
- Manually assign and requeue the job to force it to a specific agent

Relevant agent-side pieces:

- `config/agents.yml` for role and capability definitions
- `state.py` for orchestration state
- `action_schema.py` and `intent/` for parsing the execution intent
- `execution/` for running business rules and structural transformations
- `agents/orchestrator.py` for execution planning
- `tools/table_recovery.py` for structured table extraction from messy data
- `tools/output.py` for multi-format output generation

## Output Handling

Output generation is format-aware:

- `XLSX`
- `CSV`
- `JSON`
- `TXT`
- `PDF`
- `PNG`

The backend callback stores the output path on the submission and the download endpoint serves the file with a real filename and extension derived from the original upload name plus `_processed`.

## Analytics And Alerts

Analytics now summarize jobs and outputs rather than a rigid GL transaction model.

Useful aggregates include:

- submission counts by status
- output format distribution
- recent job throughput
- manager-scoped and employee-scoped summaries

Alerts remain available for operational and validation signals, but the current project no longer depends on the old `reupload_requested` workflow.

## Deployment Notes

- Docker Compose starts PostgreSQL, Redis, backend, frontend, and the agent service together
- Backend reads `REDIS_URL`, `AGENT_BASE_URL`, `BACKEND_CALLBACK_URL`, and output directories from env
- Agent service reads its own `.env` and needs access to the shared database and callback secret
- Default admin and demo seeding are development-only unless `SEED_DEFAULT_USERS=true`
- The frontend talks to the backend through the API base URL configured at build time

## Current Design Constraints

- Keep the UI and backend aligned on `pending`, `processing`, `complete`, and `failed`
- Keep the download flow pointed at the backend, not at the agent container directly
- Keep `submission_records` as the main flexible structured data store

