from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STANDARD_OUTPUT_FIELDS = (
    "score",
    "risk_level",
    "summary",
    "interpretation",
    "reference",
    "details",
)


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    label: str
    python_type: str
    required: bool
    description: str
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ParameterSpec":
        return cls(
            name=payload["name"],
            label=payload.get("label", payload["name"]),
            python_type=payload.get("type", "float"),
            required=bool(payload.get("required", False)),
            description=payload.get("description", ""),
            min_value=payload.get("min"),
            max_value=payload.get("max"),
            unit=payload.get("unit"),
        )


@dataclass(frozen=True)
class PriorityProfile:
    home_suitability: float
    clinical_importance: float
    implementation_simplicity: float
    chinese_support: float
    total_score: float
    level: str


@dataclass(frozen=True)
class CalculatorManifest:
    name: str
    display_name: str
    description: str
    source_module: str
    function_name: str
    intent_keywords: list[str]
    required_params: list[str]
    optional_params: list[str]
    parameters: list[ParameterSpec] = field(default_factory=list)
    reference: str = ""
    applicable_scenario: str = ""
    supports_chinese: bool = True
    clinical_specificity: float = 0.0
    priority: PriorityProfile | None = None
    documentation: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], priority: PriorityProfile) -> "CalculatorManifest":
        return cls(
            name=payload["name"],
            display_name=payload.get("display_name", payload["name"]),
            description=payload.get("description", ""),
            source_module=payload["source_module"],
            function_name=payload["function_name"],
            intent_keywords=list(payload.get("intent_keywords", [])),
            required_params=list(payload.get("required_params", [])),
            optional_params=list(payload.get("optional_params", [])),
            parameters=[ParameterSpec.from_dict(item) for item in payload.get("parameters", [])],
            reference=payload.get("reference", ""),
            applicable_scenario=payload.get("applicable_scenario", ""),
            supports_chinese=bool(payload.get("supports_chinese", True)),
            clinical_specificity=float(payload.get("clinical_specificity", 0.0)),
            priority=priority,
            documentation=dict(payload.get("documentation", {})),
            validation=dict(payload.get("validation", {})),
        )

    def to_tool_definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "intent_keywords": self.intent_keywords,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
            "description": self.description,
            "priority_score": self.priority.total_score if self.priority else 0.0,
            "priority_level": self.priority.level if self.priority else "unknown",
            "clinical_specificity": self.clinical_specificity,
        }
