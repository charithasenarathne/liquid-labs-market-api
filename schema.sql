-- Creating the symbols table if it does not exist.
-- Primarily used to check whether the data is fetched before for a given symbol
CREATE TABLE IF NOT EXISTS symbols (
    symbol     TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL
);

-- One row per (symbol, year, month).
-- Prices are stored as integers scaled by 10^4 (Alpha Vantage always sends 4 decimal places)
-- This is done to ommit the floating point errors as SQLite does not have a proper decimal data type.
CREATE TABLE IF NOT EXISTS monthly_prices (
    symbol TEXT    NOT NULL REFERENCES symbols(symbol),
    year   INTEGER NOT NULL,
    month  INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    high   INTEGER NOT NULL,
    low    INTEGER NOT NULL CHECK (low <= high),
    volume INTEGER NOT NULL CHECK (volume >= 0),
    PRIMARY KEY (symbol, year, month)
) WITHOUT ROWID;