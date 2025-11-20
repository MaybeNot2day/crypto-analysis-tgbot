"""
Base adapter interface for exchange data providers.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from collections import deque
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.utils.timezone import now_utc4

logger = logging.getLogger(__name__)


@dataclass
class CandleData:
    """Candle/OHLCV data structure."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    exchange: str


@dataclass
class MarketData:
    """Market data snapshot."""
    timestamp: datetime
    symbol: str
    exchange: str
    price: float
    mark_price: Optional[float] = None
    index_price: Optional[float] = None
    volume_24h: Optional[float] = None
    open_interest: Optional[float] = None
    funding_rate: Optional[float] = None
    next_funding_time: Optional[datetime] = None


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, max_requests: int, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Remove requests outside the time window
        while self.request_times and self.request_times[0] < now - self.time_window:
            self.request_times.popleft()
        
        # If we're at the limit, wait until the oldest request expires
        if len(self.request_times) >= self.max_requests:
            wait_time = self.request_times[0] + self.time_window - now + 0.1
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                # Clean up again after waiting
                while self.request_times and self.request_times[0] < now - self.time_window:
                    self.request_times.popleft()
        
        self.request_times.append(time.time())


class BaseExchangeAdapter(ABC):
    """Base class for exchange adapters."""

    def __init__(self, name: str, base_url: str, rate_limit_per_minute: int = 1200):
        """
        Initialize base adapter.
        
        Args:
            name: Exchange name
            base_url: Base API URL
            rate_limit_per_minute: Rate limit in requests per minute
        """
        self.name = name
        self.base_url = base_url
        self.rate_limiter = RateLimiter(rate_limit_per_minute, 60)
        
        # Set up session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            headers: Request headers
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON as dictionary
        """
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.name} API error: {e}")
            raise

    @abstractmethod
    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[CandleData]:
        """
        Fetch OHLCV candle data.
        
        Args:
            symbol: Trading symbol
            interval: Time interval (1m, 5m, 1h, 4h, 1d, etc.)
            limit: Maximum number of candles to return
            start_time: Start time (optional)
            end_time: End time (optional)
            
        Returns:
            List of CandleData objects
        """
        pass

    @abstractmethod
    def fetch_mark_price(self, symbol: str) -> float:
        """
        Fetch mark price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Mark price
        """
        pass

    @abstractmethod
    def fetch_index_price(self, symbol: str) -> float:
        """
        Fetch index price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Index price
        """
        pass

    @abstractmethod
    def fetch_open_interest(self, symbol: str) -> float:
        """
        Fetch open interest for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Open interest
        """
        pass

    @abstractmethod
    def fetch_funding(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch funding rate information.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with funding_rate, next_funding_time, etc.
        """
        pass

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch 24h ticker statistics.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with price, volume, etc.
        """
        pass

    def get_market_data(self, symbol: str) -> MarketData:
        """
        Fetch comprehensive market data snapshot.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            MarketData object
        """
        ticker = self.fetch_ticker(symbol)
        funding = self.fetch_funding(symbol)
        
        try:
            mark_price = self.fetch_mark_price(symbol)
        except Exception as e:
            logger.warning(f"Could not fetch mark price for {symbol}: {e}")
            mark_price = None
        
        try:
            index_price = self.fetch_index_price(symbol)
        except Exception as e:
            logger.warning(f"Could not fetch index price for {symbol}: {e}")
            index_price = None
        
        try:
            open_interest = self.fetch_open_interest(symbol)
            # Handle None return value (spot-only symbols)
            if open_interest is None:
                open_interest = None
        except Exception as e:
            logger.debug(f"Could not fetch open interest for {symbol}: {e}")
            open_interest = None

        return MarketData(
            timestamp=now_utc4(),
            symbol=symbol,
            exchange=self.name,
            price=ticker.get("last_price", ticker.get("price", 0)),
            mark_price=mark_price,
            index_price=index_price,
            volume_24h=ticker.get("volume_24h", ticker.get("volume", None)),
            open_interest=open_interest,
            funding_rate=funding.get("funding_rate"),
            next_funding_time=funding.get("next_funding_time"),
        )
