from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LibraryCalculatorEntry:
    name: str
    display_name: str
    category: str
    priority_level: str
    implementation_status: str
    literature_sources: tuple[str, ...]
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LibraryCalculatorEntry":
        return cls(
            name=payload["name"],
            display_name=payload.get("display_name", payload["name"]),
            category=payload["category"],
            priority_level=payload.get("priority_level", "medium"),
            implementation_status=payload.get("implementation_status", "planned"),
            literature_sources=tuple(payload.get("literature_sources", [])),
            notes=payload.get("notes", ""),
        )


class CalculatorLibraryCatalog:
    def __init__(self, catalog_path: str | Path | None = None) -> None:
        self.catalog_path = Path(catalog_path) if catalog_path else Path(__file__).resolve().parents[2] / "data" / "calculator_library.json"
        self._payload = self._load_payload()

    def _runtime_names(self) -> set[str]:
        runtime_names = set()
        calculators_dir = Path(__file__).resolve().parents[2] / "data" / "calculators"
        for path in sorted(calculators_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            name = payload.get("name")
            if name:
                runtime_names.add(name)
        return runtime_names

    def _load_payload(self) -> dict[str, Any]:
        with self.catalog_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def list_entries(
        self,
        *,
        category: str | None = None,
        implementation_status: str | None = None,
    ) -> list[LibraryCalculatorEntry]:
        runtime_names = self._runtime_names()
        entries = []
        for item in self._payload.get("calculators", []):
            normalized = dict(item)
            if normalized.get("name") in runtime_names:
                normalized["implementation_status"] = "implemented"
            entries.append(LibraryCalculatorEntry.from_dict(normalized))
        if category is not None:
            entries = [entry for entry in entries if entry.category == category]
        if implementation_status is not None:
            entries = [entry for entry in entries if entry.implementation_status == implementation_status]
        return entries

    def design_overview(self) -> dict[str, Any]:
        design = dict(self._payload.get("design", {}))
        design["current_runtime_total"] = len(self._runtime_names())
        return design

    def summary(self) -> dict[str, Any]:
        category_rows = list(self._payload.get("categories", []))
        entries = self.list_entries()
        implemented = [entry for entry in entries if entry.implementation_status == "implemented"]
        category_summary: list[dict[str, Any]] = []

        for row in category_rows:
            name = row["name"]
            category_entries = [entry for entry in entries if entry.category == name]
            implemented_count = sum(1 for entry in category_entries if entry.implementation_status == "implemented")
            category_summary.append(
                {
                    "category": name,
                    "target_count": int(row.get("target_count", len(category_entries))),
                    "implemented_count": implemented_count,
                    "planned_count": len(category_entries) - implemented_count,
                    "representative_calculators": list(row.get("representative_calculators", [])),
                }
            )

        return {
            "version": self._payload.get("version", ""),
            "target_total": sum(int(row.get("target_count", 0)) for row in category_rows),
            "implemented_total": len(implemented),
            "planned_total": len(entries) - len(implemented),
            "categories": category_summary,
        }
