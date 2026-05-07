import unittest

from app.calculators.basic import STANDARD_RESULT_FIELDS
from app.calculators.quality import CalculatorQualityValidator, ValidationLayer
from app.calculators.registry import CalculatorRegistry
from app.calculators.repository import CalculatorRepository


class StubLogicVerifier:
    def verify(self, manifest, sample_result):  # type: ignore[no-untyped-def]
        return ValidationLayer(
            name="llm_secondary_verification",
            passed=True,
            details="Stubbed verifier for deterministic tests.",
        )


class CalculatorQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CalculatorRepository()
        self.registry = CalculatorRegistry(self.repository)
        self.validator = CalculatorQualityValidator(logic_verifier=StubLogicVerifier())

    def test_all_runtime_calculators_pass_quality_validation(self) -> None:
        for manifest in self.repository.list_manifests():
            report = self.validator.validate(manifest, self.registry.get(manifest.name))
            self.assertTrue(report.approved, msg=f"{manifest.name}: {report}")

    def test_all_documented_example_outputs_have_standard_fields(self) -> None:
        for manifest in self.repository.list_manifests():
            example_input = dict(manifest.documentation["usage_examples"][0]["input"])
            result = self.registry.get(manifest.name)(example_input)
            for key in STANDARD_RESULT_FIELDS:
                self.assertIn(key, result, msg=f"{manifest.name} missing {key}")
            self.assertIn("advice", result, msg=f"{manifest.name} missing advice")
            self.assertIn("guideline", result, msg=f"{manifest.name} missing guideline")
            self.assertEqual(result["advice"], result["interpretation"], msg=f"{manifest.name} advice alias mismatch")
            self.assertEqual(result["guideline"], result["reference"], msg=f"{manifest.name} guideline alias mismatch")
            self.assertIsInstance(result["details"], dict, msg=f"{manifest.name} details should be dict")
            self.assertEqual(result["details"].get("calculator"), manifest.name, msg=f"{manifest.name} details.calculator mismatch")

    def test_blood_pressure_boundary_logic(self) -> None:
        calculator = self.registry.get("blood_pressure")
        self.assertEqual(calculator({"systolic_bp": 139, "diastolic_bp": 89})["risk_level"], "偏高")
        self.assertEqual(calculator({"systolic_bp": 140, "diastolic_bp": 89})["risk_level"], "高风险")

    def test_glucose_boundary_logic(self) -> None:
        calculator = self.registry.get("fasting_glucose")
        self.assertEqual(calculator({"fasting_glucose": 6.0})["risk_level"], "正常")
        self.assertEqual(calculator({"fasting_glucose": 6.1})["risk_level"], "偏高")
        self.assertEqual(calculator({"fasting_glucose": 7.0})["risk_level"], "高风险")

    def test_waist_circumference_boundary_logic(self) -> None:
        calculator = self.registry.get("waist_circumference")
        self.assertEqual(calculator({"waist_cm": 89.9, "gender": "男"})["risk_level"], "正常")
        self.assertEqual(calculator({"waist_cm": 90, "gender": "男"})["risk_level"], "偏高")
        self.assertEqual(calculator({"waist_cm": 95, "gender": "女"})["risk_level"], "高风险")

    def test_fall_risk_logic_handles_text_balance_description(self) -> None:
        calculator = self.registry.get("fall_risk")
        self.assertEqual(calculator({"age": 64, "balance_ability": "步态稳定"})["risk_level"], "低风险")
        self.assertEqual(calculator({"age": 68, "balance_ability": "一般"})["risk_level"], "中风险")
        self.assertEqual(calculator({"age": 78, "balance_ability": "步态不稳"})["risk_level"], "高风险")


if __name__ == "__main__":
    unittest.main()
