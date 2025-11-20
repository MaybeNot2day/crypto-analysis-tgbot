# Quick Deployment Checklist

**Status**: ✅ Production Ready - Automated hourly pipeline with systemd timers

This is a quick reference checklist for deploying to DigitalOcean. For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Pre-Deployment (Local Machine)

1. ✅ Test everything locally:
   ```bash
   python3 main.py test_telegram
   python3 main.py run_hourly
   ```

2. ✅ Ensure `.env` file has Telegram credentials (or config.yaml)

3. ✅ Create a git repository (optional but recommended):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   # Push to GitHub/GitLab
   ```

## On DigitalOcean Droplet

### Initial Setup (One-time)

```bash
# 1. Connect to your droplet
ssh root@YOUR_DROPLET_IP

# 2. Create user
adduser crypto --disabled-password --gecos ""
usermod -aG sudo crypto
su - crypto

# 3. Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git

# 4. Clone or upload your project
# Option A: Git clone
git clone YOUR_REPO_URL crypto-analysis
cd crypto-analysis

# Option B: Upload via SCP (from local machine)
# scp -r /path/to/Analysis crypto@DROPLET_IP:~/
# ssh crypto@DROPLET_IP
# mv Analysis crypto-analysis
# cd crypto-analysis

# 5. Run deployment script
chmod +x deploy.sh
./deploy.sh

# 6. Configure Telegram
nano .env
# Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 7. Test configuration
source venv/bin/activate
python3 main.py test_telegram

# 8. Verify timer is running
sudo systemctl status crypto-pipeline.timer
```

## Verify It's Working

```bash
# Check timer status
sudo systemctl status crypto-pipeline.timer

# Check when next run will be
sudo systemctl list-timers crypto-pipeline.timer

# View logs
tail -f logs/pipeline.log

# Manually trigger a test run
sudo systemctl start crypto-pipeline.service

# Check logs after test run
tail -n 50 logs/pipeline.log
```

## Common Issues

**Issue**: Timer not running
```bash
sudo systemctl status crypto-pipeline.timer
sudo journalctl -u crypto-pipeline.timer -n 50
```

**Issue**: Permission denied
```bash
# Make sure you're running as 'crypto' user, not root
whoami  # Should show 'crypto'
```

**Issue**: Python not found
```bash
# Make sure virtual environment is activated
source venv/bin/activate
which python3  # Should show /home/crypto/crypto-analysis/venv/bin/python3
```

**Issue**: Telegram not sending
```bash
# Test Telegram configuration
python3 main.py test_telegram

# Check environment variables
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

## Monitoring Commands

```bash
# View recent pipeline runs
grep "Pipeline completed" logs/pipeline.log | tail -10

# Check system resources
htop
free -h
df -h

# Check running processes
ps aux | grep python

# View service logs
sudo journalctl -u crypto-pipeline.service -f
```

## Update Your Code

```bash
# If using git
cd ~/crypto-analysis
git pull
source venv/bin/activate
pip install -r requirements.txt  # If dependencies changed

# Restart timer (not needed, but good practice)
sudo systemctl restart crypto-pipeline.timer
```

## Stop/Start Automation

```bash
# Stop automation
sudo systemctl stop crypto-pipeline.timer

# Start automation
sudo systemctl start crypto-pipeline.timer

# Disable on boot
sudo systemctl disable crypto-pipeline.timer

# Enable on boot
sudo systemctl enable crypto-pipeline.timer
```

