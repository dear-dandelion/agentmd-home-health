from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import requests

from app.calculators.registry import CalculatorRegistry
from app.calculators.repository import CalculatorRepository
from app.core.message_processor import MessageProcessor
from app.data.data_access import DataAccess


DEFAULT_CASES_PATH = Path(__file__).resolve().parents[2] / "experiments" / "home_inquiry_ablation_cases.json"
DEFAULT_BASELINE_CACHE_PATH = Path(__file__).resolve().parents[2] / "experiments" / "results" / "deepseek_direct_cache.json"
BASE_CALCULATOR_PROMPTS_PER_TOOL = 10
TOTAL_TARGET_CASES = 513
STRICT_EXTRA_CASES = TOTAL_TARGET_CASES - 50 * BASE_CALCULATOR_PROMPTS_PER_TOOL
_CACHED_BENCHMARK_CASES: tuple["HomeInquiryBenchmarkCase", ...] | None = None
REFERENCE_STOPWORDS = {
    "常用",
    "参考",
    "依据",
    "提示",
    "综合",
    "评分",
    "分层",
    "成人",
    "家庭",
    "静息",
    "进一步",
    "医学",
    "评估",
    "总分",
    "当前",
    "水平",
    "建议",
    "风险",
    "正常",
}


@dataclass(frozen=True)
class HomeInquiryBenchmarkCase:
    id: str
    scenario_type: str
    birth_date: str
    gender: str
    seed_params: dict[str, Any]
    message: str
    source: str = "project_calculator_manifest"
    expected_tool: str | None = None
    expected_calculation_result: str | None = None
    expected_risk_level: str | None = None
    expected_numeric_reference: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HomeInquiryBenchmarkCase":
        return cls(
            id=str(payload["id"]),
            scenario_type=str(payload["scenario_type"]),
            birth_date=str(payload["birth_date"]),
            gender=str(payload["gender"]),
            seed_params=dict(payload.get("seed_params", {})),
            message=str(payload["message"]),
            source=str(payload.get("source", "project_calculator_manifest")),
            expected_tool=payload.get("expected_tool"),
            expected_calculation_result=payload.get("expected_calculation_result"),
            expected_risk_level=payload.get("expected_risk_level"),
            expected_numeric_reference=payload.get("expected_numeric_reference"),
        )


@dataclass(frozen=True)
class HomeInquiryCaseResult:
    variant: str
    case_id: str
    scenario_type: str
    strict_correct: bool
    calculation_result_correct: bool
    risk_level_correct: bool
    numeric_reference_correct: bool
    reply_text: str
    predicted_tool: str | None
    predicted_calculation_result: str | None
    predicted_risk_level: str | None
    predicted_numeric_reference: str | None


class DeepSeekDirectBaselineClient:
    def __init__(
        self,
        *,
        cache_path: str | Path | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout = timeout
        self.cache_path = Path(cache_path) if cache_path else DEFAULT_BASELINE_CACHE_PATH
        self._cache = self._load_cache()

    def evaluate_case(self, case: HomeInquiryBenchmarkCase) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

        cache_key = self._cache_key(case)
        if cache_key in self._cache:
            return dict(self._cache[cache_key])

        payload = self._request(case)
        result = {
            "calculation_result": str(payload.get("calculation_result", "")).strip(),
            "risk_level": str(payload.get("risk_level", "")).strip(),
            "numeric_reference": str(payload.get("numeric_reference", "")).strip(),
        }
        self._cache[cache_key] = result
        self._save_cache()
        return result

    def _request(self, case: HomeInquiryBenchmarkCase) -> dict[str, Any]:
        system_prompt = (
            "你是居家健康问询对照实验中的医学回答基线模型。\n"
            "你的任务是：不使用任何外部工具、不依赖医疗计算器库，只根据用户问询和给定参数，"
            "直接给出量化评估结果。\n"
            "必须只输出 JSON，对象中仅包含以下 3 个字段：\n"
            "calculation_result: 计算结果，尽量保留原始分值/百分比/单位；\n"
            "risk_level: 风险等级；\n"
            "numeric_reference: 用于判断的数值参考、阈值或分层范围。\n"
            "不要输出解释性前后缀，不要输出 markdown。"
        )
        user_prompt = (
            f"用户问询：{case.message}\n"
            f"已知参数：{json.dumps(case.seed_params, ensure_ascii=False, sort_keys=True)}\n"
            "请直接完成对应评分或风险估计，并按要求返回 JSON。"
        )
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_json_payload(content)

    def _cache_key(self, case: HomeInquiryBenchmarkCase) -> str:
        payload = {
            "id": case.id,
            "message": case.message,
            "seed_params": case.seed_params,
            "expected_tool": case.expected_tool,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _load_cache(self) -> dict[str, dict[str, str]]:
        if not self.cache_path.exists():
            return {}
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        if not isinstance(payload, dict):
            return {}
        cleaned: dict[str, dict[str, str]] = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                cleaned[key] = {
                    "calculation_result": str(value.get("calculation_result", "")).strip(),
                    "risk_level": str(value.get("risk_level", "")).strip(),
                    "numeric_reference": str(value.get("numeric_reference", "")).strip(),
                }
        return cleaned

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def load_benchmark_cases(path: str | Path | None = None) -> list[HomeInquiryBenchmarkCase]:
    global _CACHED_BENCHMARK_CASES
    if path:
        cases_path = Path(path)
        payload = json.loads(cases_path.read_text(encoding="utf-8"))
        return [HomeInquiryBenchmarkCase.from_dict(item) for item in payload.get("cases", [])]
    if _CACHED_BENCHMARK_CASES is None:
        _CACHED_BENCHMARK_CASES = tuple(build_expanded_benchmark_cases())
    return list(_CACHED_BENCHMARK_CASES)


def build_expanded_benchmark_cases() -> list[HomeInquiryBenchmarkCase]:
    return _build_calculator_cases()


def run_full_system_variant(cases: list[HomeInquiryBenchmarkCase]) -> dict[str, Any]:
    records: list[HomeInquiryCaseResult] = []

    for case in cases:
        with TemporaryDirectory() as tmpdir:
            data_access = DataAccess(base_dir=tmpdir)
            user = data_access.create_user(name=case.id, birth_date=case.birth_date, gender=case.gender)
            if case.seed_params:
                data_access.upsert_params(user["user_id"], case.seed_params, source="ablation_seed")

            processor = MessageProcessor(data_access)
            processor.intent_recognizer.api_key = None
            processor.param_extractor.api_key = None
            message_result = processor.process(user["user_id"], case.message)

        result = message_result.result or {}
        details = result.get("details", {}) if isinstance(result, dict) else {}
        record = _build_case_result(
            variant="full_system",
            case=case,
            reply_text=message_result.reply_text,
            predicted_tool=str(details.get("tool_name")) if details.get("tool_name") is not None else None,
            predicted_calculation_result=_stringify_value(result.get("score")) if isinstance(result, dict) else None,
            predicted_risk_level=_stringify_value(result.get("risk_level")) if isinstance(result, dict) else None,
            predicted_numeric_reference=_extract_numeric_reference(result if isinstance(result, dict) else {}),
        )
        records.append(record)

    return _build_summary("full_system", records)


def run_deepseek_variant(
    cases: list[HomeInquiryBenchmarkCase],
    *,
    client: DeepSeekDirectBaselineClient | None = None,
) -> dict[str, Any]:
    baseline_client = client or DeepSeekDirectBaselineClient()
    records: list[HomeInquiryCaseResult] = []

    for case in cases:
        payload = baseline_client.evaluate_case(case)
        reply_text = json.dumps(payload, ensure_ascii=False)
        record = _build_case_result(
            variant="deepseek_direct",
            case=case,
            reply_text=reply_text,
            predicted_tool=None,
            predicted_calculation_result=_stringify_value(payload.get("calculation_result")),
            predicted_risk_level=_stringify_value(payload.get("risk_level")),
            predicted_numeric_reference=_stringify_value(payload.get("numeric_reference")),
        )
        records.append(record)

    return _build_summary("deepseek_direct", records)


def compare_variants(
    cases: list[HomeInquiryBenchmarkCase] | None = None,
    *,
    baseline_client: DeepSeekDirectBaselineClient | None = None,
) -> dict[str, Any]:
    benchmark_cases = cases or load_benchmark_cases()
    full_system = run_full_system_variant(benchmark_cases)
    deepseek_direct = run_deepseek_variant(benchmark_cases, client=baseline_client)
    return {
        "case_count": len(benchmark_cases),
        "full_system": full_system,
        "deepseek_direct": deepseek_direct,
        "strict_accuracy_delta": round(full_system["strict_accuracy"] - deepseek_direct["strict_accuracy"], 4),
        "calculation_result_accuracy_delta": round(
            full_system["calculation_result_accuracy"] - deepseek_direct["calculation_result_accuracy"],
            4,
        ),
        "risk_level_accuracy_delta": round(
            full_system["risk_level_accuracy"] - deepseek_direct["risk_level_accuracy"],
            4,
        ),
        "numeric_reference_accuracy_delta": round(
            full_system["numeric_reference_accuracy"] - deepseek_direct["numeric_reference_accuracy"],
            4,
        ),
    }


def _build_case_result(
    *,
    variant: str,
    case: HomeInquiryBenchmarkCase,
    reply_text: str,
    predicted_tool: str | None,
    predicted_calculation_result: str | None,
    predicted_risk_level: str | None,
    predicted_numeric_reference: str | None,
) -> HomeInquiryCaseResult:
    calculation_result_correct = _calculation_result_matches(
        predicted_calculation_result,
        case.expected_calculation_result,
    )
    risk_level_correct = _normalized_text(predicted_risk_level) == _normalized_text(case.expected_risk_level)
    numeric_reference_correct = _numeric_reference_matches(
        predicted_numeric_reference,
        case.expected_numeric_reference,
    )
    strict_correct = calculation_result_correct and risk_level_correct and numeric_reference_correct
    return HomeInquiryCaseResult(
        variant=variant,
        case_id=case.id,
        scenario_type=case.scenario_type,
        strict_correct=strict_correct,
        calculation_result_correct=calculation_result_correct,
        risk_level_correct=risk_level_correct,
        numeric_reference_correct=numeric_reference_correct,
        reply_text=reply_text,
        predicted_tool=predicted_tool,
        predicted_calculation_result=predicted_calculation_result,
        predicted_risk_level=predicted_risk_level,
        predicted_numeric_reference=predicted_numeric_reference,
    )


def _build_summary(variant_name: str, records: list[HomeInquiryCaseResult]) -> dict[str, Any]:
    total = len(records)
    strict_accuracy = _boolean_accuracy(item.strict_correct for item in records)
    return {
        "variant": variant_name,
        "strict_accuracy": strict_accuracy,
        "overall_accuracy": strict_accuracy,
        "calculation_result_accuracy": _boolean_accuracy(item.calculation_result_correct for item in records),
        "risk_level_accuracy": _boolean_accuracy(item.risk_level_correct for item in records),
        "numeric_reference_accuracy": _boolean_accuracy(item.numeric_reference_correct for item in records),
        "strict_correct_count": sum(1 for item in records if item.strict_correct),
        "overall_correct_count": sum(1 for item in records if item.strict_correct),
        "calculation_result_correct_count": sum(1 for item in records if item.calculation_result_correct),
        "risk_level_correct_count": sum(1 for item in records if item.risk_level_correct),
        "numeric_reference_correct_count": sum(1 for item in records if item.numeric_reference_correct),
        "total_count": total,
        "records": [asdict(item) for item in records],
    }


def _boolean_accuracy(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(1 for item in items if item) / len(items), 4)


def _build_calculator_cases() -> list[HomeInquiryBenchmarkCase]:
    repository = CalculatorRepository()
    registry = CalculatorRegistry(repository)
    prepared: list[dict[str, Any]] = []

    for manifest in repository.list_manifests():
        example_input = dict(manifest.documentation["usage_examples"][0]["input"])
        result = registry.get(manifest.name)(dict(example_input))
        birth_date = _birth_date_from_example(example_input)
        gender = str(example_input.get("gender", "男"))
        trigger_keyword = _select_calculator_trigger_keyword(manifest.name, manifest.intent_keywords)
        valid_prompts = _select_valid_calculator_prompts(
            tool_name=manifest.name,
            trigger_keyword=trigger_keyword,
            birth_date=birth_date,
            gender=gender,
            seed_params=example_input,
            expected_calculation_result=_stringify_value(result.get("score")),
            expected_risk_level=_stringify_value(result.get("risk_level")),
            expected_numeric_reference=_extract_numeric_reference(result),
        )
        prepared.append(
            {
                "manifest": manifest,
                "seed_params": example_input,
                "birth_date": birth_date,
                "gender": gender,
                "expected_calculation_result": _stringify_value(result.get("score")),
                "expected_risk_level": _stringify_value(result.get("risk_level")),
                "expected_numeric_reference": _extract_numeric_reference(result),
                "valid_prompts": valid_prompts,
            }
        )

    cases: list[HomeInquiryBenchmarkCase] = []
    extras_remaining = STRICT_EXTRA_CASES
    for item in prepared:
        valid_prompts = list(item["valid_prompts"])
        prompt_count = BASE_CALCULATOR_PROMPTS_PER_TOOL
        if extras_remaining > 0 and len(valid_prompts) > BASE_CALCULATOR_PROMPTS_PER_TOOL:
            prompt_count += 1
            extras_remaining -= 1

        manifest = item["manifest"]
        for idx, prompt in enumerate(valid_prompts[:prompt_count], start=1):
            cases.append(
                HomeInquiryBenchmarkCase(
                    id=f"{manifest.name}_case_{idx}",
                    scenario_type="calculator",
                    birth_date=str(item["birth_date"]),
                    gender=str(item["gender"]),
                    seed_params=dict(item["seed_params"]),
                    message=prompt,
                    source="project_calculator_manifest",
                    expected_tool=manifest.name,
                    expected_calculation_result=str(item["expected_calculation_result"]),
                    expected_risk_level=str(item["expected_risk_level"]),
                    expected_numeric_reference=str(item["expected_numeric_reference"]),
                )
            )

    if extras_remaining != 0:
        raise ValueError(f"Unable to distribute {STRICT_EXTRA_CASES} extra calculator cases.")
    if len(cases) != TOTAL_TARGET_CASES:
        raise ValueError(f"Expected {TOTAL_TARGET_CASES} cases, got {len(cases)}.")
    return cases


def _select_calculator_trigger_keyword(tool_name: str, intent_keywords: list[str]) -> str:
    normalized_tool_name = _normalize_keyword(tool_name)
    exact_matches = [keyword for keyword in intent_keywords if _normalize_keyword(keyword) == normalized_tool_name]
    if exact_matches:
        return exact_matches[0]

    close_matches = [
        keyword
        for keyword in intent_keywords
        if normalized_tool_name in _normalize_keyword(keyword) or _normalize_keyword(keyword) in normalized_tool_name
    ]
    if close_matches:
        return close_matches[0]

    return str(intent_keywords[0] if intent_keywords else tool_name)


def _normalize_keyword(value: str) -> str:
    return "".join(char.lower() for char in str(value) if char.isalnum())


def _calculator_prompt_candidates(trigger_keyword: str) -> list[str]:
    return [
        f"请帮我计算 {trigger_keyword} 评分。",
        f"请直接评估 {trigger_keyword}，并给出结果。",
        f"我需要 {trigger_keyword} 的评估结果。",
        f"麻烦计算一下 {trigger_keyword}。",
        f"请用 {trigger_keyword} 做一次量化评估。",
        f"现在计算 {trigger_keyword}，并告诉我风险等级。",
        f"请按 {trigger_keyword} 直接完成评分。",
        f"我想做 {trigger_keyword} 评估。",
        f"请根据已有信息计算 {trigger_keyword}。",
        f"{trigger_keyword} 评分请直接给结果。",
        f"请立刻完成 {trigger_keyword} 的评分和风险分层。",
        f"用 {trigger_keyword} 算一下，并把参考范围也告诉我。",
        f"请基于当前参数给出 {trigger_keyword} 结果。",
        f"帮我做 {trigger_keyword} 的量化打分。",
        f"请返回 {trigger_keyword} 的计算结果、风险等级和参考阈值。",
    ]


def _select_valid_calculator_prompts(
    *,
    tool_name: str,
    trigger_keyword: str,
    birth_date: str,
    gender: str,
    seed_params: dict[str, Any],
    expected_calculation_result: str | None,
    expected_risk_level: str | None,
    expected_numeric_reference: str | None,
) -> list[str]:
    prompts: list[str] = []
    for prompt in _calculator_prompt_candidates(trigger_keyword):
        if _validate_calculator_prompt(
            tool_name=tool_name,
            prompt=prompt,
            birth_date=birth_date,
            gender=gender,
            seed_params=seed_params,
            expected_calculation_result=expected_calculation_result,
            expected_risk_level=expected_risk_level,
            expected_numeric_reference=expected_numeric_reference,
        ):
            prompts.append(prompt)
    if len(prompts) < BASE_CALCULATOR_PROMPTS_PER_TOOL:
        raise ValueError(f"Unable to build {BASE_CALCULATOR_PROMPTS_PER_TOOL} stable prompts for calculator: {tool_name}")
    return prompts


def _validate_calculator_prompt(
    *,
    tool_name: str,
    prompt: str,
    birth_date: str,
    gender: str,
    seed_params: dict[str, Any],
    expected_calculation_result: str | None,
    expected_risk_level: str | None,
    expected_numeric_reference: str | None,
) -> bool:
    with TemporaryDirectory() as tmpdir:
        data_access = DataAccess(base_dir=tmpdir)
        user = data_access.create_user(name="calculator_case", birth_date=birth_date, gender=gender)
        if seed_params:
            data_access.upsert_params(user["user_id"], seed_params, source="ablation_seed")

        processor = MessageProcessor(data_access)
        processor.intent_recognizer.api_key = None
        processor.param_extractor.api_key = None
        message_result = processor.process(user["user_id"], prompt)

    result = message_result.result or {}
    details = result.get("details", {}) if isinstance(result, dict) else {}
    predicted_tool = details.get("tool_name")
    predicted_calculation_result = _stringify_value(result.get("score")) if isinstance(result, dict) else None
    predicted_risk_level = _stringify_value(result.get("risk_level")) if isinstance(result, dict) else None
    predicted_numeric_reference = _extract_numeric_reference(result if isinstance(result, dict) else {})
    return (
        bool(message_result.result)
        and predicted_tool == tool_name
        and _calculation_result_matches(predicted_calculation_result, expected_calculation_result)
        and _normalized_text(predicted_risk_level) == _normalized_text(expected_risk_level)
        and _numeric_reference_matches(predicted_numeric_reference, expected_numeric_reference)
    )


def _extract_numeric_reference(result: dict[str, Any]) -> str | None:
    reference = result.get("reference") or result.get("guideline")
    return _stringify_value(reference)


def _stringify_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalized_text(value: str | None) -> str:
    if value is None:
        return ""
    lowered = str(value).strip().lower()
    lowered = re.sub(r"\s+", "", lowered)
    lowered = re.sub(r"[，。；：、,.!！?？（）()【】\[\]\"'`]+", "", lowered)
    return lowered


def _calculation_result_matches(predicted: str | None, expected: str | None) -> bool:
    if not predicted or not expected:
        return False
    predicted_numbers = _extract_numbers(predicted)
    expected_numbers = _extract_numbers(expected)
    if predicted_numbers and expected_numbers and len(predicted_numbers) == len(expected_numbers):
        return all(abs(left - right) <= 0.05 for left, right in zip(predicted_numbers, expected_numbers))
    return _normalized_text(predicted) == _normalized_text(expected)


def _numeric_reference_matches(predicted: str | None, expected: str | None) -> bool:
    if not predicted or not expected:
        return False
    if _normalized_text(predicted) == _normalized_text(expected):
        return True

    expected_numeric_tokens = _extract_numeric_tokens(expected)
    predicted_numeric_tokens = set(_extract_numeric_tokens(predicted))
    if expected_numeric_tokens and not all(token in predicted_numeric_tokens for token in expected_numeric_tokens):
        return False

    expected_keywords = _extract_reference_keywords(expected)
    predicted_keywords = set(_extract_reference_keywords(predicted))
    if not expected_keywords:
        return bool(expected_numeric_tokens)
    overlap = sum(1 for token in expected_keywords if token in predicted_keywords)
    return overlap / len(expected_keywords) >= 0.6


def _extract_numbers(value: str) -> list[float]:
    matches = re.findall(r"-?\d+(?:\.\d+)?", value)
    return [float(match) for match in matches]


def _extract_numeric_tokens(value: str) -> list[str]:
    token_pattern = r"(?:>=|<=|>|<)?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?%?"
    return [token.replace(" ", "") for token in re.findall(token_pattern, value)]


def _extract_reference_keywords(value: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z]+(?:-\d+)?|[\u4e00-\u9fff]{2,}", value)
    cleaned = []
    for token in tokens:
        token = token.lower()
        if token in REFERENCE_STOPWORDS:
            continue
        cleaned.append(token)
    unique = list(dict.fromkeys(cleaned))
    return unique


def _parse_json_payload(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _birth_date_from_example(example_input: dict[str, Any]) -> str:
    age = example_input.get("age")
    if age in (None, ""):
        return "1980-01-01"
    try:
        years = int(float(age))
    except (TypeError, ValueError):
        return "1980-01-01"
    year = max(1900, date.today().year - years)
    return f"{year:04d}-01-01"
