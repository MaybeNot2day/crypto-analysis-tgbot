"""
CLI command to test Telegram bot configuration.
"""

import logging
from src.config import load_config
from src.notifications import TelegramBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_telegram():
    """Test Telegram bot configuration."""
    config = load_config()
    bot = TelegramBot(config.telegram)
    
    print("\n" + "="*60)
    print("Testing Telegram Bot Configuration")
    print("="*60 + "\n")
    
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


if __name__ == "__main__":
    test_telegram()

