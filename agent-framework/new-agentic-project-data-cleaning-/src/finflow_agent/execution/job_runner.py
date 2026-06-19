from finflow_agent.execution.engine import ExecutionEngine
from finflow_agent.state import ExecutionPlan

class JobRunner:
    """
    Runner helper to execute planned jobs.
    """
    def __init__(self):
        self.engine = ExecutionEngine()

    def run_job(self, plan: ExecutionPlan, submission_id: str | None = None) -> dict:
        return self.engine.execute(plan, submission_id=submission_id)
