from __future__ import annotations

import os
import unittest

from app.config.runtime import load_runtime_env
from app.core.intent_recognizer import IntentRecognizer


class RuntimeConfigTests(unittest.TestCase):
    def test_runtime_env_loader_populates_deepseek_settings(self) -> None:
        load_runtime_env()
        recognizer = IntentRecognizer()

        self.assertTrue(os.getenv("DEEPSEEK_API_KEY"))
        self.assertEqual(recognizer.base_url, "https://api.deepseek.com")
        self.assertEqual(recognizer.model, "deepseek-chat")


if __name__ == "__main__":
    unittest.main()
