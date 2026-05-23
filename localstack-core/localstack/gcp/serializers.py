"""GCP REST JSON serializers + LRO Operation envelope."""

from __future__ import annotations

import json
import uuid
from typing import Any

from localstack.gcp.exceptions import GcpError


def serialize_error(exc: GcpError) -> tuple[int, str]:
    body = {
        "error": {
            "code": exc.status_code,
            "status": exc.code,
            "message": str(exc),
        }
    }
    return exc.status_code, json.dumps(body)


def serialize_operation(name: str, *, done: bool = True, response: dict[str, Any] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"name": name, "done": done}
    if metadata is not None:
        out["metadata"] = metadata
    if response is not None:
        out["response"] = response
    return out


def make_operation_name(service: str, project: str, location: str | None = None) -> str:
    loc = location or "global"
    return f"projects/{project}/locations/{loc}/operations/{service}-{uuid.uuid4().hex[:12]}"


def parse_json_body(body: bytes | str | None) -> dict[str, Any]:
    if body is None or body == b"" or body == "":
        return {}
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON body: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError("JSON body must be an object")
    return parsed
