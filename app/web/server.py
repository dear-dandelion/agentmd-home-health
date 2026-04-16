from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.api.service import AppService


STATIC_DIR = Path(__file__).resolve().parent / "static"
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


class AgentMDRequestHandler(BaseHTTPRequestHandler):
    service = AppService()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/users":
            self._send_json({"users": [self._normalize_profile(user) for user in self.service.user_manager.list_all()]})
            return

        if re.fullmatch(r"/api/users/\d+", path):
            user_id = self._path_id(path)
            self._send_json({"user": self._normalize_profile(self.service.user_manager.get(user_id))})
            return

        if re.fullmatch(r"/api/users/\d+/assessments", path):
            user_id = self._path_id(path)
            assessments = self.service.data_access.list_assessments(user_id)
            self._send_json({"assessments": [self._normalize_assessment(item) for item in assessments]})
            return

        if re.fullmatch(r"/api/users/\d+/snapshots", path):
            user_id = self._path_id(path)
            snapshots = self.service.data_access.list_profile_snapshots(user_id)
            self._send_json({"snapshots": [self._normalize_snapshot(item) for item in snapshots]})
            return

        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_json_body()

        if path == "/api/users":
            profile = self.service.user_manager.create(
                name=str(payload.get("name", "")).strip(),
                birth_date=self._empty_to_none(payload.get("birth_date")),
                gender=self._empty_to_none(payload.get("gender")),
            )
            params = self._sanitize_params(payload.get("params", {}))
            if params:
                self.service.data_access.upsert_params(profile["user_id"], params, source="web_create")
                profile = self.service.user_manager.get(profile["user_id"])
            self._send_json({"user": self._normalize_profile(profile)}, status=HTTPStatus.CREATED)
            return

        if path == "/api/chat":
            user_id = int(payload["user_id"])
            result = self.service.message_processor.process(
                user_id=user_id,
                text=str(payload.get("message", "")),
                dialog_state=payload.get("dialog_state"),
            )
            response = {
                "reply_text": result.reply_text,
                "card_html": result.card_html,
                "state": {
                    "state": result.state.state,
                    "pending_tool": result.state.pending_tool,
                    "pending_intent": result.state.pending_intent,
                    "required_params": result.state.required_params,
                    "collected_params": result.state.collected_params,
                    "last_active_at": result.state.last_active_at.isoformat() if result.state.last_active_at else None,
                },
                "result": result.result,
                "profile": self._normalize_profile(self.service.user_manager.get(user_id)),
            }
            self._send_json(response)
            return

        if path == "/api/literature/stats":
            query = str(payload.get("query", "")).strip()
            if not query:
                self._send_json({"error": "Query is required."}, status=HTTPStatus.BAD_REQUEST)
                return
            response = self.service.literature_service.collect_statistics(
                query=query,
                sources=list(payload.get("sources", ["pubmed", "sinomed"])),
                max_results_each=int(payload.get("max_results_each", 50)),
                mindate=self._empty_to_none(payload.get("mindate")),
                maxdate=self._empty_to_none(payload.get("maxdate")),
            )
            self._send_json(response)
            return

        if re.fullmatch(r"/api/users/\d+/assessments", path):
            user_id = self._path_id(path)
            self.service.data_access.create_assessment(
                user_id=user_id,
                calculator_name=str(payload.get("calculator_name", "")),
                input_params=dict(payload.get("input_params", {})),
                result=dict(payload.get("result", {})),
            )
            assessments = self.service.data_access.list_assessments(user_id)
            self._send_json({"assessments": [self._normalize_assessment(item) for item in assessments]}, status=HTTPStatus.CREATED)
            return

        self._send_json({"error": "Unknown endpoint."}, status=HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_json_body()

        if re.fullmatch(r"/api/users/\d+", path):
            user_id = self._path_id(path)
            profile = self.service.user_manager.update(
                user_id=user_id,
                name=self._empty_to_none(payload.get("name")),
                birth_date=self._empty_to_none(payload.get("birth_date")),
                gender=self._empty_to_none(payload.get("gender")),
            )
            params = self._sanitize_params(payload.get("params", {}))
            if params:
                self.service.data_access.upsert_params(user_id, params, source="web_edit")
                profile = self.service.user_manager.get(user_id)
            self._send_json({"user": self._normalize_profile(profile)})
            return

        self._send_json({"error": "Unknown endpoint."}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _serve_static(self, path: str) -> None:
        target = "index.html" if path in {"/", ""} else path.lstrip("/")
        file_path = (STATIC_DIR / target).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists():
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type in {"text/html", "text/css", "application/javascript"}:
            content_type = f"{content_type}; charset=utf-8"
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_json_body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    @staticmethod
    def _path_id(path: str) -> int:
        match = re.search(r"/(\d+)(?:/|$)", path)
        if not match:
            raise ValueError(f"Cannot parse id from path: {path}")
        return int(match.group(1))

    @staticmethod
    def _empty_to_none(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _normalize_profile(self, profile: dict[str, object]) -> dict[str, object]:
        normalized = dict(profile)
        params = dict(normalized.get("params", {}))
        normalized["params"] = {key: self._normalize_param_value(key, value) for key, value in params.items()}
        return normalized

    def _normalize_assessment(self, item: dict[str, object]) -> dict[str, object]:
        normalized = dict(item)
        result = dict(normalized.get("result_json", {}))
        details = dict(result.get("details", {}))
        input_params = dict(normalized.get("input_params", {}))
        normalized["input_params"] = {key: self._normalize_param_value(key, value) for key, value in input_params.items()}
        if "input_params" in details:
            details["input_params"] = {
                key: self._normalize_param_value(key, value) for key, value in dict(details["input_params"]).items()
            }
            result["details"] = details
        normalized["result_json"] = result
        return normalized

    def _normalize_snapshot(self, item: dict[str, object]) -> dict[str, object]:
        normalized = dict(item)
        snapshot = dict(normalized.get("snapshot_json", {}))
        params = dict(snapshot.get("params", {}))
        snapshot["params"] = {key: self._normalize_param_value(key, value) for key, value in params.items()}
        normalized["snapshot_json"] = snapshot
        return normalized

    @staticmethod
    def _normalize_param_value(name: str, value: object) -> object:
        if name not in NUMERIC_PARAM_FIELDS:
            return value
        if isinstance(value, (int, float)):
            return value
        try:
            number = float(str(value))
        except (TypeError, ValueError):
            return value
        return int(number) if number.is_integer() else round(number, 1)

    def _sanitize_params(self, params: object) -> dict[str, object]:
        if not isinstance(params, dict):
            return {}
        result: dict[str, object] = {}
        for key, value in params.items():
            if value in ("", None):
                continue
            result[str(key)] = self._normalize_param_value(str(key), value)
        return result


def run_server(host: str = "127.0.0.1", port: int = 7860) -> None:
    try:
        server = ThreadingHTTPServer((host, port), AgentMDRequestHandler)
    except OSError as exc:
        raise RuntimeError(f"Cannot start web server on http://{host}:{port}: {exc}") from exc
    print(f"Web app running at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
