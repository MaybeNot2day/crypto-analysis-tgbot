"""
Telegram bot integration for sending notifications.
"""

import logging
import requests
from typing import Optional
from src.config import TelegramConfig

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for sending notifications."""

    def __init__(self, config: TelegramConfig):
        """Initialize Telegram bot."""
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}"

    def is_configured(self) -> bool:
        """Check if bot is properly configured."""
        return (
            self.config.enabled
            and self.config.bot_token is not None
            and self.config.chat_id is not None
        )

    def send_message(self, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
        """
        Send a message to the configured chat.
        
        Args:
            text: Message text to send
            parse_mode: Parse mode for formatting (Markdown, HTML, or None for plain text)
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Telegram bot is not configured or disabled")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.config.chat_id,
                "text": text,
            }
            
            # Only add parse_mode if specified (skip if None to use plain text)
            if parse_mode:
                payload["parse_mode"] = parse_mode
            
            response = requests.post(url, json=payload, timeout=10)
            
            # Check for errors in response
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_description = error_data.get("description", "Unknown error")
                logger.error(f"Telegram API error {response.status_code}: {error_description}")
                logger.debug(f"Full response: {response.text}")
                
                # If Markdown parsing fails, try sending as plain text
                if response.status_code == 400 and parse_mode == "Markdown":
                    logger.info("Markdown parsing failed, retrying as plain text...")
                    return self.send_message(text, parse_mode=None)
                
                return False
            
            logger.info("Telegram message sent successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Telegram API error details: {error_data}")
                except:
                    logger.error(f"Telegram API error response: {e.response.text}")
            return False

    def send_formatted_message(self, title: str, content: str) -> bool:
        """
        Send a formatted message with title and content.
        
        Args:
            title: Message title
            content: Message content
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        text = f"*{title}*\n\n{content}"
        return self.send_message(text)

    def test_connection(self) -> bool:
        """Test Telegram bot connection and chat access."""
        if not self.is_configured():
            logger.warning("Telegram bot is not configured")
            return False

        try:
            # Test bot token
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            bot_info = response.json()
            
            if not bot_info.get("ok"):
                logger.error("Telegram bot connection failed")
                return False
                
            logger.info(f"✅ Bot token valid: @{bot_info['result']['username']}")
            
            # Test chat access
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.config.chat_id,
                "text": "🧪 Test message from Crypto Outlier Detection Bot",
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json() if response.content else {}
            
            if response.status_code == 200:
                logger.info(f"✅ Chat ID valid: {self.config.chat_id}")
                return True
            else:
                error_description = response_data.get("description", "Unknown error")
                logger.error(f"❌ Chat ID test failed: {error_description}")
                
                if "chat not found" in error_description.lower():
                    logger.error(
                        "\n⚠️  CHAT ID ISSUE DETECTED:\n"
                        f"Chat ID: {self.config.chat_id}\n"
                        "\nTo fix this:\n"
                        "1. Open Telegram and search for your bot\n"
                        "2. Click 'Start' or send /start to initiate a conversation\n"
                        "3. If using a group, add the bot to the group first\n"
                        "4. Make sure you're using the correct chat_id (get it from @userinfobot or @RawDataBot)\n"
                    )
                elif "group chat was upgraded to a supergroup chat" in error_description.lower():
                    logger.error(
                        "\n⚠️  GROUP UPGRADED TO SUPERGROUP:\n"
                        "The group was upgraded to a supergroup, which has a different chat ID.\n"
                        "\nTo get the new supergroup chat ID:\n"
                        "1. Add @RawDataBot to your supergroup\n"
                        "2. Send any message in the group\n"
                        "3. Look for the 'chat' object in the response\n"
                        "4. The supergroup chat_id will be a large negative number like -1001234567890\n"
                        "5. Update your config with the new chat_id\n"
                        f"\nOld chat_id: {self.config.chat_id}"
                    )
                    # Try to get the new chat ID from the error response
                    if "parameters" in response_data and "migrate_to_chat_id" in response_data["parameters"]:
                        new_chat_id = response_data["parameters"]["migrate_to_chat_id"]
                        logger.info(f"\n✅ Suggested new chat_id: {new_chat_id}")
                        logger.info(f"Update config/config.yaml with: chat_id: \"{new_chat_id}\"")
                
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to test Telegram connection: {e}")
            return False

