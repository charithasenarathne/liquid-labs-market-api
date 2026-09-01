"""SQLite access layer. Plain SQL only, no ORM."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'schema.sql'

def connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with the app's standard per-connection settings."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db(db_path: str) -> None:
    """Create the database file if needed and apply schema.sql (idempotent)."""
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
    finally:
        conn.close()

def get_annual_stats( conn: sqlite3.Connection, symbol :str, year :int) -> dict | None:
    """Aggregate the monthly rows for one symbol-year, or None if absent."""
    row = conn.execute(
        """ 
        SELECT 
            MAX(high),
            MIN(low),
            SUM(volume)
        FROM monthly_prices
        WHERE
            symbol = ?
            AND
            year = ?
        """,
(symbol, year),
    ).fetchone()
    if row[0] is None:
        return None
    return {"high": row[0], "low": row[1], "volume": row[2]}

def get_symbol_fetched_at(conn: sqlite3.Connection, symbol:str) -> str | None:
    """Return the ISO timestamp of the symbol's last fetch, or None if never."""
    row = conn.execute(
        """
        SELECT 
            fetched_at
        FROM symbols
        WHERE
            symbol = ?
        """,
(symbol,),
    ).fetchone()
    return row[0] if row else None


def save_symbol_history(conn: sqlite3.Connection, symbol:str, fetched_at:str, rows: list[tuple]) -> None:
    """Store a symbol's full history atomically."""

    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO symbols
                (symbol, fetched_at)
            VALUES
                (?, ?)
            """,
(symbol, fetched_at),
        )

        conn.executemany(
            """
            INSERT OR REPLACE INTO monthly_prices
                (symbol, year, month, high, low, volume)
            VALUES
                (?, ?, ?, ?, ?, ?)
            """,
            rows
        )