"""Entrypoint for `uvicorn app.main:app"""

from .market_rest_api import create_app
from .config import load_config

app = create_app(load_config())