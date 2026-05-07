from __future__ import annotations

import json
from pathlib import Path

from app.calculators.extended_specs import build_extended_manifests


def main() -> None:
    catalog_dir = Path(__file__).resolve().parents[1] / "data" / "calculators"
    catalog_dir.mkdir(parents=True, exist_ok=True)

    for payload in build_extended_manifests():
        path = catalog_dir / f"{payload['name']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path.name)


if __name__ == "__main__":
    main()
