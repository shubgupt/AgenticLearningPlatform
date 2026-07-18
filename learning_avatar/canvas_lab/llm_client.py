"""OpenAI-compatible LLM client + a persisted-and-console trace helper.

The trace record is shaped close to OpenInference/OTEL span conventions
(trace_id/span_id/parent_span_id, started_at/ended_at, model, input/output)
so that adopting a real OTEL SDK + Arize Phoenix exporter later is additive
(start also emitting real spans) rather than a schema rewrite. See
docs/llm-lesson-generation-spec.md section 6.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Protocol

from openai import OpenAI

import db

logger = logging.getLogger("llm_client")


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAICompatibleClient:
    """Real client: OpenAI SDK pointed at any OpenAI-compatible endpoint.

    Not necessarily real OpenAI — LLM_BASE_URL may point at a local/lab
    inference server, matching the LearningAvatar reference's pattern.
    """

    def __init__(self) -> None:
        base_url = os.environ.get("LLM_BASE_URL")
        api_key = os.environ.get("LLM_API_KEY")
        self.model = os.environ.get("LLM_MODEL")
        if not (base_url and api_key and self.model):
            raise RuntimeError(
                "LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL must all be set "
                "in the environment to use the generation pipeline."
            )
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_llm_call(
    client: LLMClient,
    *,
    role: str,
    request_id: int | None,
    system: str,
    user: str,
    trace_id: str,
    parent_span_id: str | None = None,
) -> str:
    """Call the LLM once, recording the call to SQLite + the server console.

    This is the single chokepoint every generator/critic call goes through,
    so no LLM call in the pipeline can go untraced.
    """
    span_id = uuid.uuid4().hex
    model_name = getattr(client, "model", "unknown")
    started_at = _now_iso()
    start_perf = time.perf_counter()
    status = "ok"
    output = ""
    try:
        output = client.complete(system, user)
        return output
    except Exception as exc:
        status = "error"
        output = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        ended_at = _now_iso()
        latency_ms = int((time.perf_counter() - start_perf) * 1000)

        record = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "request_id": request_id,
            "role": role,
            "model": model_name,
            "input": user,
            "output": output,
            "status": status,
            "started_at": started_at,
            "ended_at": ended_at,
            "latency_ms": latency_ms,
        }

        with db.get_conn() as conn:
            conn.execute(
                """INSERT INTO llm_call_trace
                   (trace_id, span_id, parent_span_id, request_id, role,
                    model, input, output, status, started_at, ended_at, latency_ms)
                   VALUES (:trace_id, :span_id, :parent_span_id, :request_id, :role,
                           :model, :input, :output, :status, :started_at, :ended_at, :latency_ms)""",
                record,
            )

        logger.info("llm_call_trace %s", json.dumps(record, default=str))
