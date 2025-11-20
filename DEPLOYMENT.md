# DigitalOcean Deployment Guide

**Status**: ✅ Production Ready - Automated hourly pipeline with systemd timers

This guide covers deploying the Crypto Outlier Detection Dashboard to DigitalOcean for 24/7 automated operation.

## Quick Summary

Once deployed, the system will:
- ✅ Run the pipeline every hour automatically via systemd timer
- ✅ Send Telegram summaries after each run
- ✅ Continue running 24/7 even when your PC is off
- ✅ Auto-start on server reboot
- ✅ Rotate logs automatically (7-day retention)

**Estimated Setup Time**: 15-20 minutes  
**Monthly Cost**: ~$6-12 for DigitalOcean droplet

---

## Prerequisites

1. **DigitalOcean Account**: Sign up at [digitalocean.com](https://www.digitalocean.com)
2. **Droplet Created**: Ubuntu 22.04 LTS (minimum 1GB RAM, 1 vCPU)
3. **SSH Access**: Ability to SSH into your droplet
4. **Telegram Bot**: Bot token and chat ID configured (see [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md))

---

## Step-by-Step Deployment

### Step 1: Create DigitalOcean Droplet

1. Log into DigitalOcean dashboard
2. Create a new droplet:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic ($6/month minimum)
   - **Region**: Choose closest to you
   - **Authentication**: SSH keys (recommended) or root password
3. Note your droplet's IP address

### Step 2: Initial Server Setup

Connect to your droplet and set up a non-root user:

```bash
# SSH into droplet (replace with your IP)
ssh root@YOUR_DROPLET_IP

# Create user for running the pipeline
adduser crypto --disabled-password --gecos ""
usermod -aG sudo crypto

# Enable passwordless sudo for crypto user
echo "crypto ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/crypto

# Switch to crypto user
su - crypto
```

### Step 3: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git
```

### Step 4: Upload Project Files

**Option A: Using Git (Recommended)**
```bash
# Clone your repository
git clone YOUR_REPO_URL crypto-analysis
cd crypto-analysis
```

**Option B: Using SCP (from your local machine)**
```bash
# From your local machine
scp -r /path/to/Analysis crypto@YOUR_DROPLET_IP:~/
ssh crypto@YOUR_DROPLET_IP
mv Analysis crypto-analysis
cd crypto-analysis
```

### Step 5: Run Automated Deployment Script

The `deploy.sh` script automates the entire setup:

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment script
./deploy.sh
```

This script will:
1. Create Python virtual environment
2. Install all dependencies
3. Set up systemd service
4. Configure systemd timer (hourly runs)
5. Set up log rotation
6. Enable and start the timer

### Step 6: Configure Telegram

```bash
# Create .env file
nano .env
```

Add your Telegram credentials:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Or edit `config/config.yaml`:
```yaml
telegram:
  enabled: true
  bot_token: "your_bot_token"
  chat_id: "your_chat_id"
```

### Step 7: Test Configuration

```bash
# Activate virtual environment
source venv/bin/activate

# Test Telegram connection
python3 main.py test_telegram
```

You should receive a test message in your Telegram chat.

### Step 8: Verify Timer is Running

```bash
# Check timer status
sudo systemctl status crypto-pipeline.timer

# Check when next run will be
sudo systemctl list-timers crypto-pipeline.timer

# View logs
tail -f logs/pipeline.log
```

---

## Verification & Monitoring

### Check Timer Status
```bash
sudo systemctl status crypto-pipeline.timer
```

Expected output:
- **Active**: `active (waiting)`
- **Loaded**: `loaded`
- **Next run**: Shows next scheduled time

### View Recent Logs
```bash
# Follow logs in real-time
tail -f ~/crypto-analysis/logs/pipeline.log

# View last 50 lines
tail -n 50 ~/crypto-analysis/logs/pipeline.log

# Search for completed runs
grep "Pipeline completed" ~/crypto-analysis/logs/pipeline.log | tail -10
```

### Manual Pipeline Run
```bash
# Trigger a manual run (for testing)
sudo systemctl start crypto-pipeline.service

# Check logs after run
tail -n 50 ~/crypto-analysis/logs/pipeline.log
```

---

## Systemd Service Details

### Service File
Located at: `/etc/systemd/system/crypto-pipeline.service`

**Runs**: `python3 main.py run_hourly`  
**User**: `crypto`  
**Working Directory**: `~/crypto-analysis`  
**Logs**: `~/crypto-analysis/logs/pipeline.log`

### Timer File
Located at: `/etc/systemd/system/crypto-pipeline.timer`

**Schedule**: 
- First run: 5 minutes after boot
- Subsequent runs: Every 1 hour
- Accuracy: ±1 minute

---

## Common Issues & Solutions

### Timer Not Running
```bash
# Check timer status
sudo systemctl status crypto-pipeline.timer

# Check journal logs
sudo journalctl -u crypto-pipeline.timer -n 50

# Restart timer
sudo systemctl restart crypto-pipeline.timer
```

### Permission Denied
```bash
# Ensure you're running as crypto user
whoami  # Should show 'crypto'

# Check sudo permissions
sudo -v
```

### Python Not Found
```bash
# Verify virtual environment exists
ls -la ~/crypto-analysis/venv/bin/python3

# Recreate if needed
cd ~/crypto-analysis
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Telegram Not Sending
```bash
# Test Telegram configuration
source venv/bin/activate
python3 main.py test_telegram

# Verify environment variables
cat .env | grep TELEGRAM

# Check config.yaml
cat config/config.yaml | grep -A 3 telegram
```

### Database Lock Errors
```bash
# Check if another process is using the database
ps aux | grep python

# Wait for current run to finish, or restart timer
sudo systemctl restart crypto-pipeline.timer
```

---

## Maintenance Commands

### Update Code
```bash
cd ~/crypto-analysis

# If using git
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart timer (optional, will auto-restart on next run)
sudo systemctl restart crypto-pipeline.timer
```

### Stop/Start Automation
```bash
# Stop hourly runs
sudo systemctl stop crypto-pipeline.timer

# Start hourly runs
sudo systemctl start crypto-pipeline.timer

# Disable on boot
sudo systemctl disable crypto-pipeline.timer

# Enable on boot
sudo systemctl enable crypto-pipeline.timer
```

### View System Resources
```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Memory usage
free -h

# Process list
ps aux | grep python
```

---

## Log Management

Logs are automatically rotated:
- **Location**: `~/crypto-analysis/logs/pipeline.log`
- **Rotation**: Daily
- **Retention**: 7 days
- **Compression**: Enabled after rotation

View rotation config:
```bash
cat /etc/logrotate.d/crypto-pipeline
```

---

## Production Checklist

Before closing your laptop, verify:

- [ ] Timer is active: `sudo systemctl status crypto-pipeline.timer`
- [ ] Telegram test successful: `python3 main.py test_telegram`
- [ ] At least one successful pipeline run: `tail -n 100 logs/pipeline.log`
- [ ] Next run scheduled: `sudo systemctl list-timers crypto-pipeline.timer`
- [ ] Server accessible: `ping YOUR_DROPLET_IP`
- [ ] Disk space available: `df -h`

---

## Cost Optimization

- **Minimum Droplet**: $6/month (1GB RAM, 1 vCPU) - sufficient for this project
- **Estimated Data Usage**: ~10-50MB/month (depends on database growth)
- **Log Storage**: ~1-5MB/month (7-day retention)
- **Total Estimated Cost**: $6-12/month

To reduce costs:
- Use smallest droplet size
- Enable log compression (already configured)
- Set up database cleanup (already configured)

---

## Security Considerations

1. **SSH Keys**: Use SSH keys instead of passwords
2. **Firewall**: Configure UFW firewall (ports 22, 8000, 8501 if exposing dashboard)
3. **User Permissions**: Pipeline runs as non-root user (`crypto`)
4. **Secrets**: Store Telegram credentials in `.env` (not committed to git)
5. **Updates**: Keep system updated: `sudo apt update && sudo apt upgrade`

---

## Troubleshooting

For detailed troubleshooting, see [DEPLOYMENT_QUICKSTART.md](DEPLOYMENT_QUICKSTART.md)

**Quick Help Commands:**
```bash
# Check everything at once
sudo systemctl status crypto-pipeline.timer && \
sudo systemctl list-timers crypto-pipeline.timer && \
tail -n 20 ~/crypto-analysis/logs/pipeline.log
```

---

## Next Steps

Once deployed and verified:
1. ✅ Monitor first few runs via Telegram
2. ✅ Check logs periodically
3. ✅ Set up alerts for failures (optional)
4. ✅ Configure dashboard access (if needed)

**You're all set!** The pipeline will run automatically every hour, 24/7.
