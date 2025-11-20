# Quick Update Guide

## Option 1: Upload Changed Files via SCP (Recommended for Quick Updates)

From your **local machine**, upload only the changed files:

```bash
# Replace YOUR_DROPLET_IP with your actual droplet IP
# Replace crypto with your username if different

# Upload the changed files
scp src/notifications/summary.py crypto@YOUR_DROPLET_IP:~/crypto-analysis/src/notifications/
scp src/pipeline/pipeline.py crypto@YOUR_DROPLET_IP:~/crypto-analysis/src/pipeline/
scp src/pipeline/storage.py crypto@YOUR_DROPLET_IP:~/crypto-analysis/src/pipeline/

# Upload the new documentation file (optional)
scp SUMMARY_LOGGING.md crypto@YOUR_DROPLET_IP:~/crypto-analysis/
```

Then **SSH into your server** and verify:

```bash
# Connect to server
ssh crypto@YOUR_DROPLET_IP

# Navigate to project directory
cd ~/crypto-analysis

# Verify files are updated
ls -la src/notifications/summary.py
ls -la src/pipeline/pipeline.py
ls -la src/pipeline/storage.py

# The changes will be picked up automatically on the next hourly run
# Or test immediately with a manual run:
source venv/bin/activate
python3 main.py run_hourly

# Check logs to verify deduplication is working
tail -f logs/pipeline.log
```

## Option 2: Upload Entire Project (If You Prefer)

If you want to upload everything:

```bash
# From your local machine (in the project root)
scp -r . crypto@YOUR_DROPLET_IP:~/crypto-analysis-temp/

# Then SSH in and replace files
ssh crypto@YOUR_DROPLET_IP
cd ~/crypto-analysis
cp -r ~/crypto-analysis-temp/* ./
```

## Option 3: Using Git (If You Have a Repo)

If you've set up a git repository:

```bash
# SSH into server
ssh crypto@YOUR_DROPLET_IP

# Navigate to project
cd ~/crypto-analysis

# Pull latest changes
git pull

# Restart timer (optional - changes will be picked up automatically)
sudo systemctl restart crypto-pipeline.timer
```

## Verify Deployment

After uploading, verify the changes are working:

```bash
# SSH into server
ssh crypto@YOUR_DROPLET_IP
cd ~/crypto-analysis

# Activate virtual environment
source venv/bin/activate

# Test that the code loads correctly
python3 -c "from src.notifications.summary import MarketSummaryGenerator; print('✅ Import successful')"

# Check if database schema needs updating (will auto-create summary table)
python3 -c "from src.pipeline.storage import DataStorage; from src.config import load_config; s = DataStorage(load_config()); print('✅ Storage initialized')"

# Trigger a test run
python3 main.py run_hourly

# Watch logs for deduplication messages
tail -f logs/pipeline.log | grep -i "summary\|duplicate\|hash"
```

## Important Notes

1. **No restart needed**: The systemd timer will automatically use the new code on the next hourly run
2. **Database migration**: The new `telegram_summaries` table will be created automatically when the code runs
3. **Existing summaries**: Old summaries won't be skipped (no previous hash), but new duplicates will be detected
4. **Test first**: You can test with a manual run before waiting for the next hourly cycle

## Troubleshooting

If you see import errors:
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Verify Python path
which python3  # Should show ~/crypto-analysis/venv/bin/python3
```

If database errors occur:
```bash
# The schema will auto-migrate, but if you see errors:
cd ~/crypto-analysis
source venv/bin/activate
python3 -c "from src.pipeline.storage import DataStorage; from src.config import load_config; s = DataStorage(load_config()); print('OK')"
```

