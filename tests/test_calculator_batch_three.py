import unittest

from app.calculators.registry import CalculatorRegistry
from app.calculators.repository import CalculatorRepository


class CalculatorBatchThreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CalculatorRegistry(CalculatorRepository())

    def test_morse_braden_mna_and_gds(self) -> None:
        self.assertEqual(self.registry.get("morse_fall_scale")({"total_score": 55})["risk_level"], "高风险")
        self.assertEqual(self.registry.get("braden_scale")({"total_score": 12})["risk_level"], "高风险")
        self.assertEqual(self.registry.get("mna_sf")({"total_score": 9})["risk_level"], "营养不良风险")
        self.assertEqual(self.registry.get("gds15")({"total_score": 10})["risk_level"], "中度抑郁风险")

    def test_tug_ad8_and_mini_cog(self) -> None:
        self.assertEqual(self.registry.get("tug_test")({"time_seconds": 14.2})["risk_level"], "高跌倒风险")
        self.assertEqual(self.registry.get("ad8")({"total_score": 3})["risk_level"], "认知异常风险")
        self.assertEqual(
            self.registry.get("mini_cog")({"recall_score": 1, "clock_normal": False})["risk_level"],
            "认知异常风险",
        )

    def test_frailty_function_and_sarc_f(self) -> None:
        self.assertEqual(self.registry.get("fried_frailty")({"total_score": 3})["risk_level"], "衰弱")
        self.assertEqual(self.registry.get("lawton_iadl")({"total_score": 4})["risk_level"], "中度依赖")
        self.assertEqual(self.registry.get("sarc_f")({"total_score": 5})["risk_level"], "肌少症风险")
        self.assertEqual(self.registry.get("rockwood_cfs")({"grade": 6})["risk_level"], "衰弱")
        self.assertEqual(self.registry.get("karnofsky_ps")({"total_score": 60})["risk_level"], "中度功能受限")


if __name__ == "__main__":
    unittest.main()
