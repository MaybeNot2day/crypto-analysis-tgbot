"""
Factor computation module for momentum, mean reversion, and carry factors.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from src.config import Config, load_config
from src.factors.indicators import (
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_rsi,
    calculate_ema_crossover
)

logger = logging.getLogger(__name__)


class FactorCalculator:
    """Calculate factor scores for crypto assets."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize factor calculator."""
        self.config = config or load_config()
        self.factor_weights = self.config.factor_weights

    def calculate_momentum(
        self,
        candles: pd.DataFrame,
        periods: List[int] = [1, 4, 24],
    ) -> Dict[str, float]:
        """
        Calculate momentum factors including MACD and EMA crossover.

        Args:
            candles: DataFrame with OHLCV data sorted by timestamp
            periods: List of periods (in hours) for momentum calculation

        Returns:
            Dictionary with momentum metrics
        """
        if len(candles) < max(periods):
            return {
                "momentum_1h": None,
                "momentum_4h": None,
                "momentum_24h": None,
                "momentum_percentile": None,
                "macd_signal": None,
                "trend_strength": None,
                "ema_signal": None,
            }

        candles = candles.sort_values("timestamp")
        closes = candles["close"].values

        # Calculate returns for different periods
        momentum_scores = {}
        for period in periods:
            # Need period+1 candles: current candle + period candles back
            if len(closes) >= period + 1:
                current_price = closes[-1]
                past_price = closes[-(period + 1)]
                return_pct = (current_price / past_price - 1) * 100
                momentum_scores[f"momentum_{period}h"] = return_pct
            else:
                momentum_scores[f"momentum_{period}h"] = None

        # Calculate percentile rank
        if len(closes) >= 25:
            # We need 24 returns, so we need 25 prices
            # diff(closes[-25:]) gives 24 differences
            # closes[-25:-1] gives the first 24 prices of that window
            recent_returns = np.diff(closes[-25:]) / closes[-25:-1] * 100
            current_return = momentum_scores.get("momentum_1h", 0)
            if current_return is not None and not np.isnan(current_return) and len(recent_returns) > 0:
                percentile = (recent_returns < current_return).sum() / len(recent_returns) * 100
                momentum_scores["momentum_percentile"] = percentile
            else:
                momentum_scores["momentum_percentile"] = None
        else:
            momentum_scores["momentum_percentile"] = None

        # Calculate MACD
        macd, signal, hist = calculate_macd(closes)
        if not np.isnan(macd[-1]) and not np.isnan(signal[-1]):
            # MACD Signal: 1 if MACD > Signal (Bullish), -1 if MACD < Signal (Bearish)
            momentum_scores["macd_signal"] = 1.0 if macd[-1] > signal[-1] else -1.0
            # Trend Strength: Normalized histogram
            momentum_scores["trend_strength"] = hist[-1] / (closes[-1] * 0.01) # Normalize by 1% of price
        else:
            momentum_scores["macd_signal"] = 0.0
            momentum_scores["trend_strength"] = 0.0

        # Calculate EMA Crossover (9/21)
        fast_ema, slow_ema, ema_signal = calculate_ema_crossover(closes, fast_period=9, slow_period=21)
        momentum_scores["ema_signal"] = float(ema_signal)

        return momentum_scores

    def calculate_mean_reversion(
        self,
        candles: pd.DataFrame,
        lookback_periods: int = 24,
    ) -> Dict[str, float]:
        """
        Calculate mean reversion factors including Bollinger Bands and RSI.
        
        Args:
            candles: DataFrame with OHLCV data sorted by timestamp
            lookback_periods: Number of periods for moving average
            
        Returns:
            Dictionary with mean reversion metrics
        """
        if len(candles) < lookback_periods:
            return {
                "mean_reversion_zscore": None,
                "rsi": None,
                "bb_position": None,
            }

        candles = candles.sort_values("timestamp")
        closes = candles["close"].values
        
        # Calculate z-score vs moving average
        ma = np.mean(closes[-lookback_periods:])
        std = np.std(closes[-lookback_periods:])
        current_price = closes[-1]
        
        if std > 0:
            zscore = (current_price - ma) / std
        else:
            zscore = 0.0

        # Calculate RSI
        rsi_series = calculate_rsi(closes, period=14)
        rsi = rsi_series[-1] if len(rsi_series) > 0 else 50.0

        # Calculate Bollinger Bands Position
        upper, middle, lower = calculate_bollinger_bands(closes, period=20)
        if not np.isnan(upper[-1]) and (upper[-1] - lower[-1]) > 0:
            # Position within bands: 0 = lower band, 1 = upper band, 0.5 = middle
            bb_pos = (current_price - lower[-1]) / (upper[-1] - lower[-1])
            # Normalize to centered range: -1 (lower) to 1 (upper)
            bb_position = (bb_pos - 0.5) * 2
        else:
            bb_position = 0.0

        return {
            "mean_reversion_zscore": zscore,
            "rsi": rsi,
            "bb_position": bb_position,
        }

    def calculate_volatility(
        self,
        candles: pd.DataFrame,
        period: int = 14
    ) -> Dict[str, float]:
        """
        Calculate volatility factors.
        
        Args:
            candles: DataFrame with OHLCV
            period: Period for ATR
            
        Returns:
            Dictionary with volatility metrics
        """
        if len(candles) < period + 1:
            return {"volatility_atr_pct": None}
            
        high = candles["high"].values
        low = candles["low"].values
        close = candles["close"].values
        
        atr = calculate_atr(high, low, close, period)
        current_atr = atr[-1]
        current_price = close[-1]
        
        if current_price > 0:
            atr_pct = (current_atr / current_price) * 100
        else:
            atr_pct = 0.0
            
        return {"volatility_atr_pct": atr_pct}

    def calculate_carry(
        self,
        funding_rate: Optional[float],
        mark_price: Optional[float],
        index_price: Optional[float],
    ) -> Dict[str, float]:
        """
        Calculate carry factors.
        
        Args:
            funding_rate: Current funding rate (8-hourly)
            mark_price: Mark price
            index_price: Index price
            
        Returns:
            Dictionary with carry metrics
        """
        # Annualize funding rate (assuming 8-hour funding)
        funding_annualized = None
        if funding_rate is not None:
            # Funding occurs 3 times per day (every 8 hours)
            funding_annualized = funding_rate * 3 * 365

        # Calculate basis (mark - index) / index
        basis = None
        if mark_price is not None and index_price is not None and index_price > 0:
            basis = (mark_price - index_price) / index_price * 100

        return {
            "carry_funding_annualized": funding_annualized,
            "carry_basis": basis,
        }

    def calculate_volume_factors(
        self,
        candles: pd.DataFrame,
        periods: List[int] = [1, 4, 24],
        lookback_periods: int = 24,
    ) -> Dict[str, float]:
        """
        Calculate volume-based factors.
        
        Args:
            candles: DataFrame with OHLCV data sorted by timestamp
            periods: List of periods (in hours) for volume momentum calculation
            lookback_periods: Number of periods for historical comparison
            
        Returns:
            Dictionary with volume metrics
        """
        if len(candles) < max(periods + [lookback_periods]):
            return {
                "volume_momentum_1h": None,
                "volume_momentum_4h": None,
                "volume_momentum_24h": None,
                "volume_anomaly_zscore": None,
                "volume_percentile": None,
                "volume_price_divergence": None,
            }

        candles = candles.sort_values("timestamp")
        volumes = candles["volume"].values
        closes = candles["close"].values
        
        # Calculate volume momentum (percentage change in volume)
        volume_momentum = {}
        for period in periods:
            if len(volumes) >= period:
                current_volume = volumes[-1]
                past_volume = volumes[-period] if period < len(volumes) else volumes[0]
                if past_volume > 0:
                    momentum_pct = (current_volume / past_volume - 1) * 100
                    volume_momentum[f"volume_momentum_{period}h"] = momentum_pct
                else:
                    volume_momentum[f"volume_momentum_{period}h"] = None
            else:
                volume_momentum[f"volume_momentum_{period}h"] = None

        # Calculate volume anomaly z-score (current volume vs historical average)
        if len(volumes) >= lookback_periods:
            historical_volumes = volumes[-lookback_periods:]
            mean_volume = np.mean(historical_volumes)
            std_volume = np.std(historical_volumes)
            current_volume = volumes[-1]
            
            if std_volume > 0:
                volume_anomaly_zscore = (current_volume - mean_volume) / std_volume
            else:
                volume_anomaly_zscore = 0.0
        else:
            volume_anomaly_zscore = None

        # Calculate volume percentile (rank vs historical distribution)
        if len(volumes) >= lookback_periods:
            historical_volumes = volumes[-lookback_periods:]
            current_volume = volumes[-1]
            percentile = (historical_volumes < current_volume).sum() / len(historical_volumes) * 100
            volume_percentile = percentile
        else:
            volume_percentile = None

        # Calculate volume-price divergence (correlation between volume changes and price changes)
        if len(candles) >= lookback_periods:
            # Calculate volume and price changes over the lookback period
            volume_changes = np.diff(volumes[-lookback_periods:])
            price_changes = np.diff(closes[-lookback_periods:])
            
            if len(volume_changes) > 1 and len(price_changes) > 1:
                # Normalize changes
                volume_changes_norm = (volume_changes - np.mean(volume_changes)) / (np.std(volume_changes) + 1e-10)
                price_changes_norm = (price_changes - np.mean(price_changes)) / (np.std(price_changes) + 1e-10)
                
                # Calculate correlation (divergence = 1 - |correlation|)
                if len(volume_changes_norm) > 1 and len(price_changes_norm) > 1:
                    correlation = np.corrcoef(volume_changes_norm, price_changes_norm)[0, 1]
                    if not np.isnan(correlation):
                        # Divergence: positive when correlation is negative (volume up, price down or vice versa)
                        volume_price_divergence = -correlation  # Negative correlation = positive divergence
                    else:
                        volume_price_divergence = 0.0
                else:
                    volume_price_divergence = None
            else:
                volume_price_divergence = None
        else:
            volume_price_divergence = None

        return {
            "volume_momentum_1h": volume_momentum.get("volume_momentum_1h"),
            "volume_momentum_4h": volume_momentum.get("volume_momentum_4h"),
            "volume_momentum_24h": volume_momentum.get("volume_momentum_24h"),
            "volume_anomaly_zscore": volume_anomaly_zscore,
            "volume_percentile": volume_percentile,
            "volume_price_divergence": volume_price_divergence,
        }

    def calculate_oi_factors(
        self,
        candles: pd.DataFrame,
        periods: List[int] = [1, 4, 24],
    ) -> Dict[str, float]:
        """
        Calculate Open Interest rate of change factors.

        Args:
            candles: DataFrame with OHLCV + open_interest data sorted by timestamp
            periods: List of periods (in hours) for OI change calculation

        Returns:
            Dictionary with OI metrics
        """
        if "open_interest" not in candles.columns or len(candles) < max(periods):
            return {
                "oi_change_1h": None,
                "oi_change_4h": None,
                "oi_change_24h": None,
            }

        candles = candles.sort_values("timestamp")
        oi_values = candles["open_interest"].values

        # Calculate OI rate of change for different periods
        oi_factors = {}
        for period in periods:
            if len(oi_values) >= period + 1:
                current_oi = oi_values[-1]
                past_oi = oi_values[-(period + 1)]
                if past_oi > 0 and not np.isnan(current_oi) and not np.isnan(past_oi):
                    oi_change_pct = (current_oi / past_oi - 1) * 100
                    oi_factors[f"oi_change_{period}h"] = oi_change_pct
                else:
                    oi_factors[f"oi_change_{period}h"] = None
            else:
                oi_factors[f"oi_change_{period}h"] = None

        return oi_factors

    def calculate_btc_correlation(
        self,
        asset_candles: pd.DataFrame,
        btc_candles: pd.DataFrame,
        lookback_periods: int = 24,
    ) -> Dict[str, float]:
        """
        Calculate correlation and beta relative to BTC.

        Args:
            asset_candles: DataFrame with asset OHLCV data
            btc_candles: DataFrame with BTC OHLCV data
            lookback_periods: Number of periods for correlation calculation

        Returns:
            Dictionary with correlation metrics
        """
        if len(asset_candles) < lookback_periods or len(btc_candles) < lookback_periods:
            return {
                "btc_correlation": None,
                "btc_beta": None,
            }

        # Align timestamps
        asset_candles = asset_candles.sort_values("timestamp")
        btc_candles = btc_candles.sort_values("timestamp")

        # Get the last N periods
        asset_closes = asset_candles["close"].tail(lookback_periods).values
        btc_closes = btc_candles["close"].tail(lookback_periods).values

        # Need same length
        min_len = min(len(asset_closes), len(btc_closes))
        if min_len < 2:
            return {
                "btc_correlation": None,
                "btc_beta": None,
            }

        asset_closes = asset_closes[-min_len:]
        btc_closes = btc_closes[-min_len:]

        # Calculate returns
        asset_returns = np.diff(asset_closes) / asset_closes[:-1]
        btc_returns = np.diff(btc_closes) / btc_closes[:-1]

        if len(asset_returns) < 2:
            return {
                "btc_correlation": None,
                "btc_beta": None,
            }

        # Calculate correlation
        correlation = np.corrcoef(asset_returns, btc_returns)[0, 1]
        if np.isnan(correlation):
            correlation = 0.0

        # Calculate beta (covariance / variance)
        covariance = np.cov(asset_returns, btc_returns)[0, 1]
        btc_variance = np.var(btc_returns)

        if btc_variance > 0:
            beta = covariance / btc_variance
        else:
            beta = 1.0

        return {
            "btc_correlation": correlation,
            "btc_beta": beta,
        }

    def normalize_to_btc(self, price: float, btc_price: float) -> float:
        """Normalize price to BTC terms."""
        if btc_price > 0:
            return price / btc_price
        return price

    def calculate_composite_score(
        self,
        momentum: Dict[str, float],
        mean_reversion: Dict[str, float],
        carry: Dict[str, float],
        volume: Optional[Dict[str, float]] = None,
        volatility: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculate composite factor score.
        
        Args:
            momentum: Momentum factor dictionary
            mean_reversion: Mean reversion factor dictionary
            carry: Carry factor dictionary
            volume: Volume factor dictionary (optional)
            volatility: Volatility factor dictionary (optional)
            
        Returns:
            Composite score
        """
        # Normalize individual factors to [-1, 1] range
        momentum_score = momentum.get("momentum_24h", 0) or 0
        # Add MACD influence
        macd_signal = momentum.get("macd_signal", 0) or 0
        momentum_combined = (momentum_score / 10) + (macd_signal * 0.5)
        momentum_normalized = np.tanh(momentum_combined)

        mean_reversion_score = mean_reversion.get("mean_reversion_zscore", 0) or 0
        # Add BB position influence (revert from extremes)
        bb_pos = mean_reversion.get("bb_position", 0) or 0
        # If bb_pos is high (>0.8), we expect reversion down. If low (<-0.8), reversion up.
        # This aligns with mean reversion logic: high score = potential short, low score = potential long
        # But here we want 'score' to indicate 'interestingness' or 'strength'.
        # Let's keep it simple: combine z-score and bb_pos
        mr_combined = (mean_reversion_score / 3) + (bb_pos * 0.5)
        mean_reversion_normalized = np.tanh(mr_combined)

        carry_score = carry.get("carry_funding_annualized", 0) or 0
        carry_normalized = np.tanh(carry_score / 50)

        # Volume factor normalization
        volume_normalized = 0.0
        if volume:
            volume_anomaly = volume.get("volume_anomaly_zscore", 0) or 0
            volume_divergence = volume.get("volume_price_divergence", 0) or 0
            volume_anomaly_norm = np.tanh(volume_anomaly / 3)
            volume_divergence_norm = np.tanh(volume_divergence / 2)
            volume_normalized = (volume_anomaly_norm + volume_divergence_norm) / 2

        # Weighted composite score
        composite = (
            self.factor_weights.momentum * momentum_normalized +
            self.factor_weights.mean_reversion * mean_reversion_normalized +
            self.factor_weights.carry * carry_normalized +
            self.factor_weights.volume * volume_normalized
        )

        return composite

    def identify_outliers(
        self,
        scores: List[Dict[str, float]],
        z_score_threshold: Optional[float] = None,
        top_n: Optional[int] = None,
        bottom_n: Optional[int] = None,
        use_iqr: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Identify outliers based on composite scores using IQR or Z-score.
        
        Args:
            scores: List of score dictionaries
            z_score_threshold: Threshold for z-score (if not using IQR)
            top_n: Top N outliers
            bottom_n: Bottom N outliers
            use_iqr: Whether to use Interquartile Range (more robust) instead of Z-score
            
        Returns:
            List of score dictionaries with outlier flags
        """
        if not scores:
            return []

        df = pd.DataFrame(scores)
        composite_scores = df["composite_score"].dropna()

        if len(composite_scores) == 0:
            return scores

        # Flag outliers
        thresholds = self.config.thresholds
        
        if use_iqr and len(composite_scores) >= 4:
            # IQR Method (Robust to extreme outliers)
            Q1 = composite_scores.quantile(0.25)
            Q3 = composite_scores.quantile(0.75)
            IQR = Q3 - Q1
            
            # Standard multiplier is 1.5, but for crypto we might want 2.0 or 2.5
            multiplier = 2.0 
            lower_bound = Q1 - multiplier * IQR
            upper_bound = Q3 + multiplier * IQR
            
            results = []
            for score_dict in scores:
                score_dict = score_dict.copy()
                composite = score_dict.get("composite_score")
                
                if composite is None:
                    score_dict["is_outlier"] = False
                    score_dict["outlier_type"] = None
                else:
                    if composite > upper_bound:
                        score_dict["is_outlier"] = True
                        score_dict["outlier_type"] = "top"
                    elif composite < lower_bound:
                        score_dict["is_outlier"] = True
                        score_dict["outlier_type"] = "bottom"
                    else:
                        score_dict["is_outlier"] = False
                        score_dict["outlier_type"] = None
                results.append(score_dict)
                
        else:
            # Z-Score Method (Legacy/Fallback)
            mean_score = composite_scores.mean()
            std_score = composite_scores.std()
            z_threshold = z_score_threshold or thresholds.outlier_z_score

            if std_score > 0:
                z_scores = (composite_scores - mean_score) / std_score
            else:
                z_scores = pd.Series([0] * len(composite_scores), index=composite_scores.index)
            
            z_score_map = z_scores.to_dict()

            results = []
            for score_dict in scores:
                score_dict = score_dict.copy()
                composite = score_dict.get("composite_score")

                if composite is None:
                    score_dict["is_outlier"] = False
                    score_dict["outlier_type"] = None
                else:
                    matching_rows = df[df["composite_score"] == composite]
                    if not matching_rows.empty:
                        df_idx = matching_rows.index[0]
                        z_score = z_score_map.get(df_idx, 0)
                    else:
                        z_score = 0
                    
                    is_outlier = abs(z_score) >= z_threshold
                    score_dict["is_outlier"] = is_outlier
                    score_dict["outlier_type"] = "top" if z_score > 0 else "bottom" if z_score < 0 else None
                results.append(score_dict)

        # Also flag top/bottom N (always do this to ensure we have something to show)
        if top_n or bottom_n:
            sorted_scores = sorted(
                [r for r in results if r.get("composite_score") is not None],
                key=lambda x: x["composite_score"],
                reverse=True,
            )

            top_n = top_n or thresholds.top_n_outliers
            bottom_n = bottom_n or thresholds.bottom_n_outliers

            # Ensure we don't double-count if already flagged by IQR/Z-score
            # But we want to ensure at least Top N are flagged
            for i, result in enumerate(sorted_scores[:top_n]):
                result["is_outlier"] = True
                result["outlier_type"] = "top"

            for i, result in enumerate(sorted_scores[-bottom_n:]):
                result["is_outlier"] = True
                result["outlier_type"] = "bottom"

        return results
