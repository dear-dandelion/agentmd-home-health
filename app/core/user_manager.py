from __future__ import annotations

from typing import Any

from app.data.data_access import DataAccess


class UserManager:
    def __init__(self, data_access: DataAccess) -> None:
        self.data_access = data_access

    def create(self, name: str, birth_date: str | None, gender: str | None) -> dict[str, Any]:
        return self.data_access.create_user(name=name, birth_date=birth_date, gender=gender)

    def update(self, user_id: int, name: str | None, birth_date: str | None, gender: str | None) -> dict[str, Any]:
        return self.data_access.update_user(user_id=user_id, name=name, birth_date=birth_date, gender=gender)

    def delete(self, user_id: int) -> bool:
        return self.data_access.delete_user(user_id)

    def get(self, user_id: int) -> dict[str, Any]:
        return self.data_access.get_user(user_id)

    def list_all(self) -> list[dict[str, Any]]:
        return self.data_access.list_users()
