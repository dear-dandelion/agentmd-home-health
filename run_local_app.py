from __future__ import annotations

import sys
import time
from pathlib import Path

from app.ui.gradio_app import build_app


def main() -> None:
    log_path = Path(__file__).resolve().parent / "run_local_app.log"
    try:
        app = build_app()
        app.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            inbrowser=False,
            prevent_thread_lock=True,
        )
        log_path.write_text("RUNNING http://127.0.0.1:7860\n", encoding="utf-8")
        while True:
            time.sleep(3600)
    except Exception as exc:  # pragma: no cover
        log_path.write_text(f"ERROR {exc}\n", encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
