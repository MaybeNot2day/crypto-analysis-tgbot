# Summary Logging & Deduplication

## Overview

The system now logs all Telegram summaries and prevents duplicate messages from being sent.

## Features Added

### 1. Summary Storage in Database
- All summaries are stored in `telegram_summaries` table in DuckDB
- Includes: timestamp, hash, full text, and sent status
- Retained for 30 days for audit purposes

### 2. Deduplication Logic
- Each summary generates an MD5 hash (excluding timestamp)
- Before sending, compares hash with last sent summary
- If identical → **skips sending** (logs but doesn't send)
- If different → **sends normally**

### 3. File Logging
- All summaries (sent and skipped) are logged to: `data/logs/telegram_summaries.log`
- Includes timestamp, status (SENT/SKIPPED), hash, and full text
- Easy to review what was sent and when

### 4. Database Methods
- `get_last_summary_hash()` - Get hash of last sent summary
- `save_summary()` - Save summary to database
- `get_summary_history()` - View recent summary history

## How It Works

1. **Summary Generation**: Creates summary text from market data
2. **Hash Calculation**: Generates MD5 hash (excluding timestamp)
3. **Duplicate Check**: Compares hash with last sent summary
4. **Action**:
   - **Duplicate**: Logs to file/database with `sent=False`, skips Telegram
   - **New**: Sends to Telegram, logs to file/database with `sent=True`

## Log Files

- **Pipeline Log**: `logs/pipeline.log` - General pipeline execution logs
- **Summary Log**: `data/logs/telegram_summaries.log` - All summaries (sent and skipped)

## Viewing Summary History

To view recent summaries in the database:

```python
from src.pipeline.storage import DataStorage
from src.config import load_config

storage = DataStorage(load_config())
history = storage.get_summary_history(limit=10)
print(history)
```

## About the SSH Timeout

The terminal output you saw:
```
Read from remote host 104.248.45.192: Operation timed out
Connection to 104.248.45.192 closed.
client_loop: send disconnect: Broken pipe
```

This is **normal** - it's just your SSH connection timing out when you're inactive. The pipeline continues running on the server independently via systemd timer. This is not an error with the pipeline itself.

## Troubleshooting

### Check if summaries are being skipped
```bash
# On server
tail -f logs/pipeline.log | grep -i "summary\|duplicate"
```

### View summary log file
```bash
# On server
tail -f data/logs/telegram_summaries.log
```

### Check summary history in database
```python
python3 -c "
from src.pipeline.storage import DataStorage
from src.config import load_config
storage = DataStorage(load_config())
print(storage.get_summary_history(10))
"
```

