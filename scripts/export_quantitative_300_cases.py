from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.experiments.ablation import HomeInquiryBenchmarkCase, load_benchmark_cases


DEFAULT_OUTPUT = "experiments/home_inquiry_quantitative_300_cases.json"
SELECTED_PROMPT_POSITIONS = (1, 2, 3, 5, 7, 10)


def _case_suffix(case: HomeInquiryBenchmarkCase) -> int:
    return int(case.id.rsplit("_", 1)[1])


def select_quantitative_300_cases(cases: list[HomeInquiryBenchmarkCase]) -> list[HomeInquiryBenchmarkCase]:
    grouped: dict[str, list[HomeInquiryBenchmarkCase]] = defaultdict(list)
    for case in cases:
        if case.scenario_type != "calculator" or not case.expected_tool:
            continue
        grouped[case.expected_tool].append(case)

    selected: list[HomeInquiryBenchmarkCase] = []
    for tool_name in sorted(grouped):
        tool_cases = sorted(grouped[tool_name], key=_case_suffix)
        positions = set(SELECTED_PROMPT_POSITIONS)
        chosen = [case for case in tool_cases if _case_suffix(case) in positions]
        if len(chosen) != len(SELECTED_PROMPT_POSITIONS):
            raise ValueError(
                f"Calculator {tool_name} does not have the required prompt positions: {SELECTED_PROMPT_POSITIONS}"
            )
        selected.extend(chosen)

    if len(selected) != 300:
        raise ValueError(f"Expected 300 selected cases, got {len(selected)}.")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a curated 300-case quantitative inquiry benchmark.")
    parser.add_argument(
        "--source",
        default=None,
        help="Optional source benchmark JSON path. Defaults to the built-in 513-case benchmark.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output JSON file path.",
    )
    args = parser.parse_args()

    cases = load_benchmark_cases(args.source)
    selected = select_quantitative_300_cases(cases)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "description": "Curated 300-case quantitative home-health inquiry benchmark selected from the 513-case set.",
        "selection_rule": {
            "per_calculator_cases": 6,
            "selected_prompt_positions": list(SELECTED_PROMPT_POSITIONS),
        },
        "cases": [asdict(case) for case in selected],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"源样本数: {len(cases)}")
    print(f"精选样本数: {len(selected)}")
    print(f"输出文件: {output_path}")


if __name__ == "__main__":
    main()
