from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_worker_startup_bootstraps_agents(monkeypatch):
    import finflow_agent.api as api

    ctx = {}

    assert hasattr(api, "worker_startup"), (
        "api.py should define worker_startup(ctx) for ARQ workers."
    )

    await api.worker_startup(ctx)

    assert "repository" in ctx
    assert "file_store" in ctx

    from finflow_agent.registry import registry

    for agent_name in [
        "ingestion_agent",
        "cleaning_agent",
        "filter_agent",
        "calculation_agent",
        "reporting_agent",
    ]:
        assert registry.get_spec(agent_name).name == agent_name


@pytest.mark.asyncio
async def test_api_upload_enqueues_arq_job(monkeypatch):
    import finflow_agent.api as api

    calls = {"queued_payload": None, "job_id": None, "stored": None}

    class FakeRedis:
        async def enqueue_job(self, function_name, payload, _job_id=None):
            calls["queued_payload"] = payload
            calls["job_id"] = _job_id
            return SimpleNamespace(job_id=_job_id)

    class FakeRepository:
        async def get_job(self, job_id):
            return None

        async def create_or_update_queued(self, job_id, submission_id, payload):
            calls["stored"] = {
                "job_id": job_id,
                "submission_id": submission_id,
                "payload": payload,
            }

    monkeypatch.setattr(api, "JobRepository", lambda: FakeRepository())
    api.app.state.redis = FakeRedis()

    payload = api.JobPayload(
        submission_id="sub123",
        file_id="input.csv",
        file_name="input.csv",
        instruction="make a report",
        output_format="xlsx",
    )

    response = await api.handle_upload(payload)

    assert response["status"] == "queued"
    assert response["job_id"] == "agent:sub123"
    assert calls["job_id"] == "agent:sub123"
    assert calls["queued_payload"]["file_id"] == "input.csv"
    assert "file_path" not in calls["queued_payload"]
    assert calls["stored"]["submission_id"] == "sub123"


def test_jobpayload_uses_file_id_not_file_path():
    from finflow_agent.api import JobPayload

    payload = JobPayload(
        submission_id="sub1",
        file_id="input.csv",
        file_name="input.csv",
        instruction="report",
        output_format="xlsx",
    )

    dumped = payload.model_dump()
    assert dumped["file_id"] == "input.csv"
    assert "file_path" not in dumped


@pytest.mark.asyncio
async def test_engine_failure_summary_preserved(monkeypatch, tmp_path):
    import finflow_agent.api as api

    stored = {"failed_error": None, "callback_payload": None}

    class FakeRepository:
        async def mark_planning(self, job_id):
            pass

        async def mark_running(self, job_id):
            pass

        async def mark_failed(self, job_id, error_msg):
            stored["failed_error"] = error_msg

        async def mark_succeeded(self, job_id, result):
            raise AssertionError("Should not mark succeeded for failed engine result")

        async def mark_quarantined(self, job_id, reason):
            raise AssertionError("Should not quarantine in this test")

        async def mark_callback_failed(self, job_id, error_msg=None):
            pass

    class FakeFileStore:
        def resolve_uploaded_file(self, file_id):
            path = tmp_path / file_id
            path.write_text("a,b\n1,2\n", encoding="utf-8")
            return path

    class FakeOrchestrator:
        def build_plan(self, **kwargs):
            return object()

    class FakeEngine:
        def execute(self, plan, submission_id=None):
            return {
                "status": "failed",
                "output_path": None,
                "summary": {
                    "failed_step_id": "calculate",
                    "error": "Missing required columns in dataset: ['amount']",
                },
            }

    async def fake_callback(payload, job_id, repository):
        stored["callback_payload"] = payload

    monkeypatch.setattr(api, "JobRepository", lambda: FakeRepository())
    monkeypatch.setattr(api, "FileStore", lambda: FakeFileStore())
    monkeypatch.setattr(api, "Orchestrator", lambda: FakeOrchestrator())
    monkeypatch.setattr(api, "ExecutionEngine", lambda: FakeEngine())

    import finflow_agent.jobs.callbacks as callbacks
    monkeypatch.setattr(callbacks, "send_backend_callback", fake_callback)

    await api.process_job_task(
        {},
        {
            "submission_id": "sub-fail",
            "file_id": "input.csv",
            "file_name": "input.csv",
            "instruction": "sum amount",
            "output_format": "xlsx",
        },
    )

    assert "Step 'calculate' failed:" in stored["failed_error"]
    assert "Missing required columns" in stored["failed_error"]
    assert stored["callback_payload"]["status"] == "failed"
    assert "Missing required columns" in str(stored["callback_payload"]["summary"])
