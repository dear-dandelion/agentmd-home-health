from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.data.models import DialogState


class StateMachine:
    def __init__(self, timeout_minutes: int = 30) -> None:
        self.timeout = timedelta(minutes=timeout_minutes)

    def restore(self, raw_state: dict[str, Any] | None) -> DialogState:
        if not raw_state:
            return self.enter_idle()

        last_active = raw_state.get("last_active_at")
        if isinstance(last_active, str):
            last_active = datetime.fromisoformat(last_active)

        return DialogState(
            state=raw_state.get("state", "Idle"),
            pending_tool=raw_state.get("pending_tool"),
            pending_intent=raw_state.get("pending_intent"),
            required_params=list(raw_state.get("required_params", [])),
            collected_params=dict(raw_state.get("collected_params", {})),
            last_active_at=last_active or datetime.now(),
        )

    def reset_if_timed_out(self, state: DialogState) -> DialogState:
        if state.last_active_at and datetime.now() - state.last_active_at > self.timeout:
            return self.enter_idle()
        state.last_active_at = datetime.now()
        return state

    def enter_idle(self) -> DialogState:
        return DialogState(state="Idle", last_active_at=datetime.now())

    def enter_collecting(
        self,
        *,
        tool_name: str,
        intent: str,
        required_params: list[str],
        collected_params: dict[str, Any],
    ) -> DialogState:
        return DialogState(
            state="Collecting",
            pending_tool=tool_name,
            pending_intent=intent,
            required_params=required_params,
            collected_params=collected_params,
            last_active_at=datetime.now(),
        )

    def enter_calculating(
        self,
        *,
        tool_name: str,
        intent: str,
        required_params: list[str],
        collected_params: dict[str, Any],
    ) -> DialogState:
        return DialogState(
            state="Calculating",
            pending_tool=tool_name,
            pending_intent=intent,
            required_params=required_params,
            collected_params=collected_params,
            last_active_at=datetime.now(),
        )

    def enter_responding(self) -> DialogState:
        return DialogState(state="Responding", last_active_at=datetime.now())

    def transition(
        self,
        *,
        intent: str,
        collected_params: dict[str, Any],
        required_params: list[str],
        tool_name: str,
        missing_params: list[str],
    ) -> tuple[DialogState, str]:
        if missing_params:
            prompt = self.build_follow_up(
                required_params=required_params,
                collected_params=collected_params,
                missing_params=missing_params,
            )
            return (
                self.enter_collecting(
                    tool_name=tool_name,
                    intent=intent,
                    required_params=required_params,
                    collected_params=collected_params,
                ),
                prompt,
            )

        return (
            self.enter_calculating(
                tool_name=tool_name,
                intent=intent,
                required_params=required_params,
                collected_params=collected_params,
            ),
            "",
        )

    @staticmethod
    def build_follow_up(
        *,
        required_params: list[str],
        collected_params: dict[str, Any],
        missing_params: list[str],
    ) -> str:
        available_params = [name for name in required_params if name in collected_params and name not in missing_params]
        available_text = "、".join(
            StateMachine._format_param_item(name, collected_params[name]) for name in available_params
        ) or "暂无"
        missing_text = "、".join(StateMachine._param_label(name) for name in missing_params)
        return f"当前已获得这些参数：{available_text}。还需要补充：{missing_text}。"

    @staticmethod
    def _param_label(name: str) -> str:
        labels = {
            "temperature_c": "体温（℃）",
            "heart_rate_bpm": "心率（次/分）",
            "height_cm": "身高（cm）",
            "weight_kg": "体重（kg）",
            "systolic_bp": "收缩压（mmHg）",
            "diastolic_bp": "舒张压（mmHg）",
            "fasting_glucose": "空腹血糖（mmol/L）",
            "waist_cm": "腰围（cm）",
            "age": "年龄",
            "gender": "性别",
            "balance_ability": "平衡能力",
        }
        return labels.get(name, name)

    @staticmethod
    def _param_unit(name: str) -> str:
        units = {
            "temperature_c": "℃",
            "heart_rate_bpm": "次/分",
            "height_cm": "cm",
            "weight_kg": "kg",
            "systolic_bp": "mmHg",
            "diastolic_bp": "mmHg",
            "fasting_glucose": "mmol/L",
            "waist_cm": "cm",
        }
        return units.get(name, "")

    @classmethod
    def _format_param_item(cls, name: str, value: Any) -> str:
        unit = cls._param_unit(name)
        display_value = f"{value}{unit}" if unit else str(value)
        return f"{cls._param_label(name)}={display_value}"

    @staticmethod
    def build_invalid_param_prompt(invalid_params: list[dict[str, Any]] | list[Any]) -> str:
        messages = []
        for item in invalid_params:
            if hasattr(item, "message"):
                messages.append(str(item.message))
            elif isinstance(item, dict):
                messages.append(str(item.get("message", "")))
        return "检测到参数超出合理范围：" + " ".join(messages) + " 请重新输入。"
