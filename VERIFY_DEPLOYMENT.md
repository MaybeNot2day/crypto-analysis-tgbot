# Deployment Verification Steps

## Step 1: SSH into Server and Verify Files

```bash
ssh root@104.248.45.192
su - crypto
cd ~/crypto-analysis

# Verify files are updated (check modification times)
ls -lh src/notifications/summary.py
ls -lh src/pipeline/pipeline.py
ls -lh src/pipeline/storage.py
```

## Step 2: Test Code Loads Correctly

```bash
# Still on server as crypto user
source venv/bin/activate

# Test imports
python3 -c "from src.notifications.summary import MarketSummaryGenerator; print('✅ summary.py loads successfully')"
python3 -c "from src.pipeline.pipeline import Pipeline; print('✅ pipeline.py loads successfully')"
python3 -c "from src.pipeline.storage import DataStorage; print('✅ storage.py loads successfully')"
```

## Step 3: Verify Database Schema Update

The new `telegram_summaries` table will be created automatically:

```bash
# Test that storage initializes correctly
python3 -c "from src.pipeline.storage import DataStorage; from src.config import load_config; s = DataStorage(load_config()); print('✅ Database schema updated')"
```

## Step 4: Test Deduplication (Optional)

You can trigger a manual run to test:

```bash
# Trigger manual pipeline run
python3 main.py run_hourly

# Watch logs for deduplication messages
tail -f logs/pipeline.log | grep -i "summary\|duplicate\|hash"
```

You should see messages like:
- "New summary detected (hash: ...), sending to Telegram"
- OR "Summary is identical to last sent summary (hash: ...), skipping Telegram send"

## Step 5: Check Summary Log File

```bash
# Check if summary log file exists
ls -lh data/logs/telegram_summaries.log

# View recent summaries
tail -20 data/logs/telegram_summaries.log
```

## What Happens Next

1. **Next Hourly Run**: The systemd timer will automatically use the new code
2. **First Run**: Will send a summary (no previous hash to compare)
3. **Subsequent Runs**: Will compare hashes and skip duplicates
4. **Logs**: All summaries (sent and skipped) logged to `data/logs/telegram_summaries.log`

## Monitor for Success

```bash
# Watch pipeline logs
tail -f logs/pipeline.log

# Check summary history in database (after first run)
python3 -c "from src.pipeline.storage import DataStorage; from src.config import load_config; s = DataStorage(load_config()); print(s.get_summary_history(5))"
```

## Done! ✅

Your changes are deployed. The deduplication will start working on the next hourly run!

