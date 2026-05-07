import unittest

from app.calculators.repository import CalculatorRepository


class CalculatorRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CalculatorRepository()

    def test_loads_seed_and_batch_four_calculators(self) -> None:
        names = sorted(manifest.name for manifest in self.repository.list_manifests())
        self.assertEqual(len(names), 50)
        for name in (
            "blood_pressure",
            "bmi",
            "body_temperature",
            "fall_risk",
            "fasting_glucose",
            "resting_heart_rate",
            "waist_circumference",
            "phq9",
            "gad7",
            "qsofa",
            "news2",
            "barthel_index",
            "pain_nrs",
            "mmrc",
            "cat",
            "cha2ds2_vasc",
            "has_bled",
            "chads2",
            "wells_dvt",
            "wells_pe",
            "heart_score",
            "findrisc",
            "metabolic_syndrome",
            "nafld_fibrosis",
            "morse_fall_scale",
            "braden_scale",
            "mna_sf",
            "gds15",
            "tug_test",
            "ad8",
            "mini_cog",
            "fried_frailty",
            "lawton_iadl",
            "sarc_f",
            "rockwood_cfs",
            "karnofsky_ps",
            "cdrs",
            "nihss",
            "glasgow_coma_scale",
            "must",
            "caprini_vte",
            "mews",
            "charlson_cci",
            "norton_scale",
            "waterlow_score",
            "ascvd_10y",
            "timi",
            "grace",
            "qrisk3",
            "h2fpef",
        ):
            self.assertIn(name, names)

    def test_priority_scores_are_present_for_all_loaded_calculators(self) -> None:
        for manifest in self.repository.list_manifests():
            self.assertIsNotNone(manifest.priority)
            self.assertGreater(manifest.priority.total_score, 0.75)

    def test_tool_definitions_include_runtime_metadata(self) -> None:
        tools = {tool["name"]: tool for tool in self.repository.tool_definitions()}
        self.assertIn("priority_score", tools["bmi"])
        self.assertEqual(tools["phq9"]["display_name"], "PHQ-9 抑郁筛查")
        self.assertEqual(tools["cha2ds2_vasc"]["display_name"], "CHA2DS2-VASc 卒中风险评分")
        self.assertEqual(tools["news2"]["priority_level"], "high")


if __name__ == "__main__":
    unittest.main()
