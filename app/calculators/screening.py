from __future__ import annotations

import os
from typing import Any

import requests


class BooleanLiteratureScreener:
    def __init__(self, keywords: list[str] | None = None, min_year: int = 2016) -> None:
        self.keywords = keywords or ["评分", "量表", "风险", "计算器", "预测模型"]
        self.min_year = min_year

    def screen(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        screened: list[dict[str, Any]] = []
        for document in documents:
            year = int(document.get("year", 0))
            text = " ".join(
                str(document.get(field, ""))
                for field in ("title", "abstract", "keywords", "source")
            ).lower()
            if year < self.min_year:
                continue
            if any(keyword.lower() in text for keyword in self.keywords):
                screened.append(document)
        return screened


class DeepSeekLiteratureReviewer:
    REQUIRED_STANDARDS = (
        "明确定义评分规则",
        "有明确输入参数",
        "有风险分级输出",
        "适用于居家场景",
        "有中文支持",
    )

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def review(self, document: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            text = " ".join(str(document.get(field, "")) for field in ("title", "abstract", "keywords"))
            passed = all(keyword in text for keyword in ("评分", "输入", "风险"))
            return {
                "passed": passed,
                "mode": "rule_fallback",
                "matched_standards": list(self.REQUIRED_STANDARDS) if passed else [],
            }

        prompt = (
            "Assess whether the following paper is suitable for a home-health calculator library. "
            "Return JSON only with passed(boolean), matched_standards(list), and reason(string). "
            f"Document: {document}"
        )
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        response.raise_for_status()
        return requests.models.complexjson.loads(response.json()["choices"][0]["message"]["content"])


class LiteratureScreeningPipeline:
    def __init__(
        self,
        boolean_screener: BooleanLiteratureScreener | None = None,
        llm_reviewer: DeepSeekLiteratureReviewer | None = None,
    ) -> None:
        self.boolean_screener = boolean_screener or BooleanLiteratureScreener()
        self.llm_reviewer = llm_reviewer or DeepSeekLiteratureReviewer()

    def run(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        first_pass = self.boolean_screener.screen(documents)
        admitted: list[dict[str, Any]] = []
        for document in first_pass:
            review = self.llm_reviewer.review(document)
            if review.get("passed"):
                admitted.append({"document": document, "review": review})
        return admitted
