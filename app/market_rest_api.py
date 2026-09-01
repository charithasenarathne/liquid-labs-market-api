"""FastAPI Implementation"""

from fastapi import FastAPI, HTTPException
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import alpha_vantage_client, database, stats_service
from .config import Config

SYMBOL_PATTERN = r"^[A-Za-z.\-]{1,10}$"

class AnnualStats(BaseModel):
    high: str
    low: str
    volume: str


def create_app(cfg: Config) -> FastAPI:
    database.init_db(cfg.db_path)
    app = FastAPI(title="Market Data API")

    @app.get("/symbols/{symbol}/annual/{year}", response_model=AnnualStats)
    def get_annual_stats(
        symbol: str = PathParam(pattern=SYMBOL_PATTERN),
        year: int = PathParam(),
    ) -> AnnualStats:
        try:
            return AnnualStats(**stats_service.annual_stats(cfg, symbol, year))
        except stats_service.NoDataError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except alpha_vantage_client.UnknownSymbolError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except alpha_vantage_client.RateLimitError as exc:
            return JSONResponse(
                status_code=503,
                content={"detail": str(exc)},
                headers={"Retry-After": "3600"},
            )
        except alpha_vantage_client.UpstreamError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app
