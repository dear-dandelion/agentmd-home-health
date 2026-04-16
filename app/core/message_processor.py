from __future__ import annotations

from typing import Any

from app.calculators.repository import CalculatorRepository
from app.core.calculator_invoker import CalculatorInvoker
from app.core.intent_recognizer import IntentRecognizer
from app.core.param_extractor import ParamExtractor
from app.core.response_formatter import ResponseFormatter
from app.core.state_machine import StateMachine
from app.core.tool_selector import ToolSelector
from app.data.data_access import DataAccess
from app.data.models import MessageResult


NUMERIC_PARAM_FIELDS = {
    "temperature_c",
    "heart_rate_bpm",
    "respiratory_rate_bpm",
    "height_cm",
    "weight_kg",
    "systolic_bp",
    "diastolic_bp",
    "fasting_glucose",
    "waist_cm",
    "age",
}


class MessageProcessor:
    def __init__(self, data_access: DataAccess) -> None:
        self.data_access = data_access
        self.calculator_repository = CalculatorRepository()
        self.intent_recognizer = IntentRecognizer()
        self.param_extractor = ParamExtractor()
        self.state_machine = StateMachine()
        self.tool_selector = ToolSelector(self.calculator_repository.tool_definitions())
        self.calculator_invoker = CalculatorInvoker(self.calculator_repository)
        self.response_formatter = ResponseFormatter()

    def process(self, user_id: int, text: str, dialog_state: dict[str, Any] | None = None) -> MessageResult:
        profile = self.data_access.get_user(user_id)
        state = self.state_machine.restore(dialog_state)
        state = self.state_machine.reset_if_timed_out(state)

        intent_result = self.intent_recognizer.recognize(text)
        extraction = self.param_extractor.extract(text, profile)
        state.collected_params.update(extraction.params)
        intent = "quantitative_assessment" if state.pending_tool else intent_result["intent"]
        merged_params = self.param_extractor.merge_with_profile(state.collected_params, profile)

        if extraction.invalid_params:
            active_tool = state.pending_tool or self.tool_selector.select(text, merged_params)
            if active_tool:
                required_params = self.tool_selector.required_params(active_tool)
                next_state = self.state_machine.enter_collecting(
                    tool_name=active_tool,
                    intent=intent,
                    required_params=required_params,
                    collected_params=state.collected_params,
                )
            else:
                next_state = self.state_machine.enter_idle()
            reply = self.state_machine.build_invalid_param_prompt(extraction.invalid_params)
            return MessageResult(reply_text=reply, card_html="", state=next_state)

        if intent == "profile_update":
            if extraction.params:
                self.data_access.upsert_params(user_id, extraction.params, source="dialog_profile_update")
                refreshed = self.data_access.get_user(user_id)
                reply = "已更新档案参数：" + "，".join(f"{k}={v}" for k, v in extraction.params.items())
                card_html = self.response_formatter.format_profile_card(refreshed)
                return MessageResult(reply_text=reply, card_html=card_html, state=self.state_machine.enter_idle())
            reply = "请明确告诉我需要更新的档案参数，例如“身高170cm，体重65kg”。"
            return MessageResult(reply_text=reply, card_html="", state=self.state_machine.enter_idle())

        if intent == "profile_query":
            reply = "这是当前档案摘要。"
            card_html = self.response_formatter.format_profile_card(profile)
            return MessageResult(reply_text=reply, card_html=card_html, state=self.state_machine.enter_idle())

        if intent == "smalltalk" and not state.pending_tool:
            reply = "你好，我可以帮你做居家健康咨询、档案管理和量化评估。"
            return MessageResult(reply_text=reply, card_html="", state=self.state_machine.enter_idle())

        if intent == "health_consultation" and not state.pending_tool:
            reply = self._build_health_consultation_reply(text, profile)
            return MessageResult(reply_text=reply, card_html="", state=self.state_machine.enter_idle())

        tool = state.pending_tool or self.tool_selector.select(text, merged_params)
        if not tool:
            reply = self._build_unsupported_assessment_reply(text, profile)
            return MessageResult(reply_text=reply, card_html="", state=self.state_machine.enter_idle())

        required_params = self.tool_selector.required_params(tool)
        missing_params = [name for name in required_params if name not in merged_params]
        next_state, follow_up = self.state_machine.transition(
            intent=intent,
            collected_params=merged_params,
            required_params=required_params,
            tool_name=tool,
            missing_params=missing_params,
        )

        if next_state.state == "Collecting":
            return MessageResult(reply_text=follow_up, card_html="", state=next_state)

        result = self.calculator_invoker.invoke(tool, merged_params)
        assessment_params = {
            name: self._normalize_param_value(name, merged_params[name])
            for name in required_params
            if name in merged_params
        }
        result.setdefault("details", {})
        result["details"]["input_params"] = assessment_params
        if extraction.params:
            self.data_access.upsert_params(user_id, extraction.params, source="dialog_assessment_params")
        calculator_name = (
            result["details"].get("display_name")
            or result["details"].get("tool_name")
            or tool
        )
        self.data_access.create_assessment(
            user_id=user_id,
            calculator_name=str(calculator_name),
            input_params=assessment_params,
            result=result,
        )

        reply_text, card_html = self.response_formatter.format_result(result)
        return MessageResult(reply_text=reply_text, card_html=card_html, state=self.state_machine.enter_idle(), result=result)

    @staticmethod
    def _normalize_param_value(name: str, value: Any) -> Any:
        if name not in NUMERIC_PARAM_FIELDS or isinstance(value, (int, float)):
            return value
        try:
            number = float(str(value))
        except (TypeError, ValueError):
            return value
        return int(number) if number.is_integer() else round(number, 1)

    def _build_health_consultation_reply(self, text: str, profile: dict[str, Any]) -> str:
        topic = self._detect_topic(text)
        params = dict(profile.get("params", {}))

        if topic == "sleep":
            sleep_hint = str(params.get("sleep_quality", "")).strip()
            prefix = f"我看到你想咨询睡眠情况。当前档案里的睡眠记录是：{sleep_hint}。" if sleep_hint else "我看到你想咨询睡眠情况。"
            return (
                f"{prefix} 如果你愿意，我可以先按最近 7 天帮你梳理睡眠问题。"
                "请继续告诉我入睡是否困难、夜间醒来几次、总睡眠时长，以及白天是否困倦。"
            )

        if topic == "diet":
            glucose = params.get('fasting_glucose')
            weight = params.get('weight_kg')
            hint_parts = []
            if glucose not in (None, ""):
                hint_parts.append(f"空腹血糖 {glucose} mmol/L")
            if weight not in (None, ""):
                hint_parts.append(f"体重 {weight} kg")
            hint = f" 当前档案相关信息有：{'，'.join(hint_parts)}。" if hint_parts else ""
            return (
                f"你现在更关注饮食管理。{hint}"
                "如果你告诉我目标是控糖、减脂、控压还是改善睡眠，我可以按这个方向给你更具体的饮食建议。"
            )

        if topic == "exercise":
            return (
                "你现在更关注运动建议。请告诉我你的目标是减重、控压、改善体能还是预防跌倒，"
                "以及每周大概能运动几次，我可以给你更贴合的居家运动建议。"
            )

        if topic == "mood":
            return (
                "我看到你在关注情绪或心理状态。你可以继续告诉我这种情况持续了多久，"
                "主要是焦虑、情绪低落、易怒，还是影响到了睡眠和日常活动，我会先帮你梳理。"
            )

        if topic == "medication":
            return (
                "如果你想咨询用药问题，请告诉我药名、剂量、服用频率，以及你担心的是副作用、漏服，还是和当前症状的关系。"
            )

        return "我可以先帮你做健康信息梳理。你可以直接告诉我你现在最想解决的是睡眠、饮食、运动、情绪，还是血压血糖这类指标，我会按你的问题继续判断。"

    def _build_unsupported_assessment_reply(self, text: str, profile: dict[str, Any]) -> str:
        topic = self._detect_topic(text)
        params = dict(profile.get("params", {}))

        if topic == "sleep":
            sleep_hint = str(params.get("sleep_quality", "")).strip()
            suffix = f" 当前档案记录的睡眠情况是：{sleep_hint}。" if sleep_hint else ""
            return (
                "目前系统还没有“睡眠情况”的量化计算器。"
                f"{suffix} 但我可以先帮你做睡眠问题梳理。请告诉我最近一周的入睡困难、夜间醒来次数、总睡眠时长和白天困倦情况。"
            )

        if topic == "diet":
            return "目前系统还没有单独的饮食量化计算器，但我可以根据你的控糖、控压、减脂目标给出针对性的饮食建议。"

        if topic == "exercise":
            return "目前系统还没有单独的运动量化计算器，但我可以根据你的目标和体力情况，给你整理适合的居家运动建议。"

        if topic == "mood":
            return "目前系统还没有情绪量化评估器接入，但如果你愿意描述持续时间和主要表现，我可以先帮你做症状梳理。"

        supported = "目前可直接评估的项目包括 BMI、血压、空腹血糖、腰围、静息心率、体温和跌倒风险。"
        return f"暂时还没有与你这个问题完全对应的量化评估器。{supported}"

    @staticmethod
    def _detect_topic(text: str) -> str:
        lowered = text.lower()
        topic_keywords = {
            "sleep": ("睡眠", "失眠", "入睡", "早醒", "夜醒", "睡不好", "困倦"),
            "diet": ("饮食", "吃饭", "食谱", "减脂", "控糖", "控盐", "营养"),
            "exercise": ("运动", "锻炼", "走路", "慢走", "有氧", "力量训练"),
            "mood": ("情绪", "焦虑", "抑郁", "烦躁", "压力", "心情"),
            "medication": ("用药", "吃药", "药物", "副作用", "漏服"),
        }
        for topic, keywords in topic_keywords.items():
            if any(keyword in text or keyword in lowered for keyword in keywords):
                return topic
        return "general"
