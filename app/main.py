import os

from app.config.runtime import load_runtime_env
from app.web.server import run_server


def main() -> None:
    load_runtime_env()
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "7860"))
    run_server(host=host, port=port)


if __name__ == "__main__":
    main()
