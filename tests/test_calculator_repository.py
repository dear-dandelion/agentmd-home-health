import unittest

from app.calculators.repository import CalculatorRepository


class CalculatorRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CalculatorRepository()

    def test_loads_expected_calculators(self) -> None:
        names = sorted(manifest.name for manifest in self.repository.list_manifests())
        self.assertEqual(
            names,
            [
                "blood_pressure",
                "bmi",
                "body_temperature",
                "fall_risk",
                "fasting_glucose",
                "resting_heart_rate",
                "waist_circumference",
            ],
        )

    def test_priority_scores_are_high_for_seed_calculators(self) -> None:
        for manifest in self.repository.list_manifests():
            self.assertIsNotNone(manifest.priority)
            self.assertEqual(manifest.priority.level, "high")
            self.assertGreater(manifest.priority.total_score, 0.75)

    def test_tool_definitions_include_runtime_metadata(self) -> None:
        tools = {tool["name"]: tool for tool in self.repository.tool_definitions()}
        self.assertIn("priority_score", tools["bmi"])
        self.assertEqual(tools["blood_pressure"]["display_name"], "血压风险评估")


if __name__ == "__main__":
    unittest.main()
