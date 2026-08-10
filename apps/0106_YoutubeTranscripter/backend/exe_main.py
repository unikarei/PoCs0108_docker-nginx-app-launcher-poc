"""
PyInstaller entry point for launching the FastAPI backend as a standalone EXE.
"""
import os

import uvicorn

from main import app


def main() -> None:
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", "8502"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
