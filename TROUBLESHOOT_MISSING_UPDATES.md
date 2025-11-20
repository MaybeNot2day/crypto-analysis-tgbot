# Troubleshooting Missing Updates

## Check What's Happening

SSH into your server and run these commands:

```bash
ssh root@104.248.45.192
su - crypto
cd ~/crypto-analysis

# 1. Check recent pipeline runs
tail -n 100 logs/pipeline.log | grep -A 5 -B 5 "Step 7\|summary\|duplicate"

# 2. Check if pipeline is actually running
tail -n 50 logs/pipeline.log

# 3. Check summary history (if database is accessible)
source venv/bin/activate
python3 -c "
from src.pipeline.storage import DataStorage
from src.config import load_config
s = DataStorage(load_config())
history = s.get_summary_history(10)
print(history)
"

# 4. Check summary log file
tail -n 50 data/logs/telegram_summaries.log 2>/dev/null || echo "Summary log file not found yet"

# 5. Check for errors
grep -i "error\|exception\|failed" logs/pipeline.log | tail -20
```

## Possible Issues

### Issue 1: Deduplication Too Aggressive
The hash might be matching summaries that are actually different. Check:
- Are the summaries actually identical?
- Is the hash generation working correctly?

### Issue 2: Pipeline Not Running
Check if the pipeline service is actually executing:
```bash
sudo systemctl status crypto-pipeline.service
sudo journalctl -u crypto-pipeline.service -n 50
```

### Issue 3: Database Issues
Check if database is accessible:
```bash
source venv/bin/activate
python3 -c "
from src.pipeline.storage import DataStorage
from src.config import load_config
try:
    s = DataStorage(load_config())
    print('✅ Database OK')
except Exception as e:
    print(f'❌ Database Error: {e}')
"
```

### Issue 4: Telegram Sending Failed
Even if not duplicate, Telegram might be failing:
```bash
tail -n 100 logs/pipeline.log | grep -i "telegram\|send"
```

## Quick Fix: Test Manual Run

```bash
# Trigger a manual run to see what happens
source venv/bin/activate
python3 main.py run_hourly

# Watch the output for:
# - "Summary is identical to last sent summary" (deduplication working)
# - "New summary detected" (should send)
# - Any errors
```

## If Deduplication is Too Aggressive

We might need to adjust the hash sensitivity. The current implementation rounds:
- Percentages to nearest 5%
- Momentum to nearest 100%

This might be too aggressive. We can make it less sensitive if needed.

