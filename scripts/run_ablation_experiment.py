from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.experiments.ablation import compare_variants, load_benchmark_cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the home-health inquiry ablation experiment.")
    parser.add_argument(
        "--cases",
        default=None,
        help="Optional path to a benchmark case JSON file.",
    )
    parser.add_argument(
        "--output",
        default="experiments/results/home_inquiry_ablation_report.json",
        help="Path to write the JSON experiment report.",
    )
    args = parser.parse_args()

    cases = load_benchmark_cases(args.cases)
    report = compare_variants(cases)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"样本数: {report['case_count']}")
    print(
        "完整系统严格准确率: "
        f"{report['full_system']['strict_correct_count']}/{report['full_system']['total_count']} "
        f"({report['full_system']['strict_accuracy']:.2%})"
    )
    print(
        "DeepSeek 直答对照组严格准确率: "
        f"{report['deepseek_direct']['strict_correct_count']}/{report['deepseek_direct']['total_count']} "
        f"({report['deepseek_direct']['strict_accuracy']:.2%})"
    )
    print(
        "计算结果准确率对比: "
        f"{report['full_system']['calculation_result_accuracy']:.2%} -> "
        f"{report['deepseek_direct']['calculation_result_accuracy']:.2%}"
    )
    print(
        "风险等级准确率对比: "
        f"{report['full_system']['risk_level_accuracy']:.2%} -> "
        f"{report['deepseek_direct']['risk_level_accuracy']:.2%}"
    )
    print(
        "数值参考准确率对比: "
        f"{report['full_system']['numeric_reference_accuracy']:.2%} -> "
        f"{report['deepseek_direct']['numeric_reference_accuracy']:.2%}"
    )
    print(f"结果已写入: {output_path}")


if __name__ == "__main__":
    main()
