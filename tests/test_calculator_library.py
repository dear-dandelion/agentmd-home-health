import unittest

from app.calculators.library import CalculatorLibraryCatalog
from app.calculators.repository import CalculatorRepository


class CalculatorLibraryCatalogTests(unittest.TestCase):
    def test_summary_matches_target_library_design(self) -> None:
        catalog = CalculatorLibraryCatalog()

        summary = catalog.summary()

        self.assertEqual(summary["target_total"], 50)
        self.assertEqual(summary["implemented_total"], 50)
        self.assertEqual(summary["planned_total"], 0)
        self.assertEqual(len(summary["categories"]), 7)
        self.assertEqual(
            sorted((item["target_count"], item["implemented_count"], item["planned_count"]) for item in summary["categories"]),
            sorted([(13, 13, 0), (7, 7, 0), (10, 10, 0), (2, 2, 0), (2, 2, 0), (2, 2, 0), (14, 14, 0)]),
        )

    def test_repository_summary_reflects_runtime_progress(self) -> None:
        repository = CalculatorRepository()

        summary = repository.library_summary()
        runtime_names = sorted(manifest.name for manifest in repository.list_manifests())

        self.assertEqual(summary["target_total"], 50)
        self.assertEqual(summary["implemented_total"], len(runtime_names))
        self.assertEqual(summary["implemented_total"], 50)
        self.assertEqual(summary["planned_total"], 0)
        self.assertEqual(
            sorted((item["target_count"], item["implemented_count"], item["planned_count"]) for item in summary["categories"]),
            sorted([(13, 13, 0), (7, 7, 0), (10, 10, 0), (2, 2, 0), (2, 2, 0), (2, 2, 0), (14, 14, 0)]),
        )


if __name__ == "__main__":
    unittest.main()
