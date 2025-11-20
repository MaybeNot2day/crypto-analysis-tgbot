"""
Universe builder for managing top crypto assets from Binance.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import requests
from src.config import Config, load_config
from src.utils.timezone import now_utc4, UTC_PLUS_4

logger = logging.getLogger(__name__)


class UniverseBuilder:
    """Builds and maintains the universe of top crypto assets from Binance."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.universe_config = self.config.universe
        self.storage_path = Path(self.universe_config.storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def fetch_binance_top_assets(self, limit: int = 50) -> List[Dict]:
        """
        Fetch top assets by 24h volume from Binance.
        
        Args:
            limit: Number of top assets to fetch
            
        Returns:
            List of asset dictionaries with symbol, volume, and price info
        """
        # Fetch 24h ticker statistics for all symbols
        spot_url = "https://api.binance.com/api/v3/ticker/24hr"
        futures_url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        
        try:
            # Fetch spot tickers
            response = requests.get(spot_url, timeout=30)
            response.raise_for_status()
            spot_tickers = response.json()
            
            # Fetch futures tickers
            response = requests.get(futures_url, timeout=30)
            response.raise_for_status()
            futures_tickers = response.json()
            
            # Create a map of base asset to best symbol (prefer USDT pairs)
            asset_map = {}
            
            # Process spot tickers
            for ticker in spot_tickers:
                symbol = ticker["symbol"]
                volume = float(ticker.get("quoteVolume", 0))  # Quote volume in USDT
                price = float(ticker.get("lastPrice", ticker.get("price", 0)))
                
                # Extract base asset (everything before the quote)
                # Common quote assets: USDT, BUSD, BTC, ETH, etc.
                for quote in ["USDT", "BUSD", "BTC", "ETH", "BNB"]:
                    if symbol.endswith(quote):
                        base = symbol[:-len(quote)]
                        if base not in asset_map or quote == "USDT":
                            asset_map[base] = {
                                "symbol": symbol,
                                "quote": quote,
                                "volume": volume,
                                "price": price,
                                "spot_symbol": symbol,
                                "spot_quote": quote,
                            }
                        break
            
            # Process futures tickers (prefer futures if available)
            futures_map = {}
            for ticker in futures_tickers:
                symbol = ticker["symbol"]
                volume = float(ticker.get("quoteVolume", 0))
                price = float(ticker.get("lastPrice", ticker.get("markPrice", 0)))
                
                # Extract base asset
                for quote in ["USDT", "BUSD", "BTC", "ETH", "BNB"]:
                    if symbol.endswith(quote):
                        base = symbol[:-len(quote)]
                        futures_map[base] = {
                            "symbol": symbol,
                            "quote": quote,
                            "volume": volume,
                            "price": price,
                            "futures_symbol": symbol,
                            "futures_quote": quote,
                        }
                        break
            
            # Combine spot and futures data
            all_assets = []
            for base, spot_data in asset_map.items():
                futures_data = futures_map.get(base)
                
                asset = {
                    "base_asset": base,
                    "symbol": spot_data["symbol"],
                    "spot_symbol": spot_data["spot_symbol"],
                    "spot_quote": spot_data["spot_quote"],
                    "futures_symbol": futures_data["futures_symbol"] if futures_data else None,
                    "futures_quote": futures_data["futures_quote"] if futures_data else None,
                    "volume_24h": max(spot_data["volume"], futures_data["volume"] if futures_data else 0),
                    "price": spot_data["price"] or (futures_data["price"] if futures_data else 0),
                    "exchange": "binance",
                    "last_updated": now_utc4().isoformat(),
                }
                all_assets.append(asset)
            
            # Sort by volume and take top N
            all_assets.sort(key=lambda x: x["volume_24h"], reverse=True)
            return all_assets[:limit]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Binance data: {e}")
            raise

    def build_universe(self) -> pd.DataFrame:
        """
        Build the universe of top assets from Binance.
        
        Returns:
            DataFrame with universe information
        """
        logger.info(f"Building universe of top {self.universe_config.top_n} assets from Binance")
        
        # Fetch top assets directly from Binance
        assets = self.fetch_binance_top_assets(self.universe_config.top_n)
        logger.info(f"Fetched {len(assets)} assets from Binance")
        
        # Create DataFrame
        df = pd.DataFrame(assets)
        
        # Save to storage
        self.save_universe(df)
        
        return df

    def save_universe(self, df: pd.DataFrame):
        """Save universe to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.storage_path, index=False)
        logger.info(f"Saved universe to {self.storage_path}")

    def load_universe(self) -> pd.DataFrame:
        """Load universe from storage."""
        if not self.storage_path.exists():
            logger.warning("Universe file not found, building new universe")
            return self.build_universe()
        
        df = pd.read_parquet(self.storage_path)
        logger.info(f"Loaded universe with {len(df)} assets from {self.storage_path}")
        return df

    def should_update(self) -> bool:
        """Check if universe should be updated based on frequency."""
        if not self.storage_path.exists():
            return True
        
        # Check last update time
        last_modified = datetime.fromtimestamp(self.storage_path.stat().st_mtime)
        # Make last_modified timezone-aware by localizing to UTC+4 for comparison
        last_modified = last_modified.replace(tzinfo=UTC_PLUS_4)
        hours_since_update = (now_utc4() - last_modified).total_seconds() / 3600
        
        return hours_since_update >= self.universe_config.update_frequency_hours

    def update_universe_if_needed(self) -> pd.DataFrame:
        """Update universe if needed, otherwise return cached version."""
        if self.should_update():
            return self.build_universe()
        else:
            return self.load_universe()
