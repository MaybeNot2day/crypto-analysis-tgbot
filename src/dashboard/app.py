"""
Streamlit dashboard frontend.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Crypto Outlier Detection Dashboard",
    page_icon="📊",
    layout="wide",
)

# API base URL
API_BASE_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

# Title
st.title("📊 Crypto Outlier Detection Dashboard")
st.markdown("Real-time analysis of top 100 crypto assets by market cap")


@st.cache_data(ttl=60)
def fetch_data(endpoint: str):
    """Fetch data from API."""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching {endpoint}: {e}")
        return []


# Sidebar filters
st.sidebar.header("Filters")
exchange_filter = st.sidebar.selectbox("Exchange", ["All", "binance"])
symbol_filter = st.sidebar.selectbox("Symbol", ["All"])

# Fetch universe for symbol filter
universe = fetch_data("/api/universe")
if universe:
    symbols = ["All"] + [asset["spot_symbol"] or asset["futures_symbol"] for asset in universe if asset.get("spot_symbol") or asset.get("futures_symbol")]
    symbol_filter = st.sidebar.selectbox("Symbol", symbols, index=0)

# Main content
try:
    # Status section
    status = fetch_data("/api/status")
    if status:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Status", status.get("status", "unknown").upper())
        with col2:
            latest_ts = status.get("latest_data_timestamp")
            if latest_ts:
                st.metric("Last Update", datetime.fromisoformat(latest_ts).strftime("%H:%M:%S UTC+4"))
            else:
                st.metric("Last Update", "N/A")
        with col3:
            st.metric("Outliers Detected", status.get("outlier_count", 0))
        with col4:
            st.metric("Assets Tracked", len(universe) if universe else 0)
    
    # Fetch factor scores
    factor_scores = fetch_data("/api/factors")
    
    if factor_scores:
        df_scores = pd.DataFrame(factor_scores)
        df_scores["timestamp"] = pd.to_datetime(df_scores["timestamp"])
        
        # Apply filters
        if exchange_filter != "All":
            df_scores = df_scores[df_scores["exchange"] == exchange_filter]
        if symbol_filter != "All":
            df_scores = df_scores[df_scores["symbol"] == symbol_filter]
        
        # Get latest scores only
        if not df_scores.empty:
            latest_timestamp = df_scores["timestamp"].max()
            df_latest = df_scores[df_scores["timestamp"] == latest_timestamp]
            
            # Outliers section
            st.header("🚨 Outliers")
            outliers = fetch_data("/api/outliers?limit=20")
            if outliers:
                df_outliers = pd.DataFrame(outliers)
                # Include new metrics in outliers display
                outlier_cols = ["symbol", "composite_score", "momentum_24h", "ema_signal", "macd_signal",
                               "mean_reversion_zscore", "carry_funding_annualized", "volume_anomaly_zscore",
                               "oi_change_24h", "btc_correlation", "outlier_type"]
                available_cols = [col for col in outlier_cols if col in df_outliers.columns]
                st.dataframe(df_outliers[available_cols].head(10), width='stretch')
            
            # Factor visualization
            st.header("📈 Factor Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Momentum chart
                if "momentum_24h" in df_latest.columns:
                    df_momentum = df_latest.sort_values("momentum_24h", ascending=False).head(20)
                    fig = px.bar(
                        df_momentum,
                        x="symbol",
                        y="momentum_24h",
                        title="Top 20 Momentum (24h)",
                        labels={"momentum_24h": "Momentum %", "symbol": "Symbol"},
                    )
                    st.plotly_chart(fig, width='stretch')
            
            with col2:
                # Mean reversion chart
                if "mean_reversion_zscore" in df_latest.columns:
                    df_mr = df_latest.sort_values("mean_reversion_zscore", ascending=False).head(20)
                    fig = px.bar(
                        df_mr,
                        x="symbol",
                        y="mean_reversion_zscore",
                        title="Top 20 Mean Reversion Z-Score",
                        labels={"mean_reversion_zscore": "Z-Score", "symbol": "Symbol"},
                    )
                    st.plotly_chart(fig, width='stretch')
            
            # Funding and OI Analysis
            st.header("💸 Funding & Open Interest")
            col1, col2 = st.columns(2)
            
            with col1:
                # Funding APR vs Momentum Scatter
                if "funding_rate_apr" in df_latest.columns and "momentum_24h" in df_latest.columns:
                    df_funding = df_latest.dropna(subset=["funding_rate_apr", "momentum_24h"])
                    fig = px.scatter(
                        df_funding,
                        x="funding_rate_apr",
                        y="momentum_24h",
                        hover_data=["symbol", "composite_score"],
                        title="Funding APR vs Price Momentum",
                        labels={"funding_rate_apr": "Funding APR %", "momentum_24h": "Price Momentum (24h)"},
                        color="composite_score",
                        color_continuous_scale="RdBu",
                    )
                    # Add reference lines
                    fig.add_vline(x=0, line_dash="dash", line_color="gray")
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, width='stretch')

            with col2:
                # Open Interest vs Momentum Scatter
                # Note: Using raw OI for now. Ideally we want OI Z-Score.
                if "open_interest" in df_latest.columns and "momentum_24h" in df_latest.columns:
                    df_oi = df_latest.dropna(subset=["open_interest", "momentum_24h"])
                    # Log scale for OI often helps visualization
                    fig = px.scatter(
                        df_oi,
                        x="open_interest",
                        y="momentum_24h",
                        hover_data=["symbol", "funding_rate_apr"],
                        title="Open Interest vs Price Momentum",
                        labels={"open_interest": "Open Interest (Raw)", "momentum_24h": "Price Momentum (24h)"},
                        color="funding_rate_apr",
                        color_continuous_scale="Viridis",
                        log_x=True,
                    )
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, width='stretch')

            # Volume analysis section
            st.header("📊 Volume Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Volume anomaly chart
                if "volume_anomaly_zscore" in df_latest.columns:
                    df_volume = df_latest.sort_values("volume_anomaly_zscore", ascending=False, na_position='last').head(20)
                    df_volume = df_volume.dropna(subset=["volume_anomaly_zscore"])
                    if not df_volume.empty:
                        fig = px.bar(
                            df_volume,
                            x="symbol",
                            y="volume_anomaly_zscore",
                            title="Top 20 Volume Anomalies (Z-Score)",
                            labels={"volume_anomaly_zscore": "Volume Anomaly Z-Score", "symbol": "Symbol"},
                            color="volume_anomaly_zscore",
                            color_continuous_scale="Reds",
                        )
                        st.plotly_chart(fig, width='stretch')
            
            with col2:
                # Volume momentum chart
                if "volume_momentum_24h" in df_latest.columns:
                    df_vol_momentum = df_latest.sort_values("volume_momentum_24h", ascending=False, na_position='last').head(20)
                    df_vol_momentum = df_vol_momentum.dropna(subset=["volume_momentum_24h"])
                    if not df_vol_momentum.empty:
                        fig = px.bar(
                            df_vol_momentum,
                            x="symbol",
                            y="volume_momentum_24h",
                            title="Top 20 Volume Momentum (24h)",
                            labels={"volume_momentum_24h": "Volume Momentum %", "symbol": "Symbol"},
                            color="volume_momentum_24h",
                            color_continuous_scale="Blues",
                        )
                        st.plotly_chart(fig, width='stretch')
            
            # Volume-Price Divergence scatter plot
            if "volume_price_divergence" in df_latest.columns and "momentum_24h" in df_latest.columns:
                df_divergence = df_latest.dropna(subset=["volume_price_divergence", "momentum_24h"])
                if not df_divergence.empty:
                    fig = px.scatter(
                        df_divergence,
                        x="volume_price_divergence",
                        y="momentum_24h",
                        hover_data=["symbol", "volume_anomaly_zscore", "composite_score"],
                        title="Volume-Price Divergence Analysis",
                        labels={"volume_price_divergence": "Volume-Price Divergence", "momentum_24h": "Price Momentum (24h)"},
                        color="volume_anomaly_zscore",
                        color_continuous_scale="Viridis",
                    )
                    st.plotly_chart(fig, width='stretch')
            
            # Factor scatter plot
            st.subheader("Price Change vs Composite Score")
            if "composite_score" in df_latest.columns:
                # Calculate price change (simplified)
                fig = px.scatter(
                    df_latest,
                    x="composite_score",
                    y="momentum_24h",
                    hover_data=["symbol", "rsi", "carry_funding_annualized", "volume_anomaly_zscore"],
                    title="Factor Scatter Plot",
                    labels={"composite_score": "Composite Score", "momentum_24h": "Momentum (24h)"},
                )
                st.plotly_chart(fig, width='stretch')

            # BTC Correlation Analysis
            st.header("🔗 BTC Correlation & Open Interest")
            col1, col2 = st.columns(2)

            with col1:
                # BTC Beta vs Momentum
                if "btc_beta" in df_latest.columns and "momentum_24h" in df_latest.columns:
                    df_btc = df_latest.dropna(subset=["btc_beta", "momentum_24h"])
                    fig = px.scatter(
                        df_btc,
                        x="btc_beta",
                        y="momentum_24h",
                        hover_data=["symbol", "btc_correlation"],
                        title="BTC Beta vs Price Momentum",
                        labels={"btc_beta": "BTC Beta", "momentum_24h": "Price Momentum (24h)"},
                        color="btc_correlation",
                        color_continuous_scale="RdYlGn",
                    )
                    fig.add_vline(x=1.0, line_dash="dash", line_color="gray", annotation_text="Beta = 1")
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, width='stretch')

            with col2:
                # OI Change vs Price Momentum
                if "oi_change_24h" in df_latest.columns and "momentum_24h" in df_latest.columns:
                    df_oi_change = df_latest.dropna(subset=["oi_change_24h", "momentum_24h"])
                    fig = px.scatter(
                        df_oi_change,
                        x="oi_change_24h",
                        y="momentum_24h",
                        hover_data=["symbol", "funding_rate_apr"],
                        title="OI Change (24h) vs Price Momentum",
                        labels={"oi_change_24h": "OI Change (%)", "momentum_24h": "Price Momentum (24h)"},
                        color="funding_rate_apr",
                        color_continuous_scale="Viridis",
                    )
                    fig.add_vline(x=0, line_dash="dash", line_color="gray")
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, width='stretch')

            # Detailed table
            st.header("📊 Detailed Factor Scores")
            st.dataframe(df_latest, width='stretch')
            
        else:
            st.warning("No data available for the selected filters")
    else:
        st.warning("Unable to fetch factor scores. Please check API connection.")
        
except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    logger.error(f"Dashboard error: {e}", exc_info=True)
