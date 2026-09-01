#Liquid Labs Market API

A small REST API that serves annual stock statistics (highest price, lowest price, total volume) aggregated from Alpha Vantage monthly data. 
Fetched data is cached in a local SQLite database; each symbol costs exactly one upstream API call, ever, no matter how many requests follow.

## Endpoint

```
GET /symbols/{symbol}/annual/{year}
```

Example:

```
GET /symbols/IBM/annual/2005

{
  "high": "99.1000",
  "low": "71.8500",
  "volume": "1539128900"
}
```

## Prerequisites

1. **Python 3.11 or newer** — https://www.python.org/downloads/ (on Windows, tick "Add python.exe to PATH" in the installer). Check it works with `python --version`.
2. **A free Alpha Vantage API key** — https://www.alphavantage.co/support/#api-key. Or use the key `demo` for a first look: it works for the symbols `IBM` and `TSCO.LON` only, without consuming any quota.
3. **No database installation is needed.** SQLite ships inside Python's standard library; the database is a single local file created automatically the first time the app runs.

## Setup

From the project folder, install the third-party libraries:

```
pip install -r requirements.txt
```

This installs `fastapi`, `pydantic`, `uvicorn`, `requests`, `pytest`, and `httpx` (pinned versions listed in `requirements.txt`).

## Configuration

Set your API key as an environment variable in the terminal you will run the server from:

| Shell | Command |
|---|---|
| Windows cmd | `set ALPHA_VANTAGE_API_KEY=yourkey` |
| Windows PowerShell | `$env:ALPHA_VANTAGE_API_KEY = "yourkey"` |
| macOS / Linux (bash) | `export ALPHA_VANTAGE_API_KEY=yourkey` |

Optional variables:

| Variable | Default | Purpose |
|---|---|---|
| `MARKET_DB_PATH` | `market.db` | SQLite database file location |
| `MARKET_API_PORT` | `8000` | Port for `python -m app.main` (use if 8000 is taken) |

## Run

```
python -m app.main
```

or equivalently:

```
uvicorn app.main:app
```

The database file is created and the schema (`schema.sql`) applied automatically at startup — there is no separate database setup step. The server prints `Uvicorn running on http://127.0.0.1:8000` when ready.

## Example requests

Run these from a second terminal (or paste the URLs into a browser). With the `demo` key, use the symbol `IBM`; with a real key, any symbol works.

A full year (first call fetches from Alpha Vantage, takes a second):

```
curl http://127.0.0.1:8000/symbols/IBM/annual/2005
{"high":"99.1000","low":"71.8500","volume":"1539128900"}
```

The same request again — served instantly from the local database, no upstream call:

```
curl http://127.0.0.1:8000/symbols/IBM/annual/2005
```

A different year of the same symbol — also instant, because one fetch cached the whole history:

```
curl http://127.0.0.1:8000/symbols/IBM/annual/2010
```

The current year — aggregates the months available so far:

```
curl http://127.0.0.1:8000/symbols/IBM/annual/2026
```

A year before the data begins — 404, no quota spent on repeats:

```
curl -i http://127.0.0.1:8000/symbols/IBM/annual/1990
```

A future year — rejected immediately without any upstream call:

```
curl -i http://127.0.0.1:8000/symbols/IBM/annual/2999
```

An unknown symbol — 404; the miss is cached so retries cost no quota:

```
curl -i http://127.0.0.1:8000/symbols/ZZZZQ/annual/2015
```

Invalid input — 422 from request validation:


If port 8000 is already in use, set `MARKET_API_PORT` (for `python -m app.main`) or pass `--port` to uvicorn (`uvicorn app.main:app --port 8001`).

## Test


## Response codes

| Code | Meaning |
|---|---|
| 200 | Data found and aggregated |
| 404 | No data for that symbol/year (unknown symbol, or year outside coverage) |
| 422 | Invalid input (malformed symbol or non-numeric year) |
| 502 | Alpha Vantage failed or returned an unexpected response |
| 503 | Alpha Vantage rate limit reached; retry later (`Retry-After` header set) |

## Libraries used

- **fastapi** — required by the brief; provides routing, path-parameter validation, and JSON serialization.
- **pydantic** — ships with FastAPI and powers its validation; imported directly for the typed response model.
- **uvicorn** — the ASGI server that FastAPI runs on; FastAPI does not include an HTTP server itself.
- **requests** — HTTP client for the Alpha Vantage call; the stdlib alternative (`urllib`) needs considerably more code for timeouts and errors.
- **pytest** — test runner. Tests are not required by the brief but verify the caching, aggregation, and error-handling logic.
- **httpx** — not used by the application; test-only dependency of FastAPI's `TestClient`.

Database access uses the stdlib `sqlite3` module with plain SQL (no ORM).

## Design decisions

- **Whole-history caching.** Alpha Vantage's monthly endpoint takes only a symbol and returns its entire history in one response, so a single fetch caches every year at once — important with a 25-requests/day quota.
- **Negative cache.** The `symbols` table records that a symbol was fetched, so requests for years with no data return 404 without burning quota. This covers unknown symbols too: a symbol the upstream rejects is recorded with an empty history, so repeated requests for bogus tickers cannot drain the daily quota.
- **Staleness rule.** Years before the fetch year are complete and immutable; the fetch year onward may be partial (the current month's row is month-to-date), so it is refetched once the cache is older than 24 hours.
- **Serve-stale on upstream failure.** When a refresh fails but cached data exists for the requested year, the cached data is served instead of an error; only requests with nothing to fall back on surface the failure.
- **Exact prices.** Prices are stored as integers scaled by 10^4: floats would lose exactness and text would break SQL `MAX`/`MIN`. Responses are JSON strings (`"99.1000"`) because JSON numbers cannot keep trailing zeros.
- **Sync endpoints.** FastAPI runs `def` handlers on a threadpool, which handles concurrent requests fine at this scale; `sqlite3` and `requests` are blocking, so async would add dependencies without benefit.
- **Atomic writes and a fetch lock.** A symbol's history is inserted in one transaction, and a lock prevents concurrent requests from fetching the same symbol twice.