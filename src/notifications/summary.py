"""
Market summary generator for Telegram notifications.
"""

import logging
import hashlib
import re
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from src.utils.timezone import now_utc4

logger = logging.getLogger(__name__)


class MarketSummaryGenerator:
    """Generate market summaries from analysis results."""

    def __init__(self):
        """Initialize summary generator."""
        pass

    def generate_summary(
        self,
        outliers_df: pd.DataFrame,
        latest_scores_df: pd.DataFrame,
        market_stats: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a comprehensive market summary.
        
        Args:
            outliers_df: DataFrame with outlier information
            latest_scores_df: DataFrame with latest factor scores for all assets
            market_stats: Optional dictionary with market statistics
            
        Returns:
            Formatted summary string
        """
        timestamp = now_utc4().strftime("%Y-%m-%d %H:%M:%S UTC+4")
        
        summary_parts = []
        
        # Header
        summary_parts.append(f"📊 *Market Analysis Summary*")
        summary_parts.append(f"⏰ {timestamp}")
        summary_parts.append("─" * 40)
        
        # Market state overview
        summary_parts.append("\n📈 *Market State Overview*")
        market_state = self._analyze_market_state(latest_scores_df)
        summary_parts.append(market_state)
        
        # Outliers section
        if not outliers_df.empty:
            summary_parts.append("\n🚨 *Key Outliers*")
            outliers_summary = self._format_outliers(outliers_df)
            summary_parts.append(outliers_summary)
        else:
            summary_parts.append("\n🚨 *Outliers*")
            summary_parts.append("No significant outliers detected at this time.")
        
        # Top opportunities
        summary_parts.append("\n💎 *Top Opportunities*")
        opportunities = self._identify_opportunities(outliers_df, latest_scores_df)
        summary_parts.append(opportunities)
        
        summary_text = "\n".join(summary_parts)
        
        # Telegram has a 4096 character limit - truncate if needed
        if len(summary_text) > 4096:
            logger.warning(f"Summary too long ({len(summary_text)} chars), truncating to 4096")
            summary_text = summary_text[:4090] + "\n..."
        
        return summary_text
    
    def generate_summary_hash(self, summary_text: str) -> str:
        """
        Generate a hash for the summary text for deduplication.
        """
        lines = summary_text.split("\n")
        signature_parts = []
        current_section = None  # Track which section we're in
        
        for line in lines:
            # Skip timestamp and separator lines
            if "⏰" in line or line.strip() == "─" * 40 or line.strip() == "":
                continue
            
            # Track section headers
            if "Top Outliers" in line or "Bullish" in line:
                current_section = "top_outliers"
            elif "Bottom Outliers" in line or "Bearish" in line:
                current_section = "bottom_outliers"
            elif "Top Opportunities" in line:
                current_section = "opportunities"
            
            # Market state: Extract sentiment and rounded percentages
            if "Sentiment:" in line:
                sentiment_match = re.search(r'[🟢🔴🟡]', line)
                if sentiment_match:
                    signature_parts.append(f"sentiment:{sentiment_match.group()}")
            
            if "Bullish:" in line:
                pct_match = re.search(r'(\d+\.\d+)%', line)
                if pct_match:
                    pct = float(pct_match.group(1))
                    rounded = round(pct / 2) * 2
                    signature_parts.append(f"bullish:{rounded:.0f}%")
            
            if "Bearish:" in line:
                pct_match = re.search(r'(\d+\.\d+)%', line)
                if pct_match:
                    pct = float(pct_match.group(1))
                    rounded = round(pct / 2) * 2
                    signature_parts.append(f"bearish:{rounded:.0f}%")
            
            # Extract symbols from outlier/opportunity lines
            if "•" in line:
                symbol_match = re.search(r'\b([A-Z0-9]+(?:USDT|USDC|BTC))\b', line)
                if symbol_match:
                    symbol = symbol_match.group(1)
                    if current_section == "top_outliers":
                        signature_parts.append(f"top_outlier:{symbol}")
                    elif current_section == "bottom_outliers":
                        signature_parts.append(f"bottom_outlier:{symbol}")
                    elif current_section == "opportunities":
                        signature_parts.append(f"opportunity:{symbol}")
        
        # Sort signature parts for consistent hashing
        signature_parts.sort()
        signature = "|".join(signature_parts)
        
        return hashlib.md5(signature.encode('utf-8')).hexdigest()

    def _analyze_market_state(self, scores_df: pd.DataFrame) -> str:
        """Analyze overall market state."""
        if scores_df.empty:
            return "No data available for analysis."
        
        # Calculate statistics
        total_assets = len(scores_df)
        
        positive_scores = scores_df[scores_df["composite_score"] > 0]
        negative_scores = scores_df[scores_df["composite_score"] < 0]
        
        bullish_pct = len(positive_scores) / total_assets * 100 if total_assets > 0 else 0
        bearish_pct = len(negative_scores) / total_assets * 100 if total_assets > 0 else 0
        
        # Average momentum
        avg_momentum_24h = scores_df["momentum_24h"].mean() if "momentum_24h" in scores_df.columns else 0
        avg_momentum_24h = avg_momentum_24h if not pd.isna(avg_momentum_24h) else 0
        
        # Average Volatility
        avg_volatility = scores_df["volatility_atr_pct"].mean() if "volatility_atr_pct" in scores_df.columns else 0
        avg_volatility = avg_volatility if not pd.isna(avg_volatility) else 0

        # Market sentiment
        if bullish_pct > 60:
            sentiment = "🟢 *Bullish*"
        elif bearish_pct > 60:
            sentiment = "🔴 *Bearish*"
        else:
            sentiment = "🟡 *Mixed*"
        
        lines = [
            f"📊 Analyzed: {total_assets} assets",
            f"📈 Sentiment: {sentiment}",
            f"🟢 Bullish: {bullish_pct:.1f}% \\({len(positive_scores)} assets\\)",
            f"🔴 Bearish: {bearish_pct:.1f}% \\({len(negative_scores)} assets\\)",
            f"📊 Avg 24h Momentum: {avg_momentum_24h:+.2f}%",
            f"⚡ Avg Volatility: {avg_volatility:.2f}%",
        ]
        
        return "\n".join(lines)

    def _format_outliers(self, outliers_df: pd.DataFrame) -> str:
        """Format outliers information."""
        if outliers_df.empty:
            return "No outliers detected."
        
        # Separate top and bottom outliers
        top_outliers = outliers_df[outliers_df["outlier_type"] == "top"].head(5)
        bottom_outliers = outliers_df[outliers_df["outlier_type"] == "bottom"].head(5)
        
        lines = []
        
        def get_factor_note(row):
            # Prioritize signals
            macd_signal = row.get("macd_signal", 0)
            bb_pos = row.get("bb_position", 0)
            rsi = row.get("rsi", 50)
            
            notes = []
            if macd_signal == 1:
                notes.append("MACD Bull")
            elif macd_signal == -1:
                notes.append("MACD Bear")
                
            if bb_pos > 0.8:
                notes.append("Upper BB")
            elif bb_pos < -0.8:
                notes.append("Lower BB")
                
            if rsi > 70:
                notes.append(f"RSI {rsi:.0f}")
            elif rsi < 30:
                notes.append(f"RSI {rsi:.0f}")
                
            return ", ".join(notes) if notes else ""

        if not top_outliers.empty:
            lines.append("🟢 *Top Outliers \\(Bullish\\):*")
            for _, row in top_outliers.iterrows():
                symbol = row.get("symbol", "N/A")
                composite = row.get("composite_score", 0)
                note = get_factor_note(row)
                note_str = f" \\({note}\\)" if note else ""
                lines.append(f"  • {symbol}: Score {composite:+.2f}{note_str}")
        
        if not bottom_outliers.empty:
            lines.append("\n🔴 *Bottom Outliers \\(Bearish\\):*")
            for _, row in bottom_outliers.iterrows():
                symbol = row.get("symbol", "N/A")
                composite = row.get("composite_score", 0)
                note = get_factor_note(row)
                note_str = f" \\({note}\\)" if note else ""
                lines.append(f"  • {symbol}: Score {composite:+.2f}{note_str}")
        
        return "\n".join(lines)

    def _identify_opportunities(
        self, outliers_df: pd.DataFrame, scores_df: pd.DataFrame
    ) -> str:
        """Identify top opportunities based on multiple factors."""
        if scores_df.empty:
            return "No opportunities identified."

        long_opportunities = []
        short_opportunities = []

        # LONG OPPORTUNITIES
        # 1. Strong Bullish Trend (MACD + Momentum + EMA)
        if "macd_signal" in scores_df.columns and "momentum_24h" in scores_df.columns:
            trend_opps = scores_df[
                (scores_df["macd_signal"] == 1) &
                (scores_df["momentum_24h"] > 3) &
                (scores_df["rsi"] < 70)  # Not overbought yet
            ].sort_values("composite_score", ascending=False).head(2)

            for _, row in trend_opps.iterrows():
                symbol = row.get("symbol", "N/A")
                ema_signal = row.get("ema_signal", 0)
                ema_str = " \\+ EMA" if ema_signal == 1 else ""
                long_opportunities.append(f"  • {symbol}: Strong Trend \\(MACD Bull{ema_str}\\)")

        # 2. Oversold Bounce (RSI + BB)
        if "rsi" in scores_df.columns and "bb_position" in scores_df.columns:
            oversold = scores_df[
                (scores_df["rsi"] < 30) &
                (scores_df["bb_position"] < -0.9)
            ].sort_values("rsi").head(2)

            for _, row in oversold.iterrows():
                symbol = row.get("symbol", "N/A")
                rsi = row.get("rsi", 0)
                long_opportunities.append(f"  • {symbol}: Oversold \\(RSI {rsi:.0f} \\+ Lower BB\\)")

        # SHORT OPPORTUNITIES
        # 1. Overbought with Bearish Signals (RSI + BB + MACD/EMA)
        if "rsi" in scores_df.columns and "bb_position" in scores_df.columns:
            overbought = scores_df[
                (scores_df["rsi"] > 70) &
                (scores_df["bb_position"] > 0.9)
            ].sort_values("rsi", ascending=False).head(2)

            for _, row in overbought.iterrows():
                symbol = row.get("symbol", "N/A")
                rsi = row.get("rsi", 0)
                macd_signal = row.get("macd_signal", 0)
                ema_signal = row.get("ema_signal", 0)

                signals = []
                if macd_signal == -1:
                    signals.append("MACD Bear")
                if ema_signal == -1:
                    signals.append("EMA Bear")

                signal_str = " \\+ " + "/".join(signals) if signals else ""
                short_opportunities.append(f"  • {symbol}: Overbought \\(RSI {rsi:.0f}{signal_str}\\)")

        # 2. Negative Carry Shorts (Negative Funding + Downtrend)
        if "funding_rate_apr" in scores_df.columns and "momentum_24h" in scores_df.columns:
            negative_carry = scores_df[
                (scores_df["funding_rate_apr"] < -10) &  # Negative funding > 10% APR
                (scores_df["momentum_24h"] < 0)  # Downtrend
            ].sort_values("funding_rate_apr").head(2)

            for _, row in negative_carry.iterrows():
                symbol = row.get("symbol", "N/A")
                funding_apr = row.get("funding_rate_apr", 0)
                short_opportunities.append(f"  • {symbol}: Negative Carry \\(Funding {funding_apr:.1f}% APR\\)")

        # 3. Volume Divergence (Price Rising, Volume Declining)
        if "volume_price_divergence" in scores_df.columns and "momentum_24h" in scores_df.columns:
            divergence = scores_df[
                (scores_df["volume_price_divergence"] > 0.5) &  # Strong divergence
                (scores_df["momentum_24h"] > 0) &  # Price rising
                (scores_df["rsi"] > 65)  # Already extended
            ].sort_values("volume_price_divergence", ascending=False).head(2)

            for _, row in divergence.iterrows():
                symbol = row.get("symbol", "N/A")
                short_opportunities.append(f"  • {symbol}: Volume Divergence \\(Weak Rally\\)")

        # Format output
        output_parts = []

        if long_opportunities:
            output_parts.append("🟢 *Long Opportunities:*")
            output_parts.extend(long_opportunities)
        else:
            output_parts.append("🟢 *Long Opportunities:* None at this time")

        if short_opportunities:
            output_parts.append("\n🔴 *Short Opportunities:*")
            output_parts.extend(short_opportunities)
        else:
            output_parts.append("\n🔴 *Short Opportunities:* None at this time")

        return "\n".join(output_parts) if output_parts else "No specific opportunities identified at this time."
