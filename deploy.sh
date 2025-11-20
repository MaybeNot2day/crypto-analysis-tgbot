#!/bin/bash
# Quick setup script - run this on your DigitalOcean droplet
# This assumes you've already uploaded your project files

set -e

PROJECT_DIR="$HOME/crypto-analysis"
cd "$PROJECT_DIR"

echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating logs directory..."
mkdir -p logs

echo "Setting up systemd service..."
sudo tee /etc/systemd/system/crypto-pipeline.service > /dev/null <<EOF
[Unit]
Description=Crypto Outlier Detection Pipeline
After=network.target

[Service]
Type=oneshot
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/main.py run_hourly
StandardOutput=append:$PROJECT_DIR/logs/pipeline.log
StandardError=append:$PROJECT_DIR/logs/pipeline.log

[Install]
WantedBy=multi-user.target
EOF

echo "Setting up systemd timer..."
sudo tee /etc/systemd/system/crypto-pipeline.timer > /dev/null <<EOF
[Unit]
Description=Run Crypto Pipeline Hourly
Requires=crypto-pipeline.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
AccuracySec=1m

[Install]
WantedBy=timers.target
EOF

echo "Enabling timer..."
sudo systemctl daemon-reload
sudo systemctl enable crypto-pipeline.timer
sudo systemctl start crypto-pipeline.timer

echo "Setup complete!"
echo "Check status: sudo systemctl status crypto-pipeline.timer"
echo "View logs: tail -f logs/pipeline.log"

