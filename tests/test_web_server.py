from __future__ import annotations

import json
import unittest
from http import HTTPStatus

from app.web import server as web_server


class FakeUserManager:
    def __init__(self) -> None:
        self.users = {
            1: {
                "user_id": 1,
                "name": "张三",
                "birth_date": "1960-01-01",
                "gender": "男",
                "created_at": "2026-04-16T10:00:00",
                "updated_at": "2026-04-16T10:00:00",
                "age": 66,
                "params": {"height_cm": 170, "weight_kg": 65, "smoking_history": "从不吸烟"},
            }
        }

    def list_all(self) -> list[dict[str, object]]:
        return list(self.users.values())

    def get(self, user_id: int) -> dict[str, object]:
        return self.users[user_id]


class FakeDataAccess:
    def __init__(self) -> None:
        self.assessments = [
            {
                "assessment_id": 1,
                "calculator_name": "bmi",
                "input_params": {"height_cm": 170, "weight_kg": 65},
                "result_json": {"summary": "BMI 正常", "risk_level": "低风险"},
                "created_at": "2026-04-16T10:05:00",
            }
        ]
        self.snapshots = [
            {
                "snapshot_id": 1,
                "snapshot_json": {
                    "name": "张三",
                    "gender": "男",
                    "birth_date": "1960-01-01",
                    "params": {"height_cm": 170},
                },
                "source": "create_user",
                "created_at": "2026-04-16T10:00:00",
            }
        ]

    def list_assessments(self, user_id: int) -> list[dict[str, object]]:
        return list(self.assessments)

    def list_profile_snapshots(self, user_id: int) -> list[dict[str, object]]:
        return list(self.snapshots)


class FakeMessageResult:
    def __init__(self) -> None:
        self.reply_text = "这是测试回复"
        self.card_html = "<div>测试卡片</div>"
        self.state = type(
            "DialogState",
            (),
            {
                "state": "Idle",
                "pending_tool": None,
                "pending_intent": None,
                "required_params": [],
                "collected_params": {},
                "last_active_at": None,
            },
        )()
        self.result = {
            "summary": "BMI 正常",
            "risk_level": "低风险",
            "details": {
                "tool_name": "bmi",
                "display_name": "BMI 评估",
                "input_params": {"height_cm": 170, "weight_kg": 65},
            },
        }


class FakeMessageProcessor:
    def process(self, user_id: int, text: str, dialog_state: dict[str, object] | None = None) -> FakeMessageResult:
        return FakeMessageResult()


class FakeLiteratureService:
    def collect_statistics(self, query: str, **kwargs) -> dict[str, object]:
        return {
            "query": query,
            "sources": kwargs.get("sources", ["pubmed"]),
            "retrieved_total": 2,
            "matched_total": 2,
            "target_total": 50,
            "unclassified_count": 0,
            "provider_errors": [],
            "categories": [
                {
                    "category": "心血管",
                    "matched_count": 1,
                    "target_count": 13,
                    "representative_calculators": ["CHA2DS2-VASc"],
                }
            ],
            "documents": [],
        }


class FakeService:
    def __init__(self) -> None:
        self.user_manager = FakeUserManager()
        self.data_access = FakeDataAccess()
        self.message_processor = FakeMessageProcessor()
        self.literature_service = FakeLiteratureService()


class WebServerHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_service = web_server.AgentMDRequestHandler.service
        web_server.AgentMDRequestHandler.service = FakeService()
        self.handler = web_server.AgentMDRequestHandler.__new__(web_server.AgentMDRequestHandler)
        self.status_code = None
        self.headers_sent = {}
        self.body = b""

        def send_response(status: int) -> None:
            self.status_code = status

        def send_header(name: str, value: str) -> None:
            self.headers_sent[name] = value

        def end_headers() -> None:
            return

        class Writer:
            def __init__(self, test_case: WebServerHandlerTest) -> None:
                self.test_case = test_case

            def write(self, data: bytes) -> None:
                self.test_case.body += data

        self.handler.send_response = send_response
        self.handler.send_header = send_header
        self.handler.end_headers = end_headers
        self.handler.wfile = Writer(self)

    def tearDown(self) -> None:
        web_server.AgentMDRequestHandler.service = self.original_service

    def read_payload(self) -> dict[str, object]:
        return json.loads(self.body.decode("utf-8"))

    def test_send_json_returns_ok(self) -> None:
        self.handler._send_json({"users": [self.handler._normalize_profile(web_server.AgentMDRequestHandler.service.user_manager.get(1))]})
        self.assertEqual(self.status_code, HTTPStatus.OK)
        payload = self.read_payload()
        self.assertEqual(payload["users"][0]["name"], "张三")

    def test_normalize_assessment_converts_numeric_fields(self) -> None:
        item = web_server.AgentMDRequestHandler.service.data_access.list_assessments(1)[0]
        normalized = self.handler._normalize_assessment(item)
        self.assertEqual(normalized["input_params"]["height_cm"], 170)
        self.assertEqual(normalized["input_params"]["weight_kg"], 65)

    def test_normalize_snapshot_converts_numeric_fields(self) -> None:
        item = web_server.AgentMDRequestHandler.service.data_access.list_profile_snapshots(1)[0]
        normalized = self.handler._normalize_snapshot(item)
        self.assertEqual(normalized["snapshot_json"]["params"]["height_cm"], 170)

    def test_chat_payload_shape(self) -> None:
        result = web_server.AgentMDRequestHandler.service.message_processor.process(1, "帮我评估BMI", {})
        response = {
            "reply_text": result.reply_text,
            "card_html": result.card_html,
            "state": {
                "state": result.state.state,
                "pending_tool": result.state.pending_tool,
                "pending_intent": result.state.pending_intent,
                "required_params": result.state.required_params,
                "collected_params": result.state.collected_params,
                "last_active_at": None,
            },
            "result": result.result,
            "profile": self.handler._normalize_profile(web_server.AgentMDRequestHandler.service.user_manager.get(1)),
        }
        self.handler._send_json(response)
        payload = self.read_payload()
        self.assertEqual(payload["reply_text"], "这是测试回复")
        self.assertEqual(payload["result"]["details"]["display_name"], "BMI 评估")
        self.assertEqual(payload["profile"]["params"]["height_cm"], 170)

    def test_literature_stats_payload_shape(self) -> None:
        payload = web_server.AgentMDRequestHandler.service.literature_service.collect_statistics("calculator", sources=["pubmed"])
        self.handler._send_json(payload)
        result = self.read_payload()
        self.assertEqual(result["query"], "calculator")
        self.assertEqual(result["retrieved_total"], 2)
        self.assertEqual(result["categories"][0]["category"], "心血管")


if __name__ == "__main__":
    unittest.main()
