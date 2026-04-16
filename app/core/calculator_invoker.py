from __future__ import annotations

from typing import Any

from app.calculators.repository import CalculatorRepository
from app.calculators.registry import CalculatorRegistry


class CalculatorInvoker:
    def __init__(self, repository: CalculatorRepository | None = None) -> None:
        self.repository = repository or CalculatorRepository()
        self.registry = CalculatorRegistry(self.repository)

    def invoke(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        calculator = self.registry.get(tool_name)
        manifest = self.repository.get_manifest(tool_name)
        result = calculator(params)
        result.setdefault("details", {})
        result["details"]["tool_name"] = tool_name
        result["details"]["display_name"] = manifest.display_name
        result["details"]["priority_level"] = manifest.priority.level if manifest.priority else "unknown"
        return result
