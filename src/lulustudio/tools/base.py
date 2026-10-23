from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..models import ShotSpec, ToolResult


@dataclass
class ToolContext:
    episode_id: str
    shot: ShotSpec
    attempt_no: int
    action: str | None = None
    state: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    name: str

    @abstractmethod
    def run(self, context: ToolContext) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._tools)
