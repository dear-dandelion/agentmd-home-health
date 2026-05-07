import unittest

from app.calculators.registry import CalculatorRegistry
from app.calculators.repository import CalculatorRepository


class CalculatorBatchOneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CalculatorRegistry(CalculatorRepository())

    def test_phq9_and_gad7_ranges(self) -> None:
        self.assertEqual(self.registry.get("phq9")({"total_score": 3})["risk_level"], "低风险")
        self.assertEqual(self.registry.get("phq9")({"total_score": 12})["risk_level"], "中度抑郁风险")
        self.assertEqual(self.registry.get("gad7")({"total_score": 16})["risk_level"], "重度焦虑风险")

    def test_qsofa_and_news2_detect_high_risk(self) -> None:
        qsofa = self.registry.get("qsofa")(
            {"respiratory_rate_bpm": 24, "systolic_bp": 95, "altered_mental_status": True}
        )
        news2 = self.registry.get("news2")(
            {
                "respiratory_rate_bpm": 25,
                "oxygen_saturation": 91,
                "supplemental_oxygen": True,
                "temperature_c": 38.5,
                "systolic_bp": 90,
                "heart_rate_bpm": 132,
                "consciousness": "V",
            }
        )
        self.assertEqual(qsofa["risk_level"], "高风险")
        self.assertEqual(news2["risk_level"], "高风险")

    def test_barthel_pain_mmrc_and_cat_outputs(self) -> None:
        self.assertEqual(self.registry.get("barthel_index")({"total_score": 100})["risk_level"], "独立")
        self.assertEqual(self.registry.get("pain_nrs")({"total_score": 8})["risk_level"], "重度疼痛")
        self.assertEqual(self.registry.get("mmrc")({"grade": 3})["risk_level"], "高症状负担")
        self.assertEqual(self.registry.get("cat")({"total_score": 24})["risk_level"], "高症状负担")


if __name__ == "__main__":
    unittest.main()
