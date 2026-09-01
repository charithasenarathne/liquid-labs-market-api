"""Core flow: serve annual stats from the DB, fetching on cache miss."""
import sqlite3
import threading
import logging
from datetime import datetime, timedelta, timezone

from . import alpha_vantage_client, database
from .config import Config

logger = logging.getLogger(__name__)

MIN_YEAR = 1900
STALE_TTL = timedelta(hours=24)

fetch_lock = threading.Lock()

class NoDataError(Exception):
    """NO data exists for this symbol/year"""

def annual_stats(cfg: Config, symbol: str, year: int) -> dict:
    """Return {"high", "low", "volume"} strings for one symbol-year,
      fetching from Alpha Vantage first if the cache cannot answer."""
    symbol = symbol.upper()
    if year < MIN_YEAR or year > _utcnow().year:
        raise NoDataError(f"No Data for {symbol} in {year}")

    conn = database.connect(cfg.db_path)
    try:
        if _needs_fetch(conn, symbol, year):
            with fetch_lock:
                # Re-check: a concurrent request may have fetched this symbol
                # while we waited for the lock.
                if _needs_fetch(conn, symbol, year):
                    refresh_symbol(conn, cfg, symbol, year)
        stats = database.get_annual_stats(conn, symbol, year)
    finally:
        conn.close()

    if stats is None:
        raise NoDataError(f"No Data for {symbol} in {year}")

    return {
        "high": _format_price(stats["high"]),
        "low": _format_price(stats["low"]),
        "volume": str(stats["volume"]),
    }

def refresh_symbol(conn: sqlite3.Connection, cfg: Config, symbol: str, year: int) -> None:
    """Fetch and store a symbol's history, degrading gracefully on failure."""
    try:
        body = alpha_vantage_client.fetch_monthly_history(symbol, cfg.api_key)
        rows = alpha_vantage_client.parse_monthly_history(symbol, body)
    except alpha_vantage_client.UnKnownSymbolError:
        database.save_symbol_history(conn, symbol, _utcnow().isoformat(), [])
        logger.info("Negative-cached unknown symbol %s", symbol)
        raise
    except (alpha_vantage_client.RateLimitError, alpha_vantage_client.UpstreamError):
        if database.get_annual_stats(conn, symbol, year) is None:
            raise
        logger.warning("Refresh of %s failed; serving stale data", symbol)
    else:
        database.save_symbol_history(conn, symbol, _utcnow().isoformat(), rows)

def _needs_fetch(conn: sqlite3.Connection, symbol: str, year: int) -> bool:
    """Decide whether the upstream must be called to answer this request."""
    fetched_at_text = database.get_symbol_fetched_at(conn, symbol)
    if fetched_at_text is None:
        return True
    fetched_at = datetime.fromisoformat(fetched_at_text)

    if year < fetched_at.year:
        return False
    return _utcnow() - fetched_at > STALE_TTL


def _format_price(scaled: int) -> str:
    return f"{scaled // 10000}.{scaled % 10000:04d}"


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)