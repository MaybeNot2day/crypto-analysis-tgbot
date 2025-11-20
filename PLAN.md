Plan: Crypto Outlier Detection Dashboard (Top 100 Market Cap)
============================================================

Objective:
    Build an hourly pipeline that tracks the top 100 crypto assets by market cap
    across Binance, Bybit, and Hyperliquid, computes relative-performance and
    factor scores versus BTC, incorporates volume metrics for outlier detection,
    and publishes an internal dashboard to spotlight outliers.

**Status: Phase 1-5 Complete (Production Ready)**

---

## Phase 1 — Foundations ✅ COMPLETE

    1. Configuration & Secrets ✅
        - ✅ Define config schema (YAML) for API keys, exchange endpoints,
          universe settings, factor weights, thresholds, and storage paths.
        - ✅ Set up secrets management (local .env for dev, Vault/SSM later).
        - ✅ Telegram configuration added for notifications.
    2. Universe Builder (Daily) ✅
        - ✅ Pull top 100 assets by 24h volume directly from Binance.
        - ✅ Map tickers to specific tradable instruments (spot and futures).
        - ✅ Persist resolved list in storage (parquet) with metadata:
          symbol, exchange, contract type, quote asset, funding cadence, volume metrics.
        - ✅ Track and store volume information: 24h volume, volume trend (1h, 4h, 24h),
          volume percentile vs historical, volume-to-market-cap ratio.
        - ✅ Uses Binance-native data only (no external dependencies).
        - ✅ UTC+4 timezone support for all timestamps.

## Phase 2 — Exchange Data Adapters 🟡 PARTIAL

    3. Shared Adapter Interface ✅
        - ✅ Create base adapter with rate limiting, retries, and schema helpers.
        - ✅ Methods: fetch_candles, fetch_mark_price, fetch_open_interest,
          fetch_funding, fetch_index_price.
    4. Exchange Implementations 🟡
        - ✅ Binance (UM futures + spot) via REST; handle weight-based limits.
          - ✅ Spot vs futures detection
          - ✅ Graceful handling of spot-only symbols
          - ✅ Futures symbol caching
        - ⏳ Bybit Unified v5; manage auth for open interest/funding endpoints.
        - ⏳ Hyperliquid REST/WebSocket; normalize response structure.
        - ⏳ Add integration tests with recorded fixtures for each adapter.

## Phase 3 — Data Pipeline (Hourly) ✅ COMPLETE

    5. Orchestration ✅
        - ✅ Hourly ETL pipeline with CLI command (`run_hourly`).
        - ✅ Steps: load universe → parallel data pulls → validation → factor calc.
        - ✅ UTC+4 timezone for all timestamps.
        - ⏳ Cron/Airflow scheduling (can be added via system cron).
    6. Raw Data Storage ✅
        - ✅ Append raw snapshots to time-series store (DuckDB).
        - ✅ Schema per snapshot: timestamp, exchange, symbol, price, volume (24h, 1h, 4h),
          volume_percentile, volume_momentum, open interest, funding rate, mark/index prices.
        - ✅ Store volume metrics for trend analysis and outlier detection.
        - ✅ Schema migrations for adding new columns.
        - ✅ Data retention and cleanup.
    7. Factor Computation ✅
        - ✅ Normalize all prices in BTC terms.
        - ✅ Momentum: rolling returns (1h, 4h, 24h) + percentile ranks.
        - ✅ Mean Reversion: z-score of price vs moving average, RSI divergence.
        - ✅ Carry: annualized funding, basis (mark-index)/index.
        - ✅ Volume Factors:
          * ✅ Volume momentum: 1h/4h/24h volume changes, volume acceleration.
          * ✅ Volume anomaly detection: z-score of current volume vs historical average.
          * ✅ Volume-price divergence: correlation between volume spikes and price movements.
          * ✅ Volume percentile: rank asset volume vs its historical distribution.
        - ✅ Compute composite score (configurable weights) incorporating volume factors.
        - ✅ Flag outliers using combined signals: z-score thresholds, top/bottom N,
          volume anomalies, and volume-price divergence patterns.
        - ✅ Save engineered metrics to dedicated table with audit columns.
    8. Data Quality Safeguards ✅
        - ✅ Validate freshness, missing fields, extreme jumps vs historical bands.
        - ✅ Emit alerts via Telegram notifications on completion.
        - ⏳ Slack/webhook alerts on failure (can be added).

## Phase 4 — Dashboard ✅ COMPLETE

    9. Backend API ✅
        - ✅ Lightweight FastAPI service with direct DB access encapsulating queries.
        - ✅ Endpoints deliver latest metrics, trend history (last 24h), and
          metadata for filters.
        - ✅ Endpoints: `/api/latest`, `/api/factors`, `/api/outliers`, `/api/trends`, `/api/universe`, `/api/status`
        - ✅ JSON serialization with NaN/inf handling.
   10. Frontend (Internal Dashboard) ✅
        - ✅ Streamlit dashboard for rapid iteration.
        - ✅ Components: scatter plots (Price Change vs factor scores), ranked bar charts,
          table of flagged outliers with metrics.
        - ✅ Volume visualization:
          * ✅ Volume trend charts (top 20 volume anomalies, momentum)
          * ✅ Volume-price divergence scatter plots
          * ✅ Volume anomaly z-scores visualization
        - ✅ Filters: exchange, symbol, time window.
        - ✅ Display last refresh timestamp (UTC+4), BTC benchmark stats, and volume metrics summary.
        - ✅ Real-time updates via API integration.

## Phase 5 — Deployment & Ops ✅ COMPLETE

   11. Packaging ✅
        - ✅ Structure project with Python package layout.
        - ✅ Define `main.py` entry points:
          `update_universe`, `run_hourly`, `serve_dashboard`, `serve_api`, `serve_all`, `test_telegram`.
        - ✅ Containerize for consistent deployment (Dockerfile exists).
        - ✅ Requirements.txt with all dependencies.
   12. Scheduling & Hosting ✅ COMPLETE
        - ✅ Deploy ETL to server using systemd timer (automated hourly runs).
        - ✅ Systemd service and timer configured for 24/7 operation.
        - ✅ Log rotation and error handling configured.
        - ✅ Cloud deployment on DigitalOcean with automated setup script.
        - ✅ Pipeline runs independently of local machine.
        - ⏳ Host dashboard behind auth (reverse proxy, VPN, or SSO).
        - ✅ Local development setup complete.
   13. Monitoring & Iteration ✅
        - ✅ Pipeline logging with timing metrics.
        - ✅ Telegram notifications for pipeline completion and market summaries.
        - ✅ Error handling and graceful degradation.
        - ⏳ Backfill scripts for historical analysis and model tuning.
        - ⏳ Metrics on pipeline latency, API failure rates, dashboard usage.
        - ⏳ Roadmap for expanding beyond top 100, incorporating derivatives markets,
          on-chain data, and advanced volume analytics (order flow, market depth).

---

## Additional Features Implemented ✅

- **Telegram Integration**: Automated market summaries with outlier highlights
- **Timezone Support**: All timestamps in UTC+4
- **Schema Migrations**: Automatic database schema updates
- **Error Handling**: Comprehensive error handling with retries
- **Volume Analytics**: Complete volume factor implementation
- **CLI Tools**: Test commands for configuration validation
- **Cloud Deployment**: Automated deployment to DigitalOcean with systemd timers
- **24/7 Operation**: Pipeline runs independently on cloud server
- **Log Management**: Automatic log rotation and retention

## Next Steps (Optional Enhancements)

1. **Additional Exchanges**: Implement Bybit and Hyperliquid adapters
2. **Advanced Analytics**: Order flow, market depth analysis
3. **On-chain Data**: Integrate blockchain data sources
4. **Dashboard Authentication**: Add auth to dashboard (reverse proxy, VPN, or SSO)
5. **Enhanced Monitoring**: Advanced metrics dashboard, alerting, and health checks
6. **Backfill Scripts**: Historical data analysis and model tuning tools

