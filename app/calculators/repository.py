from __future__ import annotations

import json
from pathlib import Path

from app.calculators.library import CalculatorLibraryCatalog
from app.calculators.metadata import CalculatorManifest
from app.calculators.priority import CalculatorPriorityScorer


class CalculatorRepository:
    def __init__(self, catalog_dir: str | Path | None = None) -> None:
        root = Path(catalog_dir) if catalog_dir else Path(__file__).resolve().parents[2] / "data" / "calculators"
        self.catalog_dir = root
        self.catalog_dir.mkdir(parents=True, exist_ok=True)
        self.library_catalog = CalculatorLibraryCatalog()
        self._manifests: dict[str, CalculatorManifest] = {}
        self._load_manifests()

    def _load_manifests(self) -> None:
        manifests: dict[str, CalculatorManifest] = {}
        for path in sorted(self.catalog_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            priority = CalculatorPriorityScorer.score(payload.get("priority", {}))
            manifest = CalculatorManifest.from_dict(payload, priority=priority)
            manifests[manifest.name] = manifest
        self._manifests = manifests

    def list_manifests(self) -> list[CalculatorManifest]:
        return list(self._manifests.values())

    def get_manifest(self, name: str) -> CalculatorManifest:
        try:
            return self._manifests[name]
        except KeyError as exc:
            raise KeyError(f"Unknown calculator: {name}") from exc

    def tool_definitions(self) -> list[dict[str, object]]:
        return [manifest.to_tool_definition() for manifest in self.list_manifests()]

    def library_summary(self) -> dict[str, object]:
        summary = self.library_catalog.summary()
        implemented_names = set(self._manifests.keys())
        implemented_total = 0
        for row in summary["categories"]:
            category_name = row["category"]
            implemented_count = len(
                [
                    entry
                    for entry in self.library_catalog.list_entries(category=category_name)
                    if entry.name in implemented_names
                ]
            )
            row["implemented_count"] = implemented_count
            row["planned_count"] = row["target_count"] - implemented_count
            implemented_total += implemented_count
        summary["implemented_total"] = implemented_total
        summary["planned_total"] = summary["target_total"] - implemented_total
        return summary

    def library_design(self) -> dict[str, object]:
        design = self.library_catalog.design_overview()
        design["current_runtime_total"] = len(self._manifests)
        return design
