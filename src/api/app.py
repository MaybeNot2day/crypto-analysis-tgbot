"""
FastAPI backend API for the dashboard.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from src.config import load_config
from src.pipeline.storage import DataStorage
from src.universe.builder import UniverseBuilder
from src.utils.timezone import now_utc4

logger = logging.getLogger(__name__)


def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN and inf values with None for JSON serialization."""
    df = df.replace([np.nan, np.inf, -np.inf], None)
    return df

app = FastAPI(title="Crypto Outlier Detection API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = load_config()
storage = DataStorage(config)
universe_builder = UniverseBuilder(config)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Crypto Outlier Detection API", "version": "1.0.0"}


@app.get("/api/latest")
async def get_latest_data(symbol: Optional[str] = None, exchange: Optional[str] = None):
    """Get latest market data."""
    try:
        df = storage.get_latest_market_data(symbol=symbol, exchange=exchange)
        df = clean_dataframe_for_json(df)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching latest data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/factors")
async def get_factor_scores(symbol: Optional[str] = None, limit: Optional[int] = 100):
    """Get factor scores."""
    try:
        # Get the latest timestamp first
        latest_query = "SELECT MAX(timestamp) as max_ts FROM factor_scores"
        latest_result = storage.conn.execute(latest_query).df()
        
        if latest_result.empty or latest_result.iloc[0]["max_ts"] is None:
            return []
        
        max_timestamp = latest_result.iloc[0]["max_ts"]
        
        # Fix: Use parameterized queries to prevent SQL injection
        if symbol:
            query = """
                SELECT * FROM factor_scores 
                WHERE timestamp = ?
                AND symbol = ?
                ORDER BY timestamp DESC
            """
            params = [max_timestamp.isoformat(), symbol]
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            df = storage.conn.execute(query, params).df()
        else:
            query = """
                SELECT * FROM factor_scores 
                WHERE timestamp = ?
                ORDER BY symbol ASC
            """
            params = [max_timestamp.isoformat()]
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            df = storage.conn.execute(query, params).df()
        df = clean_dataframe_for_json(df)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching factor scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/outliers")
async def get_outliers(limit: int = 20):
    """Get flagged outliers."""
    try:
        df = storage.get_outliers(limit=limit)
        df = clean_dataframe_for_json(df)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching outliers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends")
async def get_trends(symbol: str, hours: int = 24):
    """Get trend history for a symbol."""
    try:
        start_time = now_utc4() - timedelta(hours=hours)
        df = storage.get_factor_scores(symbol=symbol, start_time=start_time)
        df = clean_dataframe_for_json(df)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/universe")
async def get_universe():
    """Get current universe."""
    try:
        df = universe_builder.load_universe()
        df = clean_dataframe_for_json(df)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching universe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Get system status."""
    try:
        latest_data = storage.get_latest_market_data()
        latest_timestamp = None
        if not latest_data.empty:
            latest_timestamp = latest_data.iloc[0]["timestamp"].isoformat()
        
        outliers = storage.get_outliers(limit=1)
        outlier_count = len(outliers)
        
        return {
            "status": "healthy",
            "latest_data_timestamp": latest_timestamp,
            "outlier_count": outlier_count,
            "config": config.to_dict(),
        }
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

