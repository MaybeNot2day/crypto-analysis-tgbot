"""
Binance exchange adapter implementation.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from src.adapters.base import BaseExchangeAdapter, CandleData, MarketData

logger = logging.getLogger(__name__)


class BinanceAdapter(BaseExchangeAdapter):
    """Binance adapter for futures and spot markets."""

    def __init__(
        self, 
        base_url: str = "https://fapi.binance.com", 
        rate_limit_per_minute: int = 1200,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        """
        Initialize Binance adapter.
        
        Args:
            base_url: Base URL for the API
            rate_limit_per_minute: Rate limit (1200 for public, 2400 with API key)
            api_key: Optional API key for higher rate limits
            api_secret: Optional API secret (not used for public endpoints)
        """
        super().__init__("binance", base_url, rate_limit_per_minute)
        self.spot_base_url = "https://api.binance.com"
        self.futures_base_url = "https://fapi.binance.com"
        self.api_key = api_key
        self.api_secret = api_secret

    def _is_futures_symbol(self, symbol: str) -> bool:
        """Check if symbol is a futures contract."""
        # Cache the futures symbols list to avoid repeated API calls
        if not hasattr(self, '_futures_symbols_cache'):
            try:
                original_base = self.base_url
                self.base_url = self.futures_base_url
                try:
                    exchange_info = self._make_request("GET", "fapi/v1/exchangeInfo")
                    self._futures_symbols_cache = set(
                        s["symbol"] for s in exchange_info.get("symbols", [])
                        if s.get("status") == "TRADING"  # Only active trading symbols
                    )
                finally:
                    self.base_url = original_base
            except Exception:
                self._futures_symbols_cache = set()
        
        return symbol in self._futures_symbols_cache

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[CandleData]:
        """Fetch OHLCV candles from Binance."""
        # Use futures API by default
        is_futures = self._is_futures_symbol(symbol)
        base = self.futures_base_url if is_futures else self.spot_base_url
        endpoint_path = "fapi/v1/klines" if is_futures else "api/v3/klines"
        
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),  # Binance max is 1000
        }
        
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        # Override base_url temporarily for this request
        original_base = self.base_url
        self.base_url = base
        
        try:
            data = self._make_request("GET", endpoint_path, params=params)
        finally:
            self.base_url = original_base

        candles = []
        for candle in data:
            candles.append(
                CandleData(
                    timestamp=datetime.fromtimestamp(candle[0] / 1000),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                    symbol=symbol,
                    exchange=self.name,
                )
            )

        return candles

    def fetch_mark_price(self, symbol: str) -> float:
        """Fetch mark price from Binance futures."""
        # Only fetch if symbol exists in futures
        if not self._is_futures_symbol(symbol):
            # For spot-only symbols, return spot price
            ticker = self.fetch_ticker(symbol)
            return float(ticker.get("last_price", ticker.get("price", 0)))
        
        try:
            original_base = self.base_url
            self.base_url = self.futures_base_url
            try:
                data = self._make_request("GET", "fapi/v1/premiumIndex", params={"symbol": symbol})
                return float(data["markPrice"])
            except Exception:
                # Try spot price as fallback
                ticker = self.fetch_ticker(symbol)
                return float(ticker.get("last_price", ticker.get("price", 0)))
            finally:
                self.base_url = original_base
        except Exception:
            # Try spot price as fallback
            ticker = self.fetch_ticker(symbol)
            return float(ticker.get("last_price", ticker.get("price", 0)))

    def fetch_index_price(self, symbol: str) -> float:
        """Fetch index price from Binance futures."""
        # Only fetch if symbol exists in futures
        if not self._is_futures_symbol(symbol):
            # For spot-only symbols, return spot price as index
            ticker = self.fetch_ticker(symbol)
            return float(ticker.get("last_price", ticker.get("price", 0)))
        
        try:
            original_base = self.base_url
            self.base_url = self.futures_base_url
            try:
                data = self._make_request("GET", "fapi/v1/premiumIndex", params={"symbol": symbol})
                return float(data["indexPrice"])
            except Exception:
                # Fallback to mark price
                return self.fetch_mark_price(symbol)
            finally:
                self.base_url = original_base
        except Exception:
            # Fallback to mark price
            return self.fetch_mark_price(symbol)

    def fetch_open_interest(self, symbol: str) -> float:
        """Fetch open interest from Binance futures."""
        # Only fetch if symbol exists in futures
        if not self._is_futures_symbol(symbol):
            return None
        
        original_base = self.base_url
        self.base_url = self.futures_base_url
        try:
            data = self._make_request("GET", "fapi/v1/openInterest", params={"symbol": symbol})
            return float(data["openInterest"])
        except Exception as e:
            logger.debug(f"Could not fetch open interest for {symbol}: {e}")
            return None
        finally:
            self.base_url = original_base

    def fetch_funding(self, symbol: str) -> Dict[str, Any]:
        """Fetch funding rate information from Binance futures."""
        # Only fetch if symbol exists in futures
        if not self._is_futures_symbol(symbol):
            # Spot-only symbols don't have funding rates
            return {
                "funding_rate": None,
                "next_funding_time": None,
            }
        
        try:
            original_base = self.base_url
            self.base_url = self.futures_base_url
            try:
                data = self._make_request("GET", "fapi/v1/premiumIndex", params={"symbol": symbol})
                
                next_funding_time = None
                if "nextFundingTime" in data:
                    next_funding_time = datetime.fromtimestamp(data["nextFundingTime"] / 1000)
                
                return {
                    "funding_rate": float(data.get("lastFundingRate", 0)),
                    "next_funding_time": next_funding_time,
                    "mark_price": float(data.get("markPrice", 0)),
                    "index_price": float(data.get("indexPrice", 0)),
                }
            finally:
                self.base_url = original_base
        except Exception as e:
            logger.debug(f"Could not fetch funding for {symbol}: {e}")
            return {
                "funding_rate": None,
                "next_funding_time": None,
            }

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch 24h ticker statistics."""
        # Try futures first
        is_futures = self._is_futures_symbol(symbol)
        base = self.futures_base_url if is_futures else self.spot_base_url
        endpoint_path = "fapi/v1/ticker/24hr" if is_futures else "api/v3/ticker/24hr"
        
        original_base = self.base_url
        self.base_url = base
        
        try:
            data = self._make_request("GET", endpoint_path, params={"symbol": symbol})
        finally:
            self.base_url = original_base

        return {
            "symbol": data["symbol"],
            "price": float(data.get("lastPrice", data.get("last_price", data.get("price", 0)))),
            "last_price": float(data.get("lastPrice", data.get("last_price", data.get("price", 0)))),
            "volume": float(data.get("volume", 0)),
            "volume_24h": float(data.get("volume", 0)),
            "high": float(data.get("highPrice", data.get("high", 0))),
            "low": float(data.get("lowPrice", data.get("low", 0))),
            "change_24h": float(data.get("priceChangePercent", 0)),
        }

