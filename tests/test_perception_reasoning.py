from __future__ import annotations

from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
import unittest

from app.calculators.repository import CalculatorRepository
from app.core.intent_recognizer import IntentRecognizer
from app.core.message_processor import MessageProcessor
from app.core.param_extractor import ParamExtractor
from app.core.state_machine import StateMachine
from app.core.tool_selector import ToolSelector
from app.data.data_access import DataAccess


class PerceptionReasoningTests(unittest.TestCase):
    def test_intent_recognizer_falls_back_when_llm_confidence_is_low(self) -> None:
        recognizer = IntentRecognizer(confidence_threshold=0.7)
        recognizer.api_key = "dummy"
        recognizer._recognize_with_llm = lambda text: {  # type: ignore[method-assign]
            "intent": "health_consultation",
            "confidence": 0.4,
            "source": "llm",
            "raw_llm_output": '{"intent":"health_consultation","confidence":0.4}',
        }

        result = recognizer.recognize("帮我评估 BMI")

        self.assertEqual(result["intent"], "quantitative_assessment")
        self.assertEqual(result["source"], "rules")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["normalized_text"], "帮我评估 bmi")

    def test_intent_recognizer_returns_llm_result_when_confidence_is_high(self) -> None:
        recognizer = IntentRecognizer(confidence_threshold=0.7)
        recognizer.api_key = "dummy"
        recognizer._recognize_with_llm = lambda text: {  # type: ignore[method-assign]
            "intent": "profile_query",
            "confidence": 0.91,
            "source": "llm",
            "raw_llm_output": '{"intent":"profile_query","confidence":0.91}',
        }

        result = recognizer.recognize("看看我的档案")

        self.assertEqual(result["intent"], "profile_query")
        self.assertEqual(result["source"], "llm")
        self.assertFalse(result["fallback_used"])

    def test_intent_recognizer_normalizes_full_width_text(self) -> None:
        recognizer = IntentRecognizer()
        recognizer.api_key = None

        result = recognizer.recognize("  ＢＭＩ　评估  ")

        self.assertEqual(result["intent"], "quantitative_assessment")
        self.assertEqual(result["normalized_text"], "bmi 评估")

    def test_param_extractor_supports_chinese_numbers_and_unit_normalization(self) -> None:
        extractor = ParamExtractor()
        extractor.api_key = None
        result = extractor.extract(
            "我身高一百七十厘米，体重一百三十斤，今年六十五岁，空腹血糖六点一，血压一百三十九/八十九",
            {"age": None, "gender": None, "params": {}},
        )

        self.assertEqual(result.params["height_cm"], 170)
        self.assertEqual(result.params["weight_kg"], 65)
        self.assertEqual(result.params["age"], 65)
        self.assertEqual(result.params["fasting_glucose"], 6.1)
        self.assertEqual(result.params["systolic_bp"], 139)
        self.assertEqual(result.params["diastolic_bp"], 89)
        self.assertFalse(result.invalid_params)

    def test_param_extractor_supports_new_home_monitoring_fields(self) -> None:
        extractor = ParamExtractor()
        extractor.api_key = None
        result = extractor.extract(
            "我体温三十七点八度，心率七十二次，腰围八十八厘米，最近步态不稳",
            {"age": None, "gender": None, "params": {}},
        )

        self.assertEqual(result.params["temperature_c"], 37.8)
        self.assertEqual(result.params["heart_rate_bpm"], 72)
        self.assertEqual(result.params["waist_cm"], 88)
        self.assertEqual(result.params["balance_ability"], "较差")

    def test_param_extractor_returns_invalid_param_issue(self) -> None:
        extractor = ParamExtractor()
        extractor.api_key = None
        result = extractor.extract("我身高400cm，体重65kg", {"age": None, "gender": None, "params": {}})

        self.assertEqual(result.params["weight_kg"], 65)
        self.assertEqual(len(result.invalid_params), 1)
        self.assertEqual(result.invalid_params[0].name, "height_cm")

    def test_state_machine_resets_after_timeout(self) -> None:
        machine = StateMachine(timeout_minutes=30)
        state = machine.restore(
            {
                "state": "Collecting",
                "pending_tool": "bmi",
                "pending_intent": "quantitative_assessment",
                "required_params": ["height_cm", "weight_kg"],
                "collected_params": {"weight_kg": 65},
                "last_active_at": (datetime.now() - timedelta(minutes=31)).isoformat(),
            }
        )

        reset_state = machine.reset_if_timed_out(state)

        self.assertEqual(reset_state.state, "Idle")
        self.assertEqual(reset_state.collected_params, {})

    def test_tool_selector_prefers_keyword_match_before_param_completeness(self) -> None:
        selector = ToolSelector(CalculatorRepository().tool_definitions())
        selected = selector.select(
            "请帮我评估血压风险，我的身高170cm，体重65kg",
            {"height_cm": 170, "weight_kg": 65},
        )

        self.assertEqual(selected, "blood_pressure")

    def test_tool_selector_uses_param_completeness_then_specificity(self) -> None:
        selector = ToolSelector(CalculatorRepository().tool_definitions())
        selected = selector.select(
            "我想评估血糖和血压",
            {"systolic_bp": 130, "diastolic_bp": 85, "fasting_glucose": 6.1},
        )

        self.assertEqual(selected, "blood_pressure")

    def test_message_processor_returns_range_error_before_completeness_check(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_access = DataAccess(base_dir=tmpdir)
            user = data_access.create_user(name="测试用户", birth_date="1980-01-01", gender="女")
            processor = MessageProcessor(data_access)
            processor.param_extractor.api_key = None

            result = processor.process(user["user_id"], "帮我评估BMI，我身高400cm，体重65kg")

        self.assertIn("参数超出合理范围", result.reply_text)
        self.assertEqual(result.state.state, "Collecting")

    def test_message_processor_auto_saves_assessment_history(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_access = DataAccess(base_dir=tmpdir)
            user = data_access.create_user(name="测试用户", birth_date="1980-01-01", gender="女")
            processor = MessageProcessor(data_access)
            processor.param_extractor.api_key = None

            result = processor.process(user["user_id"], "帮我评估BMI，我身高170cm，体重65kg")
            assessments = data_access.list_assessments(user["user_id"])

        self.assertIn("评估完成", result.reply_text)
        self.assertEqual(len(assessments), 1)
        self.assertIn("BMI", assessments[0]["calculator_name"])

    def test_message_processor_only_keeps_assessment_related_input_params(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_access = DataAccess(base_dir=tmpdir)
            user = data_access.create_user(name="测试用户", birth_date="1980-01-01", gender="女")
            data_access.upsert_params(
                user["user_id"],
                {"height_cm": 170, "weight_kg": 65, "systolic_bp": 138, "diastolic_bp": 86},
                source="seed",
            )
            processor = MessageProcessor(data_access)
            processor.param_extractor.api_key = None

            result = processor.process(user["user_id"], "帮我评估BMI")
            assessments = data_access.list_assessments(user["user_id"])

        self.assertEqual(result.result["details"]["input_params"], {"height_cm": 170, "weight_kg": 65})
        self.assertEqual(assessments[0]["input_params"], {"height_cm": 170, "weight_kg": 65})

    def test_message_processor_returns_topic_specific_reply_for_unsupported_sleep_assessment(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_access = DataAccess(base_dir=tmpdir)
            user = data_access.create_user(name="测试用户", birth_date="1980-01-01", gender="女")
            data_access.upsert_params(user["user_id"], {"sleep_quality": "夜间醒1次，睡眠6小时"}, source="seed")
            processor = MessageProcessor(data_access)
            processor.param_extractor.api_key = None

            result = processor.process(user["user_id"], "帮我评估我最近的睡眠情况")

        self.assertIn("目前系统还没有“睡眠情况”的量化计算器", result.reply_text)
        self.assertIn("夜间醒1次，睡眠6小时", result.reply_text)

    def test_message_processor_returns_topic_specific_health_consultation_reply(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_access = DataAccess(base_dir=tmpdir)
            user = data_access.create_user(name="测试用户", birth_date="1980-01-01", gender="女")
            processor = MessageProcessor(data_access)
            processor.param_extractor.api_key = None

            result = processor.process(user["user_id"], "最近总是睡不好，半夜容易醒")

        self.assertIn("想咨询睡眠情况", result.reply_text)
        self.assertIn("最近 7 天", result.reply_text)

    def test_state_machine_follow_up_lists_current_and_missing_params(self) -> None:
        machine = StateMachine()

        prompt = machine.build_follow_up(
            required_params=["height_cm", "weight_kg"],
            collected_params={"height_cm": 170},
            missing_params=["weight_kg"],
        )

        self.assertEqual(prompt, "当前已获得这些参数：身高（cm）=170cm。还需要补充：体重（kg）。")


if __name__ == "__main__":
    unittest.main()
