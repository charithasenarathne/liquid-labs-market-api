"""Application configuration, read from environment variables."""

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    db_path: str
    api_key: str

def load_config() -> Config:
    """Read configuration from the environment; fail fast if the key is missing."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        #Fail at startup, not on the first request.
        raise RuntimeError(
            "ALPHA_VANTAGE_API_KEY environment variable is not set."
            "GEt a free key at https://www.alphavantage.co/support/#api-key"
        )
    return Config(
        db_path=os.environ.get("MARKET_DB_PATH", "market.db"),
        api_key=api_key,
    )
