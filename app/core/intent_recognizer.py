from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any
import json

import requests


class IntentRecognizer:
    LABELS = [
        "health_consultation",
        "quantitative_assessment",
        "profile_query",
        "profile_update",
        "smalltalk",
    ]

    INTENT_DEFINITIONS = {
        "health_consultation": "用户在询问健康知识、症状建议或一般性健康管理问题。",
        "quantitative_assessment": "用户希望进行某种量化评估、风险评分或医疗计算。",
        "profile_query": "用户在查询个人档案、既往记录或已保存的健康参数。",
        "profile_update": "用户在新增、修改或保存个人档案参数。",
        "smalltalk": "用户只是在打招呼、寒暄或进行无医学目标的闲聊。",
    }
    DEFAULT_RULE_KEYWORDS = {
        "profile_update": [
            "更新档案",
            "修改档案",
            "保存",
            "记录",
            "补充",
            "我的身高",
            "我的体重",
            "我今年",
            "今天血压",
            "今天体重",
            "记录一下",
        ],
        "profile_query": [
            "档案",
            "资料",
            "我的信息",
            "我的情况",
            "历史记录",
            "评估记录",
            "我的记录",
            "我的档案",
        ],
        "quantitative_assessment": [
            "评估",
            "风险",
            "评分",
            "量表",
            "计算",
            "指数",
            "bmi",
            "血压",
            "血糖",
            "体温",
            "心率",
            "脉搏",
            "腰围",
            "跌倒",
            "平衡",
            "糖尿病",
            "心血管",
            "睡眠评估",
        ],
        "smalltalk": [
            "你好",
            "谢谢",
            "在吗",
            "聊聊",
            "早上好",
            "晚上好",
            "嗨",
            "hello",
            "hi",
        ],
    }

    def __init__(self, confidence_threshold: float = 0.7, keyword_config_path: str | None = None) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.confidence_threshold = confidence_threshold
        self.keyword_config_path = Path(keyword_config_path) if keyword_config_path else Path(__file__).resolve().parents[2] / "data" / "intent_keywords.json"
        self.rule_keywords = self._load_rule_keywords()

    def recognize(self, text: str) -> dict[str, Any]:
        raw_text = text
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return self._build_result(
                intent="smalltalk",
                confidence=0.5,
                source="default",
                raw_text=raw_text,
                normalized_text=normalized_text,
                fallback_used=False,
            )

        llm_raw_output = None
        if self.api_key:
            try:
                result = self._recognize_with_llm(normalized_text)
                llm_raw_output = result.pop("raw_llm_output", None)
                if result["confidence"] >= self.confidence_threshold:
                    return self._build_result(
                        intent=result["intent"],
                        confidence=result["confidence"],
                        source="llm",
                        raw_text=raw_text,
                        normalized_text=normalized_text,
                        fallback_used=False,
                        raw_llm_output=llm_raw_output,
                    )
            except Exception as exc:
                llm_raw_output = str(exc)
                pass

        rule_result = self._recognize_with_rules(normalized_text)
        return self._build_result(
            intent=rule_result["intent"],
            confidence=rule_result["confidence"],
            source="rules",
            raw_text=raw_text,
            normalized_text=normalized_text,
            fallback_used=bool(self.api_key),
            raw_llm_output=llm_raw_output,
        )

    def _recognize_with_llm(self, text: str) -> dict[str, Any]:
        system_prompt = (
            "你是居家健康智能对话系统的意图分类器。\n"
            "你的任务是根据用户输入，在以下五类意图中选择唯一一个最合适的类别：\n"
            "1. health_consultation：用户在询问健康知识、症状建议、生活方式建议或一般健康管理问题。\n"
            "2. quantitative_assessment：用户希望进行某种量化评估、风险评分、指数计算或医学计算。\n"
            "3. profile_query：用户在查询个人健康档案、既往记录、历史评估结果或已保存参数。\n"
            "4. profile_update：用户在新增、修改、记录、补充个人健康档案参数。\n"
            "5. smalltalk：用户只是在打招呼、寒暄或进行无明确医学目标的闲聊。\n"
            "要求：\n"
            "- 只输出 JSON\n"
            "- JSON 必须包含 intent 和 confidence 两个字段\n"
            "- intent 必须是上述五个标签之一\n"
            "- confidence 取值范围为 0 到 1\n"
            "- 不要输出解释，不要输出额外字段"
        )
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"用户输入：{text}"},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = self._parse_llm_json(content)
        intent = str(parsed.get("intent", "")).strip()
        confidence = float(parsed.get("confidence", 0.0))
        if intent not in self.LABELS:
            raise ValueError(f"Unknown intent returned by LLM: {intent}")
        if not 0 <= confidence <= 1:
            raise ValueError(f"Invalid confidence returned by LLM: {confidence}")
        return {"intent": intent, "confidence": confidence, "source": "llm", "raw_llm_output": content}

    def _recognize_with_rules(self, text: str) -> dict[str, Any]:
        if self._contains_any(text, self.rule_keywords.get("profile_update", [])):
            return {"intent": "profile_update", "confidence": 0.85}

        if self._contains_any(text, self.rule_keywords.get("profile_query", [])):
            return {"intent": "profile_query", "confidence": 0.8}

        if self._contains_any(text, self.rule_keywords.get("quantitative_assessment", [])):
            return {"intent": "quantitative_assessment", "confidence": 0.86}

        if self._contains_any(text, self.rule_keywords.get("smalltalk", [])):
            return {"intent": "smalltalk", "confidence": 0.75}

        return {"intent": "health_consultation", "confidence": 0.65}

    def _load_rule_keywords(self) -> dict[str, list[str]]:
        if self.keyword_config_path.exists():
            try:
                with self.keyword_config_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                return {
                    key: [str(item).strip().lower() for item in value if str(item).strip()]
                    for key, value in payload.items()
                    if key in self.DEFAULT_RULE_KEYWORDS and isinstance(value, list)
                } | {
                    key: value
                    for key, value in self.DEFAULT_RULE_KEYWORDS.items()
                    if key not in payload
                }
            except Exception:
                pass
        return {
            key: [item.strip().lower() for item in values if item.strip()]
            for key, values in self.DEFAULT_RULE_KEYWORDS.items()
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = normalized.strip().lower()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    @staticmethod
    def _parse_llm_json(content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return requests.models.complexjson.loads(cleaned)

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _build_result(
        *,
        intent: str,
        confidence: float,
        source: str,
        raw_text: str,
        normalized_text: str,
        fallback_used: bool,
        raw_llm_output: str | None = None,
    ) -> dict[str, Any]:
        return {
            "intent": intent,
            "confidence": confidence,
            "source": source,
            "fallback_used": fallback_used,
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "raw_llm_output": raw_llm_output,
        }
