import unittest
from unittest.mock import patch

from app.experiments.ablation import (
    HomeInquiryCaseResult,
    _build_summary,
    compare_variants,
    load_benchmark_cases,
)


class AblationExperimentTests(unittest.TestCase):
    def test_default_benchmark_has_expected_case_count(self) -> None:
        cases = load_benchmark_cases()

        self.assertEqual(len(cases), 513)
        self.assertTrue(all(case.scenario_type == "calculator" for case in cases))

    @patch("app.experiments.ablation.run_deepseek_variant")
    def test_compare_variants_reports_three_dimension_accuracy(self, mock_run_deepseek_variant) -> None:
        cases = load_benchmark_cases()[:5]
        fake_records = [
            HomeInquiryCaseResult(
                variant="deepseek_direct",
                case_id=case.id,
                scenario_type=case.scenario_type,
                strict_correct=False,
                calculation_result_correct=index == 0,
                risk_level_correct=index in {0, 1},
                numeric_reference_correct=False,
                reply_text="{}",
                predicted_tool=None,
                predicted_calculation_result=None,
                predicted_risk_level=None,
                predicted_numeric_reference=None,
            )
            for index, case in enumerate(cases)
        ]
        mock_run_deepseek_variant.return_value = _build_summary("deepseek_direct", fake_records)

        report = compare_variants(cases)

        self.assertEqual(len(cases), report["case_count"])
        for key in (
            "strict_accuracy",
            "calculation_result_accuracy",
            "risk_level_accuracy",
            "numeric_reference_accuracy",
        ):
            self.assertIn(key, report["full_system"])
            self.assertIn(key, report["deepseek_direct"])

        self.assertGreater(report["full_system"]["strict_accuracy"], report["deepseek_direct"]["strict_accuracy"])
        self.assertGreater(
            report["full_system"]["calculation_result_accuracy"],
            report["deepseek_direct"]["calculation_result_accuracy"],
        )
        self.assertGreater(
            report["full_system"]["numeric_reference_accuracy"],
            report["deepseek_direct"]["numeric_reference_accuracy"],
        )


if __name__ == "__main__":
    unittest.main()
