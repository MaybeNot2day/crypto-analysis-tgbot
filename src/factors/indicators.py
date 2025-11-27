"""
Technical indicators calculation module.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Union


def calculate_ema(data: np.ndarray, span: int) -> np.ndarray:
    """
    Calculate Exponential Moving Average.
    
    Args:
        data: Input data array
        span: EMA span (period)
        
    Returns:
        EMA array
    """
    alpha = 2 / (span + 1)
    return pd.Series(data).ewm(span=span, adjust=False).mean().values


def calculate_macd(
    prices: np.ndarray, 
    fast_period: int = 12, 
    slow_period: int = 26, 
    signal_period: int = 9
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate Moving Average Convergence Divergence (MACD).
    
    Args:
        prices: Array of prices
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line EMA period
        
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    if len(prices) < slow_period:
        return (
            np.full_like(prices, np.nan),
            np.full_like(prices, np.nan),
            np.full_like(prices, np.nan)
        )
        
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    
    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: np.ndarray, 
    period: int = 20, 
    num_std: float = 2.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: Array of prices
        period: Moving average period
        num_std: Number of standard deviations
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    if len(prices) < period:
        return (
            np.full_like(prices, np.nan),
            np.full_like(prices, np.nan),
            np.full_like(prices, np.nan)
        )
        
    series = pd.Series(prices)
    middle_band = series.rolling(window=period).mean().values
    std_dev = series.rolling(window=period).std().values
    
    upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std)
    
    return upper_band, middle_band, lower_band


def calculate_atr(
    high: np.ndarray, 
    low: np.ndarray, 
    close: np.ndarray, 
    period: int = 14
) -> np.ndarray:
    """
    Calculate Average True Range (ATR).
    
    Args:
        high: Array of high prices
        low: Array of low prices
        close: Array of close prices
        period: ATR period
        
    Returns:
        ATR array
    """
    if len(close) < period + 1:
        return np.full_like(close, np.nan)
        
    # Calculate True Range
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    
    # First value of tr2 and tr3 is invalid due to roll
    tr2[0] = 0
    tr3[0] = 0
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # Calculate ATR using Wilder's Smoothing (RMA)
    # RMA is equivalent to EMA with alpha = 1/period
    atr = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean().values
    
    return atr


def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        prices: Array of prices
        period: RSI period

    Returns:
        RSI array
    """
    if len(prices) < period + 1:
        return np.full_like(prices, np.nan)

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # Use pandas ewm for Wilder's smoothing which is standard for RSI
    avg_gain = pd.Series(gains).ewm(alpha=1/period, adjust=False).mean().values
    avg_loss = pd.Series(losses).ewm(alpha=1/period, adjust=False).mean().values

    # Pad with NaN for the first element lost in diff
    avg_gain = np.insert(avg_gain, 0, np.nan)
    avg_loss = np.insert(avg_loss, 0, np.nan)

    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
    rsi = 100 - (100 / (1 + rs))

    # Handle division by zero (perfect gain)
    rsi[avg_loss == 0] = 100

    return rsi


def calculate_ema_crossover(
    prices: np.ndarray,
    fast_period: int = 9,
    slow_period: int = 21
) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Calculate EMA crossover signal.

    Args:
        prices: Array of prices
        fast_period: Fast EMA period (default 9)
        slow_period: Slow EMA period (default 21)

    Returns:
        Tuple of (fast_ema, slow_ema, signal)
        signal: 1 (bullish crossover), -1 (bearish crossover), 0 (no clear signal)
    """
    if len(prices) < slow_period:
        return (
            np.full_like(prices, np.nan),
            np.full_like(prices, np.nan),
            0
        )

    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)

    # Determine signal from current position and recent crossover
    if np.isnan(fast_ema[-1]) or np.isnan(slow_ema[-1]):
        signal = 0
    elif fast_ema[-1] > slow_ema[-1]:
        signal = 1  # Bullish
    elif fast_ema[-1] < slow_ema[-1]:
        signal = -1  # Bearish
    else:
        signal = 0

    return fast_ema, slow_ema, signal
