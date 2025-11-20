# Alternative Deployment Methods

## Option 1: Connect as Root (If You Set Up Server This Way)

If you originally set up the server using `root@YOUR_DROPLET_IP`, try:

```bash
# Upload files as root, then move them to crypto user
scp src/notifications/summary.py root@104.248.45.192:/home/crypto/crypto-analysis/src/notifications/
scp src/pipeline/pipeline.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/
scp src/pipeline/storage.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/
```

## Option 2: Set Up SSH Key Authentication (Recommended)

### Step 1: Generate SSH Key (if you don't have one)
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter to accept default location
# Press Enter twice for no passphrase (or set one if you prefer)
```

### Step 2: Copy Key to Server
```bash
# Connect as root first (if that works)
ssh root@104.248.45.192

# On the server, add your public key to crypto user
mkdir -p /home/crypto/.ssh
nano /home/crypto/.ssh/authorized_keys
# Paste your public key content here (from ~/.ssh/id_ed25519.pub)
chown -R crypto:crypto /home/crypto/.ssh
chmod 700 /home/crypto/.ssh
chmod 600 /home/crypto/.ssh/authorized_keys
exit
```

### Step 3: Get Your Public Key
```bash
# On your local machine
cat ~/.ssh/id_ed25519.pub
# Copy this output
```

### Step 4: Add Key to Server (via DigitalOcean Console or root SSH)
If you can access DigitalOcean console or SSH as root:
```bash
ssh root@104.248.45.192
cat >> /home/crypto/.ssh/authorized_keys << 'EOF'
# Paste your public key here
EOF
chown -R crypto:crypto /home/crypto/.ssh
chmod 700 /home/crypto/.ssh
chmod 600 /home/crypto/.ssh/authorized_keys
```

## Option 3: Use DigitalOcean Console

1. Go to DigitalOcean dashboard
2. Click on your droplet
3. Click "Access" → "Launch Droplet Console"
4. Log in (as root or crypto user)
5. Use `nano` or `vi` to edit files directly
6. Copy-paste the file contents

## Option 4: Quick File Update via Server Console

SSH into server via DigitalOcean console, then:

```bash
# Connect to server (via console or root)
cd /home/crypto/crypto-analysis

# Edit files directly using nano
nano src/notifications/summary.py
# Copy-paste the updated content
# Ctrl+X, Y, Enter to save

nano src/pipeline/pipeline.py
# Copy-paste the updated content

nano src/pipeline/storage.py
# Copy-paste the updated content
```

## Option 5: Use rsync with Password (if password auth is enabled)

```bash
# Try with password prompt
rsync -avz -e ssh src/notifications/summary.py crypto@104.248.45.192:~/crypto-analysis/src/notifications/
```

## Quick Test: Check What Authentication Works

Try these in order:

```bash
# 1. Try root
ssh root@104.248.45.192

# 2. Try crypto with password prompt
ssh -o PreferredAuthentications=password crypto@104.248.45.192

# 3. Check if you have SSH keys elsewhere
ls -la ~/.ssh/
```

