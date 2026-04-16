from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.data.models import UserProfile


class DataAccess:
    def __init__(self, base_dir: str | None = None) -> None:
        root = Path(base_dir) if base_dir else Path(__file__).resolve().parents[1]
        self.base_dir = root
        self.storage_dir = self.base_dir / "storage"
        self.config_dir = self.base_dir / "config"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "health.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    birth_date TEXT,
                    gender TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_params (
                    param_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    param_name TEXT NOT NULL,
                    param_value TEXT NOT NULL,
                    unit TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS assessments (
                    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    calculator_name TEXT NOT NULL,
                    input_params TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS profile_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                """
            )

    def read_json(self, filename: str) -> Any:
        with (self.config_dir / filename).open("r", encoding="utf-8") as file:
            return json.load(file)

    def list_users(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY updated_at DESC, user_id DESC").fetchall()
        return [self.get_user(row["user_id"]) for row in rows]

    def create_user(self, name: str, birth_date: str | None, gender: str | None) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, birth_date, gender, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name, birth_date, gender, now, now),
            )
            user_id = cursor.lastrowid
        profile = self.get_user(user_id)
        self._record_profile_snapshot(user_id, profile, source="create_user")
        return profile

    def update_user(self, user_id: int, name: str | None = None, birth_date: str | None = None, gender: str | None = None) -> dict[str, Any]:
        existing = self.get_user(user_id)
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET name = ?, birth_date = ?, gender = ?, updated_at = ? WHERE user_id = ?",
                (
                    name if name is not None else existing["name"],
                    birth_date if birth_date is not None else existing["birth_date"],
                    gender if gender is not None else existing["gender"],
                    now,
                    user_id,
                ),
            )
        profile = self.get_user(user_id)
        self._record_profile_snapshot(user_id, profile, source="update_user")
        return profile

    def delete_user(self, user_id: int) -> bool:
        with self._connect() as conn:
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        return True

    def upsert_param(self, user_id: int, param_name: str, param_value: Any, unit: str | None = None) -> bool:
        return self.upsert_params(user_id, {param_name: param_value}, units={param_name: unit} if unit else None)

    def upsert_params(self, user_id: int, params: dict[str, Any], units: dict[str, str | None] | None = None, source: str = "upsert_params") -> bool:
        if not params:
            return True
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            for param_name, param_value in params.items():
                conn.execute("DELETE FROM user_params WHERE user_id = ? AND param_name = ?", (user_id, param_name))
                conn.execute(
                    "INSERT INTO user_params (user_id, param_name, param_value, unit, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (
                        user_id,
                        param_name,
                        str(param_value),
                        (units or {}).get(param_name),
                        now,
                    ),
                )
            conn.execute("UPDATE users SET updated_at = ? WHERE user_id = ?", (now, user_id))
        profile = self.get_user(user_id)
        self._record_profile_snapshot(user_id, profile, source=source)
        return True

    def get_params(self, user_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT param_name, param_value FROM user_params WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,),
            ).fetchall()
        result: dict[str, Any] = {}
        for row in rows:
            result[row["param_name"]] = row["param_value"]
        return result

    def get_user(self, user_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row is None:
                raise ValueError(f"用户不存在: {user_id}")
        params = self.get_params(user_id)
        profile = UserProfile(
            user_id=row["user_id"],
            name=row["name"],
            birth_date=row["birth_date"],
            gender=row["gender"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            params=params,
        )
        return {
            "user_id": profile.user_id,
            "name": profile.name,
            "birth_date": profile.birth_date,
            "gender": profile.gender,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "age": profile.age,
            "params": profile.params,
        }

    def create_assessment(self, user_id: int, calculator_name: str, input_params: dict[str, Any], result: dict[str, Any]) -> bool:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assessments (user_id, calculator_name, input_params, result_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    calculator_name,
                    json.dumps(input_params, ensure_ascii=False),
                    json.dumps(result, ensure_ascii=False),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        return True

    def list_assessments(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [
            {
                "assessment_id": row["assessment_id"],
                "calculator_name": row["calculator_name"],
                "input_params": json.loads(row["input_params"]),
                "result_json": json.loads(row["result_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_profile_snapshots(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM profile_snapshots WHERE user_id = ? ORDER BY created_at DESC, snapshot_id DESC",
                (user_id,),
            ).fetchall()
        return [
            {
                "snapshot_id": row["snapshot_id"],
                "snapshot_json": json.loads(row["snapshot_json"]),
                "source": row["source"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _record_profile_snapshot(self, user_id: int, profile: dict[str, Any], source: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO profile_snapshots (user_id, snapshot_json, source, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    json.dumps(profile, ensure_ascii=False),
                    source,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
