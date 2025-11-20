# Telegram Bot Setup Guide

## Overview
The pipeline now includes Telegram notifications that send market summaries after each analysis run.

## Setup Instructions

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

**Option A: Using @userinfobot**
1. Search for `@userinfobot` in Telegram
2. Start a conversation with it
3. It will reply with your chat ID (a number like `123456789`)

**Option B: Using @RawDataBot**
1. Search for `@RawDataBot` in Telegram
2. Start a conversation with it
3. Send any message to it
4. Look for the `"chat":{"id":123456789}` value in the response

### 3. Configure the Bot

**Option A: Using Environment Variables (Recommended)**
Add to your `.env` file:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**Option B: Using config.yaml**
Edit `config/config.yaml`:
```yaml
telegram:
  enabled: true
  bot_token: "your_bot_token_here"
  chat_id: "your_chat_id_here"
```

### 4. Enable Notifications

In `config/config.yaml`, set:
```yaml
telegram:
  enabled: true
```

### 5. Test the Setup

Run the pipeline:
```bash
python3 main.py run_hourly
```

If configured correctly, you should receive a Telegram message with the market summary after the analysis completes.

## Summary Content

The summary includes:
- **Market State Overview**: Overall sentiment, bullish/bearish percentages, average momentum
- **Key Outliers**: Top 5 bullish and bearish outliers with their key metrics
- **Top Opportunities**: Assets showing strong momentum, volume anomalies, or mean reversion signals

## Troubleshooting

- **Bot not responding**: Check that you've enabled the bot in config.yaml (`enabled: true`)
- **No messages received**: Verify bot token and chat ID are correct
- **Connection errors**: Ensure your network can reach `api.telegram.org`

