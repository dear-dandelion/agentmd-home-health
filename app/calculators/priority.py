from __future__ import annotations

from typing import Any

from app.calculators.metadata import PriorityProfile


class CalculatorPriorityScorer:
    WEIGHTS = {
        "home_suitability": 0.4,
        "clinical_importance": 0.3,
        "implementation_simplicity": 0.2,
        "chinese_support": 0.1,
    }

    @classmethod
    def score(cls, payload: dict[str, Any]) -> PriorityProfile:
        home_suitability = float(payload.get("home_suitability", 0))
        clinical_importance = float(payload.get("clinical_importance", 0))
        implementation_simplicity = float(payload.get("implementation_simplicity", 0))
        chinese_support = float(payload.get("chinese_support", 0))

        total_score = round(
            cls.WEIGHTS["home_suitability"] * home_suitability
            + cls.WEIGHTS["clinical_importance"] * clinical_importance
            + cls.WEIGHTS["implementation_simplicity"] * implementation_simplicity
            + cls.WEIGHTS["chinese_support"] * chinese_support,
            3,
        )
        return PriorityProfile(
            home_suitability=home_suitability,
            clinical_importance=clinical_importance,
            implementation_simplicity=implementation_simplicity,
            chinese_support=chinese_support,
            total_score=total_score,
            level=cls.classify(total_score),
        )

    @staticmethod
    def classify(score: float) -> str:
        if score > 0.75:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"
