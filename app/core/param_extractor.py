from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class ParameterIssue:
    name: str
    value: Any
    message: str


@dataclass
class ParameterExtractionResult:
    params: dict[str, Any] = field(default_factory=dict)
    invalid_params: list[ParameterIssue] = field(default_factory=list)
    source: str = "rules"


class ParamExtractor:
    RANGE_LIMITS = {
        "age": (0, 120, "年龄需要在 0 到 120 岁之间。"),
        "temperature_c": (30, 45, "体温需要在 30 到 45 ℃ 之间。"),
        "heart_rate_bpm": (20, 220, "心率需要在 20 到 220 次/分之间。"),
        "height_cm": (50, 250, "身高需要在 50 到 250 cm 之间。"),
        "weight_kg": (30, 200, "体重需要在 30 到 200 kg 之间。"),
        "systolic_bp": (50, 300, "收缩压需要在 50 到 300 mmHg 之间。"),
        "diastolic_bp": (30, 200, "舒张压需要在 30 到 200 mmHg 之间。"),
        "fasting_glucose": (1, 50, "空腹血糖需要在 1 到 50 mmol/L 之间。"),
        "waist_cm": (30, 200, "腰围需要在 30 到 200 cm 之间。"),
    }

    CHINESE_DIGITS = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def extract(self, text: str, profile: dict[str, Any]) -> ParameterExtractionResult:
        normalized = self._normalize_chinese_numbers(text)
        params = self._extract_with_rules(normalized)
        source = "rules"

        llm_params = self._extract_with_llm(normalized, existing=params)
        if llm_params:
            params.update({key: value for key, value in llm_params.items() if key not in params})
            source = "hybrid"

        validated_params, invalid_params = self._validate(params)
        if not validated_params.get("age") and profile.get("age") is not None:
            validated_params["age"] = profile["age"]
        if not validated_params.get("gender") and profile.get("gender"):
            validated_params["gender"] = profile["gender"]

        return ParameterExtractionResult(params=validated_params, invalid_params=invalid_params, source=source)

    def merge_with_profile(self, params: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        merged = dict(profile.get("params", {}))
        merged.update(params)
        if profile.get("age") is not None:
            merged.setdefault("age", profile["age"])
        if profile.get("gender"):
            merged.setdefault("gender", profile["gender"])
        return merged

    def _extract_with_rules(self, text: str) -> dict[str, Any]:
        params: dict[str, Any] = {}

        temperature_match = re.search(
            r"(?:体温|温度)(?:是|为)?\s*(\d{2}(?:\.\d+)?)\s*(?:℃|度|c)?",
            text,
            re.IGNORECASE,
        )
        if temperature_match:
            params["temperature_c"] = self._normalize_number(float(temperature_match.group(1)))

        heart_rate_match = re.search(
            r"(?:静息)?(?:心率|脉搏|心跳)(?:是|为)?\s*(\d{2,3})\s*(?:次/分|次每分|bpm)?",
            text,
            re.IGNORECASE,
        )
        if heart_rate_match:
            params["heart_rate_bpm"] = int(heart_rate_match.group(1))

        height_match = re.search(
            r"(?:身高|高)(?:是|为)?\s*(\d{1,3}(?:\.\d+)?)\s*(cm|厘米|米|m)?",
            text,
            re.IGNORECASE,
        )
        if height_match:
            value = float(height_match.group(1))
            unit = (height_match.group(2) or "cm").lower()
            params["height_cm"] = round(value * 100, 1) if unit in {"米", "m"} else self._normalize_number(value)

        weight_match = re.search(
            r"(?:体重|重)(?:是|为)?\s*(\d{1,3}(?:\.\d+)?)\s*(kg|公斤|千克|斤)?",
            text,
            re.IGNORECASE,
        )
        if weight_match:
            value = float(weight_match.group(1))
            unit = weight_match.group(2) or "kg"
            weight_kg = value / 2 if unit == "斤" else value
            params["weight_kg"] = round(weight_kg, 1) if not weight_kg.is_integer() else int(weight_kg)

        blood_pressure_match = re.search(r"(?:血压)?\s*(\d{2,3})\s*/\s*(\d{2,3})", text)
        if blood_pressure_match:
            params["systolic_bp"] = int(blood_pressure_match.group(1))
            params["diastolic_bp"] = int(blood_pressure_match.group(2))

        systolic_match = re.search(r"(?:收缩压)(?:是|为)?\s*(\d{2,3})", text)
        if systolic_match:
            params["systolic_bp"] = int(systolic_match.group(1))

        diastolic_match = re.search(r"(?:舒张压)(?:是|为)?\s*(\d{2,3})", text)
        if diastolic_match:
            params["diastolic_bp"] = int(diastolic_match.group(1))

        glucose_match = re.search(
            r"(?:空腹)?血糖(?:是|为)?\s*(\d{1,2}(?:\.\d+)?)\s*(?:mmol/?l)?",
            text,
            re.IGNORECASE,
        )
        if glucose_match:
            params["fasting_glucose"] = self._normalize_number(float(glucose_match.group(1)))

        waist_match = re.search(
            r"(?:腰围)(?:是|为)?\s*(\d{2,3}(?:\.\d+)?)\s*(?:cm|厘米)?",
            text,
            re.IGNORECASE,
        )
        if waist_match:
            params["waist_cm"] = self._normalize_number(float(waist_match.group(1)))

        age_match = re.search(r"(\d{1,3})\s*岁", text)
        if age_match:
            params["age"] = int(age_match.group(1))

        if "男" in text and "男女" not in text:
            params["gender"] = "男"
        elif "女" in text and "男女" not in text:
            params["gender"] = "女"

        balance_level = self._extract_balance_ability(text)
        if balance_level:
            params["balance_ability"] = balance_level

        return params

    def _extract_with_llm(self, text: str, existing: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            return {}

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "你是居家健康系统的参数提取器。"
                                "只输出 JSON。可提取字段仅限 age、gender、height_cm、weight_kg、"
                                "systolic_bp、diastolic_bp、fasting_glucose、temperature_c、"
                                "heart_rate_bpm、waist_cm、balance_ability。"
                                "如果没有提到某个字段，不要猜测。所有数值统一使用标准单位。"
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"已通过规则提取的参数：{existing}。请从以下文本补充遗漏参数：{text}",
                        },
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                timeout=15,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = requests.models.complexjson.loads(content)
            return {
                key: value
                for key, value in parsed.items()
                if key in {
                    "age",
                    "gender",
                    "height_cm",
                    "weight_kg",
                    "systolic_bp",
                    "diastolic_bp",
                    "fasting_glucose",
                    "temperature_c",
                    "heart_rate_bpm",
                    "waist_cm",
                    "balance_ability",
                }
                and value is not None
            }
        except Exception:
            return {}

    def _validate(self, params: dict[str, Any]) -> tuple[dict[str, Any], list[ParameterIssue]]:
        validated: dict[str, Any] = {}
        invalid_params: list[ParameterIssue] = []
        for name, value in params.items():
            if name not in self.RANGE_LIMITS:
                validated[name] = value
                continue
            minimum, maximum, message = self.RANGE_LIMITS[name]
            numeric_value = float(value)
            if minimum <= numeric_value <= maximum:
                validated[name] = value
            else:
                invalid_params.append(ParameterIssue(name=name, value=value, message=message))
        return validated, invalid_params

    def _normalize_chinese_numbers(self, text: str) -> str:
        pattern = re.compile(r"[零一二两三四五六七八九十百点半]+")

        def repl(match: re.Match[str]) -> str:
            raw = match.group(0)
            if raw == "半":
                return "0.5"
            converted = self._parse_chinese_number(raw)
            return str(converted) if converted is not None else raw

        return pattern.sub(repl, text)

    def _parse_chinese_number(self, text: str) -> float | int | None:
        if not text:
            return None
        if text == "半":
            return 0.5

        if "点" in text:
            integer_part, decimal_part = text.split("点", maxsplit=1)
            integer_value = self._parse_chinese_integer(integer_part) if integer_part else 0
            decimal_digits = []
            for char in decimal_part:
                if char == "半":
                    decimal_digits.append("5")
                elif char in self.CHINESE_DIGITS:
                    decimal_digits.append(str(self.CHINESE_DIGITS[char]))
            if not decimal_digits:
                return integer_value
            return float(f"{integer_value}.{''.join(decimal_digits)}")

        return self._parse_chinese_integer(text)

    def _parse_chinese_integer(self, text: str) -> int:
        if not text:
            return 0
        if all(char in self.CHINESE_DIGITS for char in text):
            return int("".join(str(self.CHINESE_DIGITS[char]) for char in text))

        total = 0
        current_digit = 0
        for char in text:
            if char in self.CHINESE_DIGITS:
                current_digit = self.CHINESE_DIGITS[char]
            elif char == "十":
                total += (current_digit or 1) * 10
                current_digit = 0
            elif char == "百":
                total += (current_digit or 1) * 100
                current_digit = 0
        return total + current_digit

    @staticmethod
    def _normalize_number(value: float) -> int | float:
        return int(value) if float(value).is_integer() else round(value, 1)

    @staticmethod
    def _extract_balance_ability(text: str) -> str | None:
        high_risk_terms = ("步态不稳", "站不稳", "需搀扶", "易跌倒", "曾跌倒", "平衡较差", "平衡差")
        medium_terms = ("平衡一般", "尚可", "偶有不稳", "稍差")
        low_risk_terms = ("步态稳定", "平衡良好", "平衡正常", "平稳", "无跌倒")

        if any(term in text for term in high_risk_terms):
            return "较差"
        if any(term in text for term in medium_terms):
            return "一般"
        if any(term in text for term in low_risk_terms):
            return "良好"
        return None
