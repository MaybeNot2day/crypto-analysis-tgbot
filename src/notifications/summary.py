"""
Market summary generator for Telegram notifications.
"""

import logging
import hashlib
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
        Uses a 'signature' approach that focuses on meaningful changes:
        - Which assets are outliers (symbols, not exact scores)
        - Market sentiment (rounded percentages)
        - Which opportunities are identified (symbols, not exact values)
        This prevents minor score fluctuations from triggering duplicate sends.
        """
        import re
        
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
                # Extract sentiment emoji (🟢, 🔴, 🟡)
                sentiment_match = re.search(r'[🟢🔴🟡]', line)
                if sentiment_match:
                    signature_parts.append(f"sentiment:{sentiment_match.group()}")
            
            if "Bullish:" in line:
                # Extract percentage and round to nearest 2% (less aggressive)
                pct_match = re.search(r'(\d+\.\d+)%', line)
                if pct_match:
                    pct = float(pct_match.group(1))
                    rounded = round(pct / 2) * 2  # Round to nearest 2%
                    signature_parts.append(f"bullish:{rounded:.0f}%")
            
            if "Bearish:" in line:
                # Extract percentage and round to nearest 2% (less aggressive)
                pct_match = re.search(r'(\d+\.\d+)%', line)
                if pct_match:
                    pct = float(pct_match.group(1))
                    rounded = round(pct / 2) * 2  # Round to nearest 2%
                    signature_parts.append(f"bearish:{rounded:.0f}%")
            
            if "Avg 24h Momentum:" in line:
                # Extract and round momentum to nearest 50% (less aggressive)
                momentum_match = re.search(r'([+-]?\d+\.\d+)%', line)
                if momentum_match:
                    momentum = float(momentum_match.group(1))
                    rounded = round(momentum / 50) * 50  # Round to nearest 50%
                    signature_parts.append(f"avg_momentum:{rounded:.0f}%")
            
            # Extract symbols from outlier/opportunity lines (ignore exact scores)
            if "•" in line:
                # Match symbols ending with USDT, USDC, or BTC
                symbol_match = re.search(r'\b([A-Z0-9]+(?:USDT|USDC|BTC))\b', line)
                if symbol_match:
                    symbol = symbol_match.group(1)
                    if current_section == "top_outliers":
                        signature_parts.append(f"top_outlier:{symbol}")
                    elif current_section == "bottom_outliers":
                        signature_parts.append(f"bottom_outlier:{symbol}")
                    elif current_section == "opportunities":
                        signature_parts.append(f"opportunity:{symbol}")
            
            # High Volume Anomalies count
            if "High Volume Anomalies:" in line:
                count_match = re.search(r'(\d+) assets', line)
                if count_match:
                    signature_parts.append(f"volume_anomalies:{count_match.group(1)}")
        
        # Sort signature parts for consistent hashing
        signature_parts.sort()
        signature = "|".join(signature_parts)
        
        # Generate hash from signature
        return hashlib.md5(signature.encode('utf-8')).hexdigest()

    def _analyze_market_state(self, scores_df: pd.DataFrame) -> str:
        """Analyze overall market state."""
        if scores_df.empty:
            return "No data available for analysis."
        
        # Calculate statistics
        total_assets = len(scores_df)
        
        # Count positive vs negative composite scores
        positive_scores = scores_df[scores_df["composite_score"] > 0]
        negative_scores = scores_df[scores_df["composite_score"] < 0]
        
        bullish_pct = len(positive_scores) / total_assets * 100 if total_assets > 0 else 0
        bearish_pct = len(negative_scores) / total_assets * 100 if total_assets > 0 else 0
        
        # Average momentum (already in percentages, don't multiply by 100 again)
        avg_momentum_24h = scores_df["momentum_24h"].mean() if "momentum_24h" in scores_df.columns else 0
        avg_momentum_24h = avg_momentum_24h if not pd.isna(avg_momentum_24h) else 0
        
        # Volume analysis
        high_volume_anomalies = 0
        if "volume_anomaly_zscore" in scores_df.columns:
            high_volume_anomalies = len(scores_df[scores_df["volume_anomaly_zscore"] > 2])
        
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
        ]
        
        if high_volume_anomalies > 0:
            lines.append(f"📊 High Volume Anomalies: {high_volume_anomalies} assets")
        
        return "\n".join(lines)

    def _format_outliers(self, outliers_df: pd.DataFrame) -> str:
        """Format outliers information."""
        if outliers_df.empty:
            return "No outliers detected."
        
        # Separate top and bottom outliers
        top_outliers = outliers_df[outliers_df["outlier_type"] == "top"].head(5)
        bottom_outliers = outliers_df[outliers_df["outlier_type"] == "bottom"].head(5)
        
        lines = []
        
        if not top_outliers.empty:
            lines.append("🟢 *Top Outliers \\(Bullish\\):*")
            for _, row in top_outliers.iterrows():
                symbol = row.get("symbol", "N/A")
                composite = row.get("composite_score", 0)
                momentum = row.get("momentum_24h", 0)
                # Momentum is already in percentages, don't multiply by 100
                momentum_pct = momentum if not pd.isna(momentum) else 0
                
                # Get key factor
                volume_anomaly = row.get("volume_anomaly_zscore", 0)
                if not pd.isna(volume_anomaly) and volume_anomaly > 2:
                    factor_note = f"📊 Vol anomaly: {volume_anomaly:.1f}"
                elif not pd.isna(momentum) and abs(momentum) > 5:  # Fix: threshold is 5% not 0.05%
                    factor_note = f"📈 Momentum: {momentum_pct:+.1f}%"
                else:
                    factor_note = ""
                
                lines.append(f"  • {symbol}: Score {composite:+.3f} {factor_note}")
        
        if not bottom_outliers.empty:
            lines.append("\n🔴 *Bottom Outliers \\(Bearish\\):*")
            for _, row in bottom_outliers.iterrows():
                symbol = row.get("symbol", "N/A")
                composite = row.get("composite_score", 0)
                momentum = row.get("momentum_24h", 0)
                # Momentum is already in percentages, don't multiply by 100
                momentum_pct = momentum if not pd.isna(momentum) else 0
                
                # Get key factor
                volume_anomaly = row.get("volume_anomaly_zscore", 0)
                if not pd.isna(volume_anomaly) and volume_anomaly > 2:
                    factor_note = f"📊 Vol anomaly: {volume_anomaly:.1f}"
                elif not pd.isna(momentum) and abs(momentum) > 5:  # Fix: threshold is 5% not 0.05%
                    factor_note = f"📈 Momentum: {momentum_pct:+.1f}%"
                else:
                    factor_note = ""
                
                lines.append(f"  • {symbol}: Score {composite:+.3f} {factor_note}")
        
        return "\n".join(lines)

    def _identify_opportunities(
        self, outliers_df: pd.DataFrame, scores_df: pd.DataFrame
    ) -> str:
        """Identify top opportunities based on multiple factors."""
        if scores_df.empty:
            return "No opportunities identified."
        
        opportunities = []
        
        # Look for assets with strong momentum and volume
        if "momentum_24h" in scores_df.columns and "volume_anomaly_zscore" in scores_df.columns:
            # Fix: momentum is already in %, so threshold should be 5% not 0.05%
            strong_momentum = scores_df[
                (scores_df["momentum_24h"] > 5) &
                (scores_df["volume_anomaly_zscore"] > 1.5)
            ].sort_values("composite_score", ascending=False).head(3)
            
            for _, row in strong_momentum.iterrows():
                symbol = row.get("symbol", "N/A")
                momentum = row.get("momentum_24h", 0)  # Already in percentages
                volume_anomaly = row.get("volume_anomaly_zscore", 0)
                opportunities.append(
                    f"  • {symbol}: Strong momentum \\({momentum:+.1f}%\\) \\+ high volume"
                )
        
        # Look for mean reversion opportunities (oversold)
        if "mean_reversion_zscore" in scores_df.columns:
            oversold = scores_df[
                (scores_df["mean_reversion_zscore"] < -2) &
                (scores_df["composite_score"] > -0.3)
            ].sort_values("mean_reversion_zscore").head(2)
            
            for _, row in oversold.iterrows():
                symbol = row.get("symbol", "N/A")
                zscore = row.get("mean_reversion_zscore", 0)
                opportunities.append(
                    f"  • {symbol}: Oversold \\(z\\-score: {zscore:.2f}\\) \\- potential bounce"
                )
        
        if opportunities:
            return "\n".join(opportunities)
        else:
            return "No specific opportunities identified at this time."
