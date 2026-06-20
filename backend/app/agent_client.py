import mimetypes
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.config import get_settings


class AgentDispatchError(Exception):
    pass


def _candidate_agent_base_urls(agent_base_url: str) -> list[str]:
    normalized = str(agent_base_url or "").strip().rstrip("/")
    if not normalized:
        return []

    candidates = [normalized]
    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").strip().lower()
    port = parsed.port

    fallback_hosts: list[str] = []
    if hostname in {"agent-service", "backend", "postgres", "redis"}:
        fallback_hosts.extend(["localhost", "127.0.0.1"])
    elif hostname in {"localhost", "127.0.0.1"}:
        fallback_hosts.append("agent-service")

    for host in fallback_hosts:
        netloc = host
        if port:
            netloc = f"{host}:{port}"
        rebuilt = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)).rstrip("/")
        if rebuilt not in candidates:
            candidates.append(rebuilt)
    return candidates


async def dispatch_to_agent(
    *,
    file_path: str,
    instruction: str,
    output_format: str,
    submission_id: str,
    callback_url: str,
    callback_token: str,
    user_id: str | None = None,
    preferred_agent: str | None = None,
    action_schema: str | None = None,
    canonical_intent: dict | None = None,
) -> str:
    settings = get_settings()
    source_path = Path(file_path)
    if not source_path.exists():
        raise AgentDispatchError(f"Input file not found: {source_path}")

    data = {
        "submission_id": submission_id,
        "file_path": file_path,
        "file_name": source_path.name,
        "resolved_file_path": file_path,
        "output_format": output_format,
        "canonical_intent": canonical_intent,
    }

    attempted_endpoints: list[str] = []
    last_error: Exception | None = None
    response: httpx.Response | None = None
    
    for base_url in _candidate_agent_base_urls(settings.agent_base_url):
        endpoint = f"{base_url}/api/agent/upload"
        attempted_endpoints.append(endpoint)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint,
                    json=data,
                )
            if response.status_code >= 400:
                raise AgentDispatchError(f"Agent dispatch returned {response.status_code}: {response.text}")
            payload = response.json()
            # We don't strictly need task_id in new architecture, we just use submission_id as the link
            return str(submission_id)
        except AgentDispatchError:
            raise
        except httpx.HTTPError as exc:
            last_error = exc
            continue

    attempted = ", ".join(attempted_endpoints) if attempted_endpoints else settings.agent_base_url
    if last_error is not None:
        raise AgentDispatchError(f"Agent dispatch failed after trying {attempted}: {last_error}") from last_error
    raise AgentDispatchError(f"Agent dispatch failed before request could be made. Attempted endpoints: {attempted}")
