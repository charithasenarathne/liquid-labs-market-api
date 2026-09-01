"""Entrypoint for `uvicorn app.main:app"""
import os
import logging

from .market_rest_api import create_app
from .config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

app = create_app(load_config())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MARKET_API_PORT", "8000")))