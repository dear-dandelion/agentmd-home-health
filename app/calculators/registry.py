from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Dict

from app.calculators.repository import CalculatorRepository


CalculatorFunc = Callable[[Dict[str, Any]], Dict[str, Any]]


class CalculatorRegistry:
    def __init__(self, repository: CalculatorRepository | None = None) -> None:
        self.repository = repository or CalculatorRepository()
        self._calculators: Dict[str, CalculatorFunc] = {}
        self._load_runtime_calculators()

    def _load_runtime_calculators(self) -> None:
        calculators: Dict[str, CalculatorFunc] = {}
        for manifest in self.repository.list_manifests():
            module = import_module(manifest.source_module)
            calculators[manifest.name] = getattr(module, manifest.function_name)
        self._calculators = calculators

    def get(self, name: str) -> CalculatorFunc:
        if name not in self._calculators:
            raise KeyError(f"未注册的计算器: {name}")
        return self._calculators[name]

    def names(self) -> list[str]:
        return list(self._calculators.keys())
