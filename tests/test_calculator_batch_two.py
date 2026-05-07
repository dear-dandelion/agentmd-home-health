import unittest

from app.calculators.registry import CalculatorRegistry
from app.calculators.repository import CalculatorRepository


class CalculatorBatchTwoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CalculatorRegistry(CalculatorRepository())

    def test_stroke_and_bleeding_scores(self) -> None:
        cha2ds2_vasc = self.registry.get("cha2ds2_vasc")(
            {
                "age": 78,
                "gender": "女",
                "congestive_heart_failure": True,
                "hypertension": True,
                "diabetes": False,
                "prior_stroke_tia_thromboembolism": True,
                "vascular_disease": False,
            }
        )
        has_bled = self.registry.get("has_bled")(
            {
                "age": 72,
                "uncontrolled_hypertension": True,
                "abnormal_renal_function": True,
                "abnormal_liver_function": False,
                "prior_stroke": True,
                "bleeding_history": False,
                "labile_inr": False,
                "drugs_predisposing_bleeding": False,
                "alcohol_excess": False,
            }
        )
        chads2 = self.registry.get("chads2")(
            {
                "age": 76,
                "congestive_heart_failure": False,
                "hypertension": True,
                "diabetes": True,
                "prior_stroke_tia": True,
            }
        )
        self.assertEqual(cha2ds2_vasc["risk_level"], "高风险")
        self.assertEqual(has_bled["risk_level"], "高风险")
        self.assertEqual(chads2["risk_level"], "高风险")

    def test_wells_and_heart_scores(self) -> None:
        wells_dvt = self.registry.get("wells_dvt")(
            {
                "active_cancer": False,
                "paralysis_or_recent_cast": False,
                "bedridden_or_recent_surgery": True,
                "localized_tenderness": True,
                "entire_leg_swollen": True,
                "calf_swelling_gt_3cm": True,
                "pitting_edema": True,
                "collateral_superficial_veins": False,
                "previous_dvt": False,
                "alternative_diagnosis_more_likely": False,
            }
        )
        wells_pe = self.registry.get("wells_pe")(
            {
                "clinical_signs_dvt": True,
                "pe_more_likely_than_alternative": True,
                "heart_rate_bpm": 118,
                "immobilization_or_recent_surgery": False,
                "previous_dvt_pe": False,
                "hemoptysis": False,
                "malignancy": False,
            }
        )
        heart_score = self.registry.get("heart_score")(
            {
                "history_score": 2,
                "ecg_score": 1,
                "troponin_score": 1,
                "age": 67,
                "risk_factor_count": 3,
            }
        )
        self.assertEqual(wells_dvt["risk_level"], "高风险")
        self.assertEqual(wells_pe["risk_level"], "高风险")
        self.assertEqual(heart_score["risk_level"], "高风险")

    def test_metabolic_scores(self) -> None:
        findrisc = self.registry.get("findrisc")(
            {
                "age": 58,
                "bmi": 31,
                "waist_cm": 106,
                "gender": "男",
                "physically_active_daily": False,
                "daily_fruits_vegetables": False,
                "antihypertensive_medication": True,
                "history_high_blood_glucose": True,
                "family_history_diabetes": "first_degree",
            }
        )
        metabolic_syndrome = self.registry.get("metabolic_syndrome")(
            {
                "waist_cm": 96,
                "gender": "男",
                "systolic_bp": 138,
                "diastolic_bp": 88,
                "fasting_glucose": 6.0,
                "triglycerides_mmol_l": 2.1,
                "hdl_mmol_l": 0.9,
            }
        )
        nafld_fibrosis = self.registry.get("nafld_fibrosis")(
            {
                "age": 58,
                "bmi": 31.2,
                "ast_u_l": 42,
                "alt_u_l": 35,
                "platelet_10e9_l": 180,
                "albumin_g_dl": 4.0,
                "impaired_fasting_glucose_or_diabetes": True,
            }
        )
        self.assertEqual(findrisc["risk_level"], "极高风险")
        self.assertEqual(metabolic_syndrome["risk_level"], "符合代谢综合征")
        self.assertIn(nafld_fibrosis["risk_level"], {"不确定风险", "高风险"})


if __name__ == "__main__":
    unittest.main()
