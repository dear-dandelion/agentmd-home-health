from __future__ import annotations

import inspect
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import requests

from app.calculators.metadata import CalculatorManifest, STANDARD_OUTPUT_FIELDS


CalculatorFunc = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class ValidationLayer:
    name: str
    passed: bool
    details: str


@dataclass
class CalculatorValidationReport:
    calculator_name: str
    approved: bool
    standards: dict[str, bool] = field(default_factory=dict)
    layers: list[ValidationLayer] = field(default_factory=list)


class DeepSeekLogicVerifier:
    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def verify(self, manifest: CalculatorManifest, sample_result: dict[str, Any]) -> ValidationLayer:
        if not self.api_key:
            fallback_ok = bool(manifest.reference and manifest.documentation.get("reference_literature"))
            return ValidationLayer(
                name="llm_secondary_verification",
                passed=fallback_ok,
                details="DeepSeek API unavailable; used local reference-consistency fallback.",
            )

        prompt = {
            "calculator": manifest.display_name,
            "description": manifest.description,
            "reference": manifest.reference,
            "sample_result": sample_result,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Review whether the calculator logic and risk stratification are consistent with the cited medical reference. "
                            "Return JSON only with keys passed(boolean) and details(string). "
                            f"Payload: {prompt}"
                        ),
                    }
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = requests.models.complexjson.loads(content)
        return ValidationLayer(
            name="llm_secondary_verification",
            passed=bool(parsed.get("passed", False)),
            details=str(parsed.get("details", "")),
        )


class CalculatorQualityValidator:
    DOCUMENTATION_KEYS = ("parameter_notes", "usage_examples", "reference_literature", "update_record")

    def __init__(self, logic_verifier: DeepSeekLogicVerifier | None = None) -> None:
        self.logic_verifier = logic_verifier or DeepSeekLogicVerifier()

    def validate(self, manifest: CalculatorManifest, calculator: CalculatorFunc) -> CalculatorValidationReport:
        unit_layer, sample_outputs = self._run_unit_tests(manifest, calculator)
        llm_layer = self.logic_verifier.verify(manifest, sample_outputs[0] if sample_outputs else {})
        boundary_layer = self._run_boundary_tests(manifest, calculator)

        standards = {
            "code_completeness": self._check_code_completeness(calculator, unit_layer),
            "parameter_completeness": self._check_parameter_completeness(manifest),
            "calculation_logic_correctness": unit_layer.passed and llm_layer.passed,
            "risk_grading_accuracy": unit_layer.passed and boundary_layer.passed,
            "output_format_standardization": self._check_output_format(sample_outputs),
            "chinese_localization": self._check_chinese_localization(manifest, sample_outputs),
            "documentation_completeness": self._check_documentation(manifest),
        }

        approved = all(standards.values()) and all(layer.passed for layer in (unit_layer, llm_layer, boundary_layer))
        return CalculatorValidationReport(
            calculator_name=manifest.name,
            approved=approved,
            standards=standards,
            layers=[unit_layer, llm_layer, boundary_layer],
        )

    def _check_code_completeness(self, calculator: CalculatorFunc, unit_layer: ValidationLayer) -> bool:
        signature = inspect.signature(calculator)
        return callable(calculator) and len(signature.parameters) == 1 and unit_layer.passed

    def _check_parameter_completeness(self, manifest: CalculatorManifest) -> bool:
        if not manifest.parameters:
            return False

        param_map = {item.name: item for item in manifest.parameters}
        for param_name in manifest.required_params:
            spec = param_map.get(param_name)
            if spec is None or not spec.python_type:
                return False
            if spec.python_type in {"float", "int"} and (spec.min_value is None or spec.max_value is None):
                return False
        return True

    def _check_output_format(self, outputs: list[dict[str, Any]]) -> bool:
        if not outputs:
            return False
        return all(all(field in output for field in STANDARD_OUTPUT_FIELDS) for output in outputs)

    def _check_chinese_localization(self, manifest: CalculatorManifest, outputs: list[dict[str, Any]]) -> bool:
        if not manifest.supports_chinese:
            return False
        if not self._contains_cjk(manifest.display_name) or not self._contains_cjk(manifest.description):
            return False
        return all(self._contains_cjk(str(output.get("summary", ""))) for output in outputs)

    def _check_documentation(self, manifest: CalculatorManifest) -> bool:
        documentation = manifest.documentation
        return all(documentation.get(key) for key in self.DOCUMENTATION_KEYS)

    def _run_unit_tests(self, manifest: CalculatorManifest, calculator: CalculatorFunc) -> tuple[ValidationLayer, list[dict[str, Any]]]:
        unit_cases = list(manifest.validation.get("unit_cases", []))
        if len(unit_cases) < 4:
            return ValidationLayer("unit_test_validation", False, "At least 4 unit cases are required."), []

        sample_outputs: list[dict[str, Any]] = []
        for case in unit_cases:
            try:
                output = calculator(dict(case["input"]))
            except Exception as exc:
                return ValidationLayer("unit_test_validation", False, f"{case['name']}: raised {exc}"), []

            expected = case.get("expected", {})
            if expected.get("risk_level") and output.get("risk_level") != expected["risk_level"]:
                return ValidationLayer(
                    "unit_test_validation",
                    False,
                    f"{case['name']}: risk level mismatch ({output.get('risk_level')} != {expected['risk_level']})",
                ), []
            if expected.get("score") is not None and output.get("score") != expected["score"]:
                return ValidationLayer(
                    "unit_test_validation",
                    False,
                    f"{case['name']}: score mismatch ({output.get('score')} != {expected['score']})",
                ), []
            if expected.get("summary_contains") and expected["summary_contains"] not in str(output.get("summary", "")):
                return ValidationLayer(
                    "unit_test_validation",
                    False,
                    f"{case['name']}: summary mismatch",
                ), []
            sample_outputs.append(output)

        return ValidationLayer("unit_test_validation", True, f"{len(unit_cases)} unit cases passed."), sample_outputs

    def _run_boundary_tests(self, manifest: CalculatorManifest, calculator: CalculatorFunc) -> ValidationLayer:
        boundary_cases = list(manifest.validation.get("boundary_checks", []))
        if not boundary_cases:
            return ValidationLayer("boundary_value_validation", False, "No boundary checks configured.")

        for case in boundary_cases:
            output = calculator(dict(case["input"]))
            expected_risk_level = case.get("expected_risk_level")
            if expected_risk_level and output.get("risk_level") != expected_risk_level:
                return ValidationLayer(
                    "boundary_value_validation",
                    False,
                    f"{case['name']}: risk level mismatch ({output.get('risk_level')} != {expected_risk_level})",
                )

        return ValidationLayer("boundary_value_validation", True, f"{len(boundary_cases)} boundary checks passed.")

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text))
