"""
ETL Pipeline orchestrator for hourly data collection and factor computation.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import gc
from src.config import Config, load_config
from src.universe.builder import UniverseBuilder
from src.adapters.binance import BinanceAdapter
from src.pipeline.storage import DataStorage
from src.factors.calculator import FactorCalculator
from src.utils.timezone import now_utc4
from src.notifications import TelegramBot, MarketSummaryGenerator

logger = logging.getLogger(__name__)


class Pipeline:
    """Main ETL pipeline orchestrator."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize pipeline."""
        self.config = config or load_config()
        self.universe_builder = UniverseBuilder(self.config)
        self.storage = DataStorage(self.config)
        self.factor_calculator = FactorCalculator(self.config)
        self.telegram_bot = TelegramBot(self.config.telegram)
        self.summary_generator = MarketSummaryGenerator()
        
        # Initialize adapters
        self.adapters = {}
        for name, exchange_config in self.config.exchanges.items():
            if exchange_config.enabled:
                if name.lower() == "binance":
                    self.adapters[name] = BinanceAdapter(
                        base_url=exchange_config.base_url,
                        rate_limit_per_minute=exchange_config.rate_limit_per_minute,
                        api_key=exchange_config.api_key,
                        api_secret=exchange_config.api_secret,
                    )
                # Add other exchanges here when implemented

    def run_hourly(self):
        """Run hourly ETL pipeline."""
        logger.info("Starting hourly ETL pipeline")
        start_time = now_utc4()
        
        try:
            # Step 1: Update universe if needed
            logger.info("Step 1: Updating universe")
            universe_df = self.universe_builder.update_universe_if_needed()
            gc.collect()  # Cleanup after universe update
            
            # Step 2: Fetch market data for all symbols
            logger.info("Step 2: Fetching market data")
            market_data_snapshots = []
            btc_price = None
            
            for _, asset in universe_df.iterrows():
                exchange = asset["exchange"]
                adapter = self.adapters.get(exchange)
                
                if not adapter:
                    logger.warning(f"No adapter found for exchange {exchange}")
                    continue
                
                # Try futures symbol first, then spot
                symbol = asset.get("futures_symbol") or asset.get("spot_symbol")
                if not symbol:
                    logger.warning(f"No symbol found for {asset.get('base_asset', 'unknown')}")
                    continue
                
                try:
                    market_data = adapter.get_market_data(symbol)
                    market_data_snapshots.append(market_data)
                    
                    # Get BTC price for normalization
                    if asset.get("base_asset") == "BTC" and btc_price is None:
                        btc_price = market_data.price
                    
                    logger.debug(f"Fetched data for {symbol}")
                except Exception as e:
                    logger.error(f"Error fetching data for {symbol}: {e}")
                    continue
            
            # Step 3: Save market data
            logger.info(f"Step 3: Saving {len(market_data_snapshots)} market data snapshots")
            self.storage.save_market_data(market_data_snapshots)
            del market_data_snapshots  # Free memory
            gc.collect()
            
            # Step 4: Fetch and save candle data
            logger.info("Step 4: Fetching candle data")
            for _, asset in universe_df.iterrows():
                exchange = asset["exchange"]
                adapter = self.adapters.get(exchange)
                
                if not adapter:
                    continue
                
                symbol = asset.get("futures_symbol") or asset.get("spot_symbol")
                if not symbol:
                    continue
                
                try:
                    # Fetch last 24 hours of hourly candles
                    end_time = now_utc4()
                    start_time_candles = end_time - timedelta(hours=24)
                    
                    candles = adapter.fetch_candles(
                        symbol=symbol,
                        interval="1h",
                        limit=24,
                        start_time=start_time_candles,
                        end_time=end_time,
                    )
                    
                    if candles:
                        self.storage.save_candle_data(candles, interval="1h")
                        logger.debug(f"Saved {len(candles)} candles for {symbol}")
                        del candles  # Free memory per iteration
                except Exception as e:
                    logger.error(f"Error fetching candles for {symbol}: {e}")
                    continue
            
            gc.collect()  # Cleanup after candle fetching
            
            # Step 5: Calculate factor scores
            logger.info("Step 5: Calculating factor scores")
            if btc_price is None:
                # Try to get BTC price from storage
                btc_data = self.storage.get_latest_market_data(symbol="BTCUSDT")
                if not btc_data.empty:
                    btc_price = btc_data.iloc[0]["price"]
                else:
                    logger.error("Could not determine BTC price for normalization")
                    btc_price = 1.0  # Fallback
            
            # Use a single timestamp for all factor scores in this batch
            batch_timestamp = now_utc4()
            
            factor_scores = []
            processed_count = 0
            skipped_count = 0
            
            for _, asset in universe_df.iterrows():
                symbol = asset.get("futures_symbol") or asset.get("spot_symbol")
                if not symbol:
                    skipped_count += 1
                    continue
                
                try:
                    # Get latest market data
                    market_data = self.storage.get_latest_market_data(symbol=symbol)
                    if market_data.empty:
                        logger.debug(f"No market data for {symbol}, skipping")
                        skipped_count += 1
                        continue
                    
                    current_price = market_data.iloc[0]["price"]
                    price_btc = self.factor_calculator.normalize_to_btc(current_price, btc_price)
                    
                    # Get candle data for factor calculation
                    candles_df = self.storage.get_candle_data(
                        symbol=symbol,
                        interval="1h",
                        limit=24,
                    )
                    
                    if candles_df.empty:
                        logger.debug(f"No candle data for {symbol}, skipping factor calculation")
                        skipped_count += 1
                        continue
                    
                    # Sort by timestamp ascending for proper factor calculation
                    candles_df = candles_df.sort_values("timestamp")
                    
                    if len(candles_df) < self.config.thresholds.min_data_points:
                        logger.info(f"Insufficient data for {symbol} ({len(candles_df)} candles, need {self.config.thresholds.min_data_points}), skipping factor calculation")
                        skipped_count += 1
                        continue
                    
                    # Calculate factors
                    momentum = self.factor_calculator.calculate_momentum(candles_df)
                    mean_reversion = self.factor_calculator.calculate_mean_reversion(candles_df)
                    volatility = self.factor_calculator.calculate_volatility(candles_df)
                    carry = self.factor_calculator.calculate_carry(
                        funding_rate=market_data.iloc[0].get("funding_rate"),
                        mark_price=market_data.iloc[0].get("mark_price"),
                        index_price=market_data.iloc[0].get("index_price"),
                    )
                    volume = self.factor_calculator.calculate_volume_factors(candles_df)
                    
                    composite_score = self.factor_calculator.calculate_composite_score(
                        momentum, mean_reversion, carry, volume, volatility
                    )
                    
                    # Calculate APR for funding rate
                    funding_rate = market_data.iloc[0].get("funding_rate")
                    funding_rate_apr = funding_rate * 3 * 365 * 100 if funding_rate else 0
                    
                    score_dict = {
                        "timestamp": batch_timestamp,  # Use consistent timestamp for all scores
                        "exchange": asset["exchange"],
                        "symbol": symbol,
                        "price_btc": price_btc,
                        "momentum_1h": momentum.get("momentum_1h"),
                        "momentum_4h": momentum.get("momentum_4h"),
                        "momentum_24h": momentum.get("momentum_24h"),
                        "momentum_percentile": momentum.get("momentum_percentile"),
                        "macd_signal": momentum.get("macd_signal"),
                        "trend_strength": momentum.get("trend_strength"),
                        "mean_reversion_zscore": mean_reversion.get("mean_reversion_zscore"),
                        "rsi": mean_reversion.get("rsi"),
                        "bb_position": mean_reversion.get("bb_position"),
                        "volatility_atr_pct": volatility.get("volatility_atr_pct"),
                        "carry_funding_annualized": carry.get("carry_funding_annualized"),
                        "carry_basis": carry.get("carry_basis"),
                        "volume_momentum_1h": volume.get("volume_momentum_1h"),
                        "volume_momentum_4h": volume.get("volume_momentum_4h"),
                        "volume_momentum_24h": volume.get("volume_momentum_24h"),
                        "volume_anomaly_zscore": volume.get("volume_anomaly_zscore"),
                        "volume_percentile": volume.get("volume_percentile"),
                        "volume_price_divergence": volume.get("volume_price_divergence"),
                        "open_interest": market_data.iloc[0].get("open_interest"),
                        "funding_rate": funding_rate,
                        "funding_rate_apr": funding_rate_apr,
                        "composite_score": composite_score,
                        "is_outlier": False,
                        "outlier_type": None,
                    }
                    
                    factor_scores.append(score_dict)
                    processed_count += 1
                    logger.debug(f"Calculated factors for {symbol}")
                    
                    # Explicitly free memory
                    del candles_df
                    del momentum, mean_reversion, volatility, carry, volume
                    
                except Exception as e:
                    logger.error(f"Error calculating factors for {symbol}: {e}")
                    skipped_count += 1
                    continue
            
            logger.info(f"Factor calculation complete: {processed_count} processed, {skipped_count} skipped out of {len(universe_df)} total assets")
            gc.collect()
            
            # Step 6: Identify outliers
            logger.info("Step 6: Identifying outliers")
            if factor_scores:
                factor_scores = self.factor_calculator.identify_outliers(factor_scores)
                self.storage.save_factor_scores(factor_scores)
                logger.info(f"Calculated and saved {len(factor_scores)} factor scores")

                # Step 6b: Calculate BTC correlation for outliers specifically
                logger.info("Step 6b: Calculating BTC correlation for outliers")
                if not btc_candles_df.empty:
                    try:
                        # Get all outliers
                        outlier_symbols = [
                            score["symbol"] for score in factor_scores
                            if score.get("is_outlier") and score.get("symbol") != "BTCUSDT"
                        ]

                        btc_corr_count = 0
                        for score_dict in factor_scores:
                            symbol = score_dict.get("symbol")
                            # Only calculate for outliers if not already calculated
                            if (symbol in outlier_symbols and
                                (score_dict.get("btc_correlation") is None or
                                 pd.isna(score_dict.get("btc_correlation")))):
                                try:
                                    # Get candles for this outlier
                                    asset_candles = self.storage.get_candle_data(
                                        symbol=symbol,
                                        interval="1h",
                                        limit=24,
                                    )
                                    if not asset_candles.empty:
                                        btc_corr = self.factor_calculator.calculate_btc_correlation(
                                            asset_candles, btc_candles_df
                                        )
                                        # Update the score_dict
                                        score_dict["btc_correlation"] = btc_corr.get("btc_correlation")
                                        score_dict["btc_beta"] = btc_corr.get("btc_beta")
                                        btc_corr_count += 1
                                except Exception as e:
                                    logger.warning(f"Error calculating BTC correlation for outlier {symbol}: {e}")
                                    continue

                        # Re-save factor scores with updated BTC correlation for outliers
                        if btc_corr_count > 0:
                            self.storage.save_factor_scores(factor_scores)
                            logger.info(f"Calculated BTC correlation for {btc_corr_count} outliers")
                    except Exception as e:
                        logger.error(f"Error in BTC correlation for outliers: {e}")

            # Step 7: Generate summary and send Telegram notification (with deduplication)
            logger.info("Step 7: Generating summary and sending notification")
            if factor_scores and self.telegram_bot.is_configured():
                try:
                    # Get outliers and latest scores
                    outliers_df = self.storage.get_outliers(limit=20)
                    latest_scores_df = pd.DataFrame(factor_scores)
                    
                    # Generate summary
                    summary = self.summary_generator.generate_summary(
                        outliers_df=outliers_df,
                        latest_scores_df=latest_scores_df,
                    )
                    
                    # Generate hash for deduplication
                    summary_hash = self.summary_generator.generate_summary_hash(summary)
                    
                    # Check if this summary is a duplicate
                    last_hash = self.storage.get_last_summary_hash()
                    is_duplicate = (last_hash == summary_hash)
                    
                    if is_duplicate:
                        logger.info(f"Summary is identical to last sent summary (hash: {summary_hash[:8]}...), skipping Telegram send")
                        # Still save to database for audit, but mark as not sent
                        self.storage.save_summary(summary, summary_hash, sent=False)
                        self._log_summary_to_file(summary, summary_hash, sent=False)
                    else:
                        logger.info(f"New summary detected (hash: {summary_hash[:8]}...), sending to Telegram")
                        # Send to Telegram
                        success = self.telegram_bot.send_message(summary)
                        
                        if success:
                            logger.info("Summary sent to Telegram successfully")
                            # Save to database with sent=True
                            self.storage.save_summary(summary, summary_hash, sent=True)
                            self._log_summary_to_file(summary, summary_hash, sent=True)
                        else:
                            logger.warning("Failed to send summary to Telegram")
                            # Save to database with sent=False
                            self.storage.save_summary(summary, summary_hash, sent=False)
                            self._log_summary_to_file(summary, summary_hash, sent=False)
                except Exception as e:
                    logger.error(f"Error generating/sending summary: {e}", exc_info=True)
            
            # Step 8: Cleanup old data
            logger.info("Step 8: Cleaning up old data")
            self.storage.cleanup_old_data()
            
            elapsed = (now_utc4() - start_time).total_seconds()
            logger.info(f"Pipeline completed successfully in {elapsed:.2f} seconds")
            
            # Final cleanup
            gc.collect()
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
    
    def _log_summary_to_file(self, summary: str, summary_hash: str, sent: bool):
        """Log summary to a file for audit purposes."""
        try:
            from pathlib import Path
            log_dir = Path(self.config.database.path).parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            summary_log_file = log_dir / "telegram_summaries.log"
            
            timestamp = now_utc4().isoformat()
            status = "SENT" if sent else "SKIPPED (duplicate)"
            
            with open(summary_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Status: {status}\n")
                f.write(f"Hash: {summary_hash}\n")
                f.write(f"{'='*80}\n")
                f.write(summary)
                f.write(f"\n{'='*80}\n\n")
            
            logger.debug(f"Summary logged to {summary_log_file}")
        except Exception as e:
            logger.warning(f"Failed to log summary to file: {e}")
