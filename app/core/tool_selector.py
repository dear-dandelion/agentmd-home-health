from __future__ import annotations

from typing import Any


class ToolSelector:
    def __init__(self, tools: list[dict[str, Any]]) -> None:
        self.tools = tools

    def select(self, text: str, params: dict[str, Any]) -> str | None:
        lowered = text.lower()
        candidates: list[tuple[tuple[float, int, float, float], str]] = []
        for tool in self.tools:
            keyword_score = sum(1 for keyword in tool.get("intent_keywords", []) if keyword.lower() in lowered)
            if keyword_score <= 0:
                continue
            param_completeness = sum(1 for param_name in tool.get("required_params", []) if param_name in params)
            clinical_specificity = float(tool.get("clinical_specificity", 0))
            priority_score = float(tool.get("priority_score", 0))
            candidates.append(((keyword_score, param_completeness, clinical_specificity, priority_score), tool["name"]))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def required_params(self, tool_name: str) -> list[str]:
        for tool in self.tools:
            if tool["name"] == tool_name:
                return list(tool.get("required_params", []))
        raise ValueError(f"未知工具: {tool_name}")
