from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from ..models import Defect, DefectType, ToolResult
from .base import Tool, ToolContext


def _replace_templates(value: Any, parameters: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_templates(item, parameters) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_templates(item, parameters) for item in value]
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        return parameters.get(value[2:-2], value)
    return value


class ComfyUITool(Tool):
    name = "production"

    def __init__(self, base_url: str, timeout_sec: int = 900, poll_sec: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.poll_sec = poll_sec

    def run(self, context: ToolContext) -> ToolResult:
        started = time.monotonic()
        workflow_path = context.shot.workflow_path
        if not workflow_path:
            return self._error("workflow_path is required for real ComfyUI execution", started)
        path = Path(workflow_path)
        if not path.exists():
            return self._error(f"workflow not found: {path}", started)

        parameters = {
            "PROMPT": context.shot.prompt,
            "SEED": context.shot.parameters.get("seed", 1),
            "DURATION_MS": context.shot.duration_ms,
            **context.shot.parameters,
        }
        workflow = _replace_templates(json.loads(path.read_text(encoding="utf-8")), parameters)
        client_id = str(uuid.uuid4())
        try:
            queued = self._json_request("POST", "/prompt", {"prompt": workflow, "client_id": client_id})
            prompt_id = queued["prompt_id"]
            history = self._wait_for_history(prompt_id)
            execution_error = self._execution_error(history)
            if execution_error:
                return self._error(execution_error, started)
            artifacts = self._collect_artifacts(history)
            if not artifacts:
                return self._error("ComfyUI completed without a saved artifact", started)
            return ToolResult(
                success=True,
                artifacts=artifacts,
                cost=float(context.shot.parameters.get("estimated_cost", 1.0)),
                latency_sec=time.monotonic() - started,
                metadata={"backend": "comfyui", "prompt_id": prompt_id, "client_id": client_id},
            )
        except (OSError, KeyError, ValueError, TimeoutError, urllib.error.URLError) as exc:
            return self._error(str(exc), started)

    def _wait_for_history(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_sec
        while time.monotonic() < deadline:
            payload = self._json_request("GET", f"/history/{prompt_id}")
            if prompt_id in payload:
                return payload[prompt_id]
            time.sleep(self.poll_sec)
        raise TimeoutError(f"ComfyUI prompt timed out: {prompt_id}")

    def _json_request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _collect_artifacts(history: dict[str, Any]) -> dict[str, str]:
        artifacts: dict[str, str] = {}
        for node_id, output in history.get("outputs", {}).items():
            for key in ("images", "audio", "gifs", "videos"):
                for index, item in enumerate(output.get(key, [])):
                    if isinstance(item, dict) and "filename" in item:
                        subfolder = str(item.get("subfolder", "")).strip("/\\")
                        filename = str(item["filename"])
                        artifacts[f"{node_id}.{key}.{index}"] = (
                            f"{subfolder}/{filename}" if subfolder else filename
                        )
        return artifacts

    @staticmethod
    def _execution_error(history: dict[str, Any]) -> str | None:
        status = history.get("status", {})
        for message in status.get("messages", []):
            if not isinstance(message, list) or len(message) < 2 or message[0] != "execution_error":
                continue
            detail = message[1] if isinstance(message[1], dict) else {}
            node = detail.get("node_id", "unknown")
            node_type = detail.get("node_type", "unknown")
            reason = detail.get("exception_message", "unknown error")
            return f"ComfyUI execution failed at node {node} ({node_type}): {reason}"
        if status.get("status_str") == "error":
            return "ComfyUI execution failed"
        return None

    @staticmethod
    def _error(message: str, started: float) -> ToolResult:
        return ToolResult(
            success=False,
            defects=[Defect(type=DefectType.TOOL_ERROR, severity="high", evidence={"message": message})],
            latency_sec=time.monotonic() - started,
            error=message,
        )
