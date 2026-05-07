import unittest

from app.calculators.registry import CalculatorRegistry
from app.calculators.repository import CalculatorRepository


class CalculatorBatchFourTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CalculatorRegistry(CalculatorRepository())

    def test_metabolic_and_neurologic_batch_four_calculators(self) -> None:
        cdrs = self.registry.get("cdrs")(
            {
                "age": 58,
                "bmi": 28,
                "waist_cm": 92,
                "systolic_bp": 142,
                "gender": "male",
                "family_history_diabetes": True,
            }
        )
        nihss = self.registry.get("nihss")({"total_score": 18})
        gcs = self.registry.get("glasgow_coma_scale")({"gcs_score": 7})

        self.assertEqual(cdrs["score"], 41)
        self.assertEqual(cdrs["details"]["calculator"], "cdrs")
        self.assertEqual(nihss["score"], 18)
        self.assertEqual(nihss["details"]["calculator"], "nihss")
        self.assertEqual(gcs["score"], 7)
        self.assertEqual(gcs["details"]["calculator"], "glasgow_coma_scale")

    def test_general_risk_and_pressure_injury_batch_four_calculators(self) -> None:
        must = self.registry.get("must")(
            {"bmi": 17.8, "weight_loss_percent": 12, "acute_disease_effect": True}
        )
        caprini_vte = self.registry.get("caprini_vte")({"total_score": 6})
        mews = self.registry.get("mews")(
            {
                "respiratory_rate_bpm": 32,
                "temperature_c": 39.1,
                "systolic_bp": 78,
                "heart_rate_bpm": 138,
                "consciousness": "V",
            }
        )
        charlson_cci = self.registry.get("charlson_cci")({"total_score": 5})
        norton_scale = self.registry.get("norton_scale")({"total_score": 12})
        waterlow_score = self.registry.get("waterlow_score")({"total_score": 22})

        self.assertEqual(must["score"], 6)
        self.assertEqual(caprini_vte["score"], 6)
        self.assertEqual(mews["score"], 13)
        self.assertEqual(charlson_cci["score"], 5)
        self.assertEqual(norton_scale["score"], 12)
        self.assertEqual(waterlow_score["score"], 22)

    def test_cardiovascular_batch_four_calculators(self) -> None:
        ascvd_10y = self.registry.get("ascvd_10y")({"risk_percent": 12.4})
        timi = self.registry.get("timi")({"total_score": 5})
        grace_score = self.registry.get("grace")({"total_score": 150})
        grace_percent = self.registry.get("grace")({"risk_percent": 12.0})
        qrisk3 = self.registry.get("qrisk3")({"risk_percent": 11.2})
        h2fpef = self.registry.get("h2fpef")(
            {
                "bmi": 32.1,
                "antihypertensive_count": 2,
                "atrial_fibrillation": True,
                "pulmonary_artery_systolic_pressure": 42,
                "age": 68,
                "e_over_e_prime": 12,
            }
        )

        self.assertEqual(ascvd_10y["score"], 12.4)
        self.assertEqual(ascvd_10y["details"]["mode"], "risk_percent_interpreter")
        self.assertEqual(timi["score"], 5)
        self.assertEqual(grace_score["score"], 150)
        self.assertEqual(grace_score["details"]["mode"], "score_interpreter")
        self.assertEqual(grace_percent["score"], 12.0)
        self.assertEqual(grace_percent["details"]["mode"], "risk_percent_interpreter")
        self.assertEqual(qrisk3["score"], 11.2)
        self.assertEqual(qrisk3["details"]["mode"], "risk_percent_interpreter")
        self.assertEqual(h2fpef["score"], 9)


if __name__ == "__main__":
    unittest.main()
