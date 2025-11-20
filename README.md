# Crypto Outlier Detection Dashboard

A comprehensive system for tracking top 100 crypto assets by market cap, computing factor scores, identifying outliers, and delivering automated Telegram notifications.

## Features

- **Universe Management**: Daily updates of top 100 assets by volume from Binance
- **Exchange Integration**: Binance futures and spot market data (100% Binance-native)
- **Factor Analysis**: 
  - Momentum factors (1h, 4h, 24h returns, percentile ranks)
  - Mean Reversion (z-score, RSI)
  - Carry (annualized funding, basis)
  - **Volume Factors** (volume momentum, anomaly detection, price divergence, percentile)
- **Outlier Detection**: Automated identification of outliers based on composite scores
- **Dashboard**: Real-time Streamlit dashboard with visualizations and volume analysis
- **API**: FastAPI backend for programmatic access
- **Telegram Notifications**: Automated market summaries and outlier alerts
- **Timezone Support**: All timestamps in UTC+4

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

4. Configure `config/config.yaml` as needed

## Usage

### Update Universe
```bash
python main.py update_universe
```

### Run Hourly Pipeline
```bash
python main.py run_hourly
```
The pipeline will automatically:
- Fetch market data for all assets
- Calculate factor scores
- Identify outliers
- Generate and send Telegram summary (if configured)

### Start Dashboard

Option 1: Start both API and dashboard together:
```bash
python main.py serve_all
```

Option 2: Start them separately (in two terminals):
```bash
# Terminal 1: Start API server
python main.py serve_api

# Terminal 2: Start dashboard
python main.py serve_dashboard
```

### Test Telegram Configuration
```bash
python main.py test_telegram
```
This will verify your bot token and chat ID are correctly configured.

### CLI Commands
- `update_universe` - Update the list of top 100 assets
- `run_hourly` - Run the hourly ETL pipeline
- `serve_dashboard` - Start Streamlit dashboard only
- `serve_api` - Start FastAPI backend only
- `serve_all` - Start both API and dashboard concurrently
- `test_telegram` - Test Telegram bot configuration

## Configuration

Edit `config/config.yaml` to customize:
- Exchange settings
- Factor weights (momentum, mean_reversion, carry, volume)
- Outlier thresholds
- Database settings
- Telegram notifications (bot token, chat ID)

### Telegram Setup

See [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for detailed instructions on setting up Telegram notifications.

Quick setup:
1. Create a bot with @BotFather
2. Get your chat ID from @userinfobot
3. Add to `config/config.yaml`:
```yaml
telegram:
  enabled: true
  bot_token: "your_bot_token"
  chat_id: "your_chat_id"
```

Or set environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## Project Structure

```
Analysis/
├── src/
│   ├── adapters/        # Exchange adapters (Binance implemented)
│   ├── api/            # FastAPI backend
│   ├── dashboard/      # Streamlit frontend
│   ├── factors/        # Factor calculation (momentum, mean reversion, carry, volume)
│   ├── notifications/  # Telegram bot and summary generator
│   ├── pipeline/       # ETL pipeline orchestrator
│   ├── universe/       # Universe builder (top 100 assets)
│   └── utils/          # Utility functions (timezone handling)
├── config/             # Configuration files (config.yaml)
├── data/               # Data storage (DuckDB database, parquet files)
├── main.py             # CLI entry point
├── README.md           # This file
├── PLAN.md             # Project plan and roadmap
├── METRICS.md          # Detailed metrics explanation
└── TELEGRAM_SETUP.md  # Telegram bot setup guide
```

## Deployment

### Cloud Deployment (DigitalOcean) ✅ **PRODUCTION READY**

For 24/7 automated operation, deploy to DigitalOcean:

1. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup instructions
2. See [DEPLOYMENT_QUICKSTART.md](DEPLOYMENT_QUICKSTART.md) for quick checklist
3. Use `deploy.sh` script for automated setup

**Once deployed, the system will automatically:**
- ✅ Run the pipeline every hour via systemd timer
- ✅ Send Telegram summaries after each run
- ✅ Continue running 24/7 even when your PC is off
- ✅ Auto-start on server reboot
- ✅ Rotate logs automatically (7-day retention)

**Deployment Status:**
- ✅ Systemd service configured (`crypto-pipeline.service`)
- ✅ Systemd timer configured (`crypto-pipeline.timer`) - runs hourly
- ✅ Log rotation configured
- ✅ Virtual environment isolation
- ✅ Error handling and retries

**Cost**: ~$6-12/month for a DigitalOcean droplet

**Verification Commands** (on server):
```bash
# Check timer status
sudo systemctl status crypto-pipeline.timer

# View recent logs
tail -f ~/crypto-analysis/logs/pipeline.log

# Check next run time
sudo systemctl list-timers crypto-pipeline.timer
```

## Docker

Build and run with Docker:

```bash
docker build -t crypto-dashboard .
docker run -p 8000:8000 -p 8501:8501 crypto-dashboard
```

## Data & Metrics

All metrics are calculated relative to BTC and include:
- **Momentum**: 1h, 4h, 24h returns and percentile ranks
- **Mean Reversion**: Z-score vs moving average, RSI (14-period)
- **Carry**: Annualized funding rate, basis (mark-index)/index
- **Volume**: Momentum (1h/4h/24h), anomaly z-score, percentile, price divergence

See [METRICS.md](METRICS.md) for detailed explanations of all metrics.

## Current Status

✅ **Completed & Production-Ready:**
- Universe builder (top 100 assets from Binance)
- Binance adapter (futures + spot)
- Factor calculation (momentum, mean reversion, carry, volume)
- Outlier detection with composite scoring
- DuckDB storage with schema migrations
- FastAPI backend
- Streamlit dashboard with volume visualizations
- Telegram notifications with market summaries
- UTC+4 timezone support
- CLI interface with multiple commands
- **Cloud deployment with automated hourly runs (DigitalOcean + systemd)**
- **24/7 operation independent of local machine**

🚧 **Future Enhancements:**
- Additional exchanges (Bybit, Hyperliquid)
- Advanced volume analytics (order flow, market depth)
- On-chain data integration
- Dashboard authentication
- Enhanced monitoring and alerting

## License

MIT

