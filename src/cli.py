"""
CLI entry points for the Crypto Outlier Detection Dashboard.
"""

import logging
import sys
import argparse
from src.config import load_config
from src.universe.builder import UniverseBuilder
from src.pipeline.pipeline import Pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def update_universe():
    """Update the universe of top assets."""
    logger.info("Updating universe")
    config = load_config()
    builder = UniverseBuilder(config)
    df = builder.build_universe()
    logger.info(f"Universe updated: {len(df)} assets")


def run_hourly():
    """Run the hourly ETL pipeline."""
    logger.info("Running hourly ETL pipeline")
    config = load_config()
    pipeline = Pipeline(config)
    pipeline.run_hourly()
    logger.info("Hourly pipeline completed")


def serve_dashboard():
    """Start the dashboard server."""
    logger.info("Starting dashboard server")
    import subprocess
    import os
    import sys
    
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
    if os.path.exists(dashboard_path):
        logger.info("Starting Streamlit dashboard...")
        logger.info("Note: Make sure the API server is running on port 8000")
        logger.info("To start API server: python main.py serve_api")
        logger.info("Or in another terminal: cd src/api && python app.py")
        subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
    else:
        logger.error(f"Dashboard not found at {dashboard_path}")


def serve_api():
    """Start the API server."""
    logger.info("Starting API server on http://localhost:8000")
    import uvicorn
    from src.api.app import app
    
    uvicorn.run(app, host="0.0.0.0", port=8000)


def serve_all():
    """Start both API server and dashboard."""
    import subprocess
    import os
    import sys
    import threading
    import time
    
    logger.info("Starting API server and dashboard...")
    
    # Start API server in a separate thread
    def start_api():
        import uvicorn
        from src.api.app import app
        uvicorn.run(app, host="0.0.0.0", port=8000)
    
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    
    # Wait a bit for API to start
    logger.info("Waiting for API server to start...")
    time.sleep(3)
    
    # Start dashboard
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
    if os.path.exists(dashboard_path):
        logger.info("Starting Streamlit dashboard...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
    else:
        logger.error(f"Dashboard not found at {dashboard_path}")


def test_telegram():
    """Test Telegram bot configuration."""
    from src.notifications import TelegramBot
    
    print("\n" + "="*60)
    print("Testing Telegram Bot Configuration")
    print("="*60 + "\n")
    
    config = load_config()
    bot = TelegramBot(config.telegram)
    
    if not bot.is_configured():
        print("❌ Telegram bot is not configured")
        print("\nPlease configure in config/config.yaml:")
        print("  telegram:")
        print("    enabled: true")
        print("    bot_token: 'your_token'")
        print("    chat_id: 'your_chat_id'")
        print("\nOr set environment variables:")
        print("  TELEGRAM_BOT_TOKEN=your_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        return False
    
    print(f"Bot Token: {config.telegram.bot_token[:20]}...")
    print(f"Chat ID: {config.telegram.chat_id}\n")
    
    success = bot.test_connection()
    
    if success:
        print("\n✅ All tests passed! Telegram bot is ready to use.")
    else:
        print("\n❌ Tests failed. Please check the errors above.")
    
    return success


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Crypto Outlier Detection Dashboard")
    parser.add_argument(
        "command",
        choices=["update_universe", "run_hourly", "serve_dashboard", "serve_api", "serve_all", "test_telegram"],
        help="Command to execute",
    )
    
    args = parser.parse_args()
    
    if args.command == "update_universe":
        update_universe()
    elif args.command == "run_hourly":
        run_hourly()
    elif args.command == "serve_dashboard":
        serve_dashboard()
    elif args.command == "serve_api":
        serve_api()
    elif args.command == "serve_all":
        serve_all()
    elif args.command == "test_telegram":
        test_telegram()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

