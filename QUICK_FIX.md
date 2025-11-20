# You're currently SSH'd into the server. Here's what to do:

## Method 1: Exit and Upload from Local Machine

**On your server (currently):**
```bash
exit  # Exit SSH session
```

**Then on your LOCAL machine (new terminal):**
```bash
cd "/Users/ds/Desktop/Vibe coding/Analysis"
scp src/notifications/summary.py root@104.248.45.192:/home/crypto/crypto-analysis/src/notifications/
scp src/pipeline/pipeline.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/
scp src/pipeline/storage.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/
```

## Method 2: Edit Files Directly on Server (Easier!)

**While you're still SSH'd into the server (as root):**

```bash
# Switch to crypto user
su - crypto
cd ~/crypto-analysis

# Display the file contents so you can copy-paste
cat > src/notifications/summary.py << 'ENDOFFILE'
# Then paste the entire file content here
ENDOFFILE
```

**OR use nano/vim to edit directly:**

```bash
su - crypto
cd ~/crypto-analysis
nano src/notifications/summary.py
# Copy-paste the updated content, then Ctrl+X, Y, Enter
```

## Method 3: Download from GitHub/GitLab (If you have repo)

If you've pushed to git:
```bash
# On server (as crypto user)
su - crypto
cd ~/crypto-analysis
git pull
```

## Method 4: Use a File Transfer Tool

If you have the files in a git repo or on a paste service:
```bash
# On server
su - crypto
cd ~/crypto-analysis/src/notifications
curl -o summary.py https://raw.githubusercontent.com/YOUR_REPO/path/to/summary.py
```

