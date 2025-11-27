"""
Data storage layer using DuckDB for time-series data.
"""

import logging
import duckdb
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from src.adapters.base import MarketData, CandleData
from src.config import Config, DatabaseConfig
from src.utils.timezone import now_utc4

logger = logging.getLogger(__name__)


class DataStorage:
    """Data storage using DuckDB."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize data storage."""
        self.config = config or Config()
        self.db_config = self.config.database
        
        # Ensure data directory exists
        db_path = Path(self.db_config.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to DuckDB with retry logic for lock conflicts
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                self.conn = duckdb.connect(str(db_path))
                self._initialize_schema()
                break
            except Exception as e:
                if "lock" in str(e).lower() or "conflicting" in str(e).lower():
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Database lock detected, retrying ({retry_count}/{max_retries})...")
                        import time
                        time.sleep(1)
                    else:
                        logger.error(f"Could not acquire database lock after {max_retries} attempts. "
                                   f"Please ensure no other processes are using the database.")
                        raise
                else:
                    raise

    def _initialize_schema(self):
        """Initialize database schema."""
        # Raw market data table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                timestamp TIMESTAMP,
                exchange VARCHAR,
                symbol VARCHAR,
                price DOUBLE,
                mark_price DOUBLE,
                index_price DOUBLE,
                volume_24h DOUBLE,
                open_interest DOUBLE,
                funding_rate DOUBLE,
                next_funding_time TIMESTAMP,
                PRIMARY KEY (timestamp, exchange, symbol)
            )
        """)
        
        # Candle data table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS candle_data (
                timestamp TIMESTAMP,
                exchange VARCHAR,
                symbol VARCHAR,
                interval VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                PRIMARY KEY (timestamp, exchange, symbol, interval)
            )
        """)
        
        # Factor scores table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS factor_scores (
                timestamp TIMESTAMP,
                exchange VARCHAR,
                symbol VARCHAR,
                price_btc DOUBLE,
                momentum_1h DOUBLE,
                momentum_4h DOUBLE,
                momentum_24h DOUBLE,
                momentum_percentile DOUBLE,
                mean_reversion_zscore DOUBLE,
                rsi DOUBLE,
                carry_funding_annualized DOUBLE,
                carry_basis DOUBLE,
                volume_momentum_1h DOUBLE,
                volume_momentum_4h DOUBLE,
                volume_momentum_24h DOUBLE,
                volume_anomaly_zscore DOUBLE,
                volume_percentile DOUBLE,
                volume_price_divergence DOUBLE,
                composite_score DOUBLE,
                is_outlier BOOLEAN,
                outlier_type VARCHAR,
                PRIMARY KEY (timestamp, exchange, symbol)
            )
        """)
        
        # Migrate existing tables to add volume columns if they don't exist
        self._migrate_schema()
        
        # Telegram summaries table (for deduplication and audit)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS telegram_summaries (
                timestamp TIMESTAMP,
                summary_hash VARCHAR,
                summary_text VARCHAR,
                sent BOOLEAN,
                PRIMARY KEY (timestamp, summary_hash)
            )
        """)
        
        # Create indexes for better query performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_candle_data_symbol ON candle_data(symbol, interval)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_candle_data_timestamp ON candle_data(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_scores_symbol ON factor_scores(symbol)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_scores_timestamp ON factor_scores(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_scores_outlier ON factor_scores(is_outlier)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_timestamp ON telegram_summaries(timestamp DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_hash ON telegram_summaries(summary_hash)")
        
        logger.info("Database schema initialized")

    def _migrate_schema(self):
        """Migrate schema to add missing columns if they don't exist."""
        try:
            # Check if columns exist
            columns_result = self.conn.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'factor_scores'
            """).df()

            existing_columns = set(columns_result["column_name"].tolist()) if not columns_result.empty else set()

            # Define all columns that should exist
            required_columns = {
                # Volume factors
                "volume_momentum_1h", "volume_momentum_4h", "volume_momentum_24h",
                "volume_anomaly_zscore", "volume_percentile", "volume_price_divergence",
                # Momentum indicators
                "macd_signal", "trend_strength", "ema_signal",
                # Mean reversion
                "bb_position",
                # Volatility
                "volatility_atr_pct",
                # Open Interest factors
                "oi_change_1h", "oi_change_4h", "oi_change_24h",
                "open_interest", "funding_rate", "funding_rate_apr",
                # BTC correlation
                "btc_correlation", "btc_beta"
            }

            # Add missing columns
            for col in required_columns:
                if col not in existing_columns:
                    self.conn.execute(f"ALTER TABLE factor_scores ADD COLUMN {col} DOUBLE")
                    logger.info(f"Added column {col} to factor_scores table")
        except Exception as e:
            # If information_schema is not available (older DuckDB), try direct ALTER
            # DuckDB will ignore if column already exists
            try:
                all_columns = [
                    "volume_momentum_1h", "volume_momentum_4h", "volume_momentum_24h",
                    "volume_anomaly_zscore", "volume_percentile", "volume_price_divergence",
                    "macd_signal", "trend_strength", "ema_signal",
                    "bb_position", "volatility_atr_pct",
                    "oi_change_1h", "oi_change_4h", "oi_change_24h",
                    "open_interest", "funding_rate", "funding_rate_apr",
                    "btc_correlation", "btc_beta"
                ]
                for col in all_columns:
                    self.conn.execute(f"ALTER TABLE factor_scores ADD COLUMN IF NOT EXISTS {col} DOUBLE")
            except Exception as migration_error:
                logger.warning(f"Schema migration warning: {migration_error}")

    def save_market_data(self, data: List[MarketData]):
        """Save market data snapshots."""
        if not data:
            return
        
        df = pd.DataFrame([
            {
                "timestamp": d.timestamp,
                "exchange": d.exchange,
                "symbol": d.symbol,
                "price": d.price,
                "mark_price": d.mark_price,
                "index_price": d.index_price,
                "volume_24h": d.volume_24h,
                "open_interest": d.open_interest,
                "funding_rate": d.funding_rate,
                "next_funding_time": d.next_funding_time,
            }
            for d in data
        ])
        
        # Register DataFrame and insert (DuckDB will handle duplicates via primary key)
        self.conn.register("df_temp", df)
        # Use INSERT OR IGNORE equivalent - delete existing rows first, then insert
        for _, row in df.iterrows():
            self.conn.execute("""
                DELETE FROM market_data 
                WHERE timestamp = ? AND exchange = ? AND symbol = ?
            """, [row["timestamp"], row["exchange"], row["symbol"]])
        
        self.conn.execute("INSERT INTO market_data SELECT * FROM df_temp")
        
        logger.info(f"Saved {len(data)} market data snapshots")

    def save_candle_data(self, data: List[CandleData], interval: str = "1h"):
        """Save candle data."""
        if not data:
            return
        
        df = pd.DataFrame([
            {
                "timestamp": d.timestamp,
                "exchange": d.exchange,
                "symbol": d.symbol,
                "interval": interval,
                "open": d.open,
                "high": d.high,
                "low": d.low,
                "close": d.close,
                "volume": d.volume,
            }
            for d in data
        ])
        
        self.conn.register("df_temp", df)
        # Delete existing rows first to handle duplicates
        for _, row in df.iterrows():
            self.conn.execute("""
                DELETE FROM candle_data 
                WHERE timestamp = ? AND exchange = ? AND symbol = ? AND interval = ?
            """, [row["timestamp"], row["exchange"], row["symbol"], row["interval"]])
        
        self.conn.execute("INSERT INTO candle_data SELECT * FROM df_temp")
        
        logger.info(f"Saved {len(data)} candles for interval {interval}")

    def save_factor_scores(self, scores: List[Dict[str, Any]]):
        """Save factor scores."""
        if not scores:
            return
        
        df = pd.DataFrame(scores)
        
        # Define the expected column order matching the table schema
        expected_columns = [
            "timestamp", "exchange", "symbol", "price_btc",
            "momentum_1h", "momentum_4h", "momentum_24h", "momentum_percentile",
            "mean_reversion_zscore", "rsi",
            "carry_funding_annualized", "carry_basis",
            "volume_momentum_1h", "volume_momentum_4h", "volume_momentum_24h",
            "volume_anomaly_zscore", "volume_percentile", "volume_price_divergence",
            "composite_score", "is_outlier", "outlier_type"
        ]
        
        # Reorder DataFrame columns to match table schema
        # Only include columns that exist in both DataFrame and schema
        available_columns = [col for col in expected_columns if col in df.columns]
        df_ordered = df[available_columns].copy()
        
        # Ensure all expected columns exist (fill missing ones with None)
        for col in expected_columns:
            if col not in df_ordered.columns:
                df_ordered[col] = None
        
        # Reorder to match exact schema order
        df_ordered = df_ordered[expected_columns]
        
        self.conn.register("df_temp", df_ordered)
        # Delete existing rows first, then insert (upsert behavior)
        for _, row in df_ordered.iterrows():
            self.conn.execute("""
                DELETE FROM factor_scores 
                WHERE timestamp = ? AND exchange = ? AND symbol = ?
            """, [row["timestamp"], row["exchange"], row["symbol"]])
        
        # Insert with explicit column names to ensure correct mapping
        column_list = ", ".join(expected_columns)
        placeholders = ", ".join(["?" for _ in expected_columns])
        self.conn.execute(f"""
            INSERT INTO factor_scores ({column_list})
            SELECT {column_list} FROM df_temp
        """)
        
        logger.info(f"Saved {len(scores)} factor scores")

    def get_latest_market_data(self, symbol: Optional[str] = None, exchange: Optional[str] = None) -> pd.DataFrame:
        """Get latest market data."""
        # Fix: Use parameterized queries to prevent SQL injection
        if symbol:
            # Get latest data for specific symbol
            query = """
                SELECT * FROM market_data
                WHERE symbol = ?
            """
            params = [symbol]
            if exchange:
                query += " AND exchange = ?"
                params.append(exchange)
            query += " ORDER BY timestamp DESC LIMIT 1"
            return self.conn.execute(query, params).df()
        else:
            # Get latest data for all symbols (latest per symbol)
            query = """
                SELECT * FROM market_data md1
                WHERE timestamp = (
                    SELECT MAX(timestamp) 
                    FROM market_data md2 
                    WHERE md2.symbol = md1.symbol
                )
            """
            params = []
            if exchange:
                query += " AND exchange = ?"
                params.append(exchange)
            
            if params:
                return self.conn.execute(query, params).df()
            else:
                return self.conn.execute(query).df()

    def get_candle_data(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Get candle data - returns most recent candles first, then sorts ASC for analysis."""
        # Fix: Use parameterized query to prevent SQL injection
        # Get most recent candles first, then sort ASC for time series analysis
        if limit:
            # Use subquery to get most recent N candles, then sort ASC
            query = """
                SELECT * FROM (
                    SELECT * FROM candle_data
                    WHERE symbol = ? AND interval = ?
            """
            params = [symbol, interval]
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += """
                    ORDER BY timestamp DESC
                    LIMIT ?
                ) ORDER BY timestamp ASC
            """
            params.append(limit)
            
            return self.conn.execute(query, params).df()
        else:
            # No limit - get all and sort ASC
            query = """
                SELECT * FROM candle_data
                WHERE symbol = ? AND interval = ?
            """
            params = [symbol, interval]
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp ASC"
            
            return self.conn.execute(query, params).df()

    def get_factor_scores(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Get factor scores."""
        # Fix: Use parameterized queries to prevent SQL injection
        query = "SELECT * FROM factor_scores WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        if params:
            return self.conn.execute(query, params).df()
        else:
            return self.conn.execute(query).df()

    def get_outliers(self, limit: int = 20) -> pd.DataFrame:
        """Get flagged outliers from the latest timestamp only."""
        # First get the latest timestamp
        latest_query = "SELECT MAX(timestamp) as max_ts FROM factor_scores"
        latest_result = self.conn.execute(latest_query).df()
        
        if latest_result.empty or latest_result.iloc[0]["max_ts"] is None:
            return pd.DataFrame()
        
        max_timestamp = latest_result.iloc[0]["max_ts"]
        
        # Get outliers only from the latest timestamp
        query = f"""
            SELECT * FROM factor_scores
            WHERE is_outlier = TRUE
            AND timestamp = '{max_timestamp.isoformat()}'
            ORDER BY ABS(composite_score) DESC
            LIMIT {limit}
        """
        return self.conn.execute(query).df()

    def get_last_summary_hash(self) -> Optional[str]:
        """Get the hash of the last sent summary for deduplication."""
        try:
            result = self.conn.execute("""
                SELECT summary_hash 
                FROM telegram_summaries 
                WHERE sent = true 
                ORDER BY timestamp DESC 
                LIMIT 1
            """).fetchone()
            
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.warning(f"Error getting last summary hash: {e}")
            return None

    def save_summary(self, summary_text: str, summary_hash: str, sent: bool = True) -> bool:
        """Save a summary to the database for audit and deduplication."""
        try:
            timestamp = now_utc4()
            
            # Check if summary with same hash already exists for this timestamp
            existing = self.conn.execute("""
                SELECT COUNT(*) FROM telegram_summaries 
                WHERE timestamp = ? AND summary_hash = ?
            """, [timestamp, summary_hash]).fetchone()
            
            if existing[0] > 0:
                # Update existing record
                self.conn.execute("""
                    UPDATE telegram_summaries 
                    SET summary_text = ?, sent = ?
                    WHERE timestamp = ? AND summary_hash = ?
                """, [summary_text, sent, timestamp, summary_hash])
            else:
                # Insert new record
                self.conn.execute("""
                    INSERT INTO telegram_summaries (timestamp, summary_hash, summary_text, sent)
                    VALUES (?, ?, ?, ?)
                """, [timestamp, summary_hash, summary_text, sent])
            
            logger.debug(f"Saved summary with hash {summary_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Error saving summary: {e}", exc_info=True)
            return False

    def get_summary_history(self, limit: int = 10) -> pd.DataFrame:
        """Get recent summary history."""
        try:
            query = f"""
                SELECT timestamp, summary_hash, sent, 
                       LENGTH(summary_text) as summary_length
                FROM telegram_summaries 
                ORDER BY timestamp DESC 
                LIMIT {limit}
            """
            return self.conn.execute(query).df()
        except Exception as e:
            logger.error(f"Error getting summary history: {e}", exc_info=True)
            return pd.DataFrame()

    def cleanup_old_data(self, retention_days: Optional[int] = None):
        """Clean up old data beyond retention period."""
        retention_days = retention_days or self.config.data_retention_days
        cutoff_date = now_utc4() - pd.Timedelta(days=retention_days)
        
        self.conn.execute(f"""
            DELETE FROM market_data WHERE timestamp < '{cutoff_date.isoformat()}'
        """)
        
        self.conn.execute(f"""
            DELETE FROM candle_data WHERE timestamp < '{cutoff_date.isoformat()}'
        """)
        
        self.conn.execute(f"""
            DELETE FROM factor_scores WHERE timestamp < '{cutoff_date.isoformat()}'
        """)
        
        # Clean up old summaries (keep for 30 days for audit)
        summary_cutoff = now_utc4() - pd.Timedelta(days=30)
        self.conn.execute(f"""
            DELETE FROM telegram_summaries WHERE timestamp < '{summary_cutoff.isoformat()}'
        """)
        
        logger.info(f"Cleaned up data older than {retention_days} days")

    def close(self):
        """Close database connection."""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

