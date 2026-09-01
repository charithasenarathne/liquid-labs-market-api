"""Alpha Vantage client: fetch monthly history and parse it into DB rows."""

from decimal import Decimal,InvalidOperation
import requests

BASE_URL = "https://www.alphavantage.co/query"
FETCH_TIMEOUT_SECONDS = 10
PRICE_SCALE = 10000
SERIES_KEY = "Monthly Time Series"

class UpstreamError(Exception):
    """The upstream API failed"""

class RateLimitError(Exception):
    """The upstream API refused due to quota reasons"""

class UnKnownSymbolError(Exception):
    """The upstream API refused due to unknown symbol"""

def fetch_monthly_history(symbol: str, api_key: str) -> dict:
    try:
        response = requests.get(
            BASE_URL,
            params={
                "function": "TIME_SERIES_MONTHLY",
                "symbol": symbol,
                "api_key": api_key,
            },
            timeout=FETCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except requests.exceptions.RequestException as e:
        raise UpstreamError(f"Alpha Vantage API request failed: {e}") from e

    # Alpha Vantage reports quota exhaustion inside an HTTP 200 body,
    # so these checks must come before trusting the payload.

    if "Note" in body or "Information" in body:
        raise RateLimitError(f"Alpha Vantage API rate limit exceeded: {body}")
    if "Error Message" in body:
        raise UnKnownSymbolError(f"Alpha Vantage API error message: {body}")
    if SERIES_KEY not in body:
        raise UpstreamError(f"Alpha Vantage API error message: {body}")
    return body

def parse_monthly_history(symbol: str, body:dict) -> list[tuple]:
    """Convert a fetch_monthly() body into (symbol, year, month, high, low,
    volume) tuples ready for insertion. Prices become scaled integers."""
    rows = []
    try:
        for date_key, fields in body[SERIES_KEY].items():
            year = int(date_key[:4])
            month = int(date_key[5:7])
            rows.append(
                (
                    symbol,
                    year,
                    month,
                    _to_scaled_int(fields["2. high"]),
                    _to_scaled_int(fields["3. low"]),
                    int(fields["5. volume"]),
                )
            )
    except (KeyError, ValueError, IndexError, InvalidOperation) as e:
        raise UpstreamError(f"Malformed Alpha Vintage data: {e}") from e
    return rows

def _to_scaled_int(text:str) -> int:
    value = Decimal(text) * PRICE_SCALE
    if value != value.to_integral_value():
        raise UpstreamError(f"Price has more than 4 decimal places: {text}")
    return int(value)