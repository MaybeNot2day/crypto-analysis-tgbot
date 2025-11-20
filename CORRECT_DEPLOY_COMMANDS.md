# Correct Deployment Commands

## Fix: You need to include `scp` at the beginning!

**Wrong:**
```bash
Analysis src/pipeline/storage.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/
```

**Correct:**
```bash
scp src/pipeline/storage.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/
scp src/api/app.py root@104.248.45.192:/home/crypto/crypto-analysis/src/api/
```

## All Fixed Files to Deploy

Run these commands from your project directory:

```bash
cd "/Users/ds/Desktop/Vibe coding/Analysis"

# Upload all fixed files
scp src/factors/calculator.py root@104.248.45.192:/home/crypto/crypto-analysis/src/factors/
scp src/notifications/summary.py root@104.248.45.192:/home/crypto/crypto-analysis/src/notifications/
scp src/pipeline/storage.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/
scp src/api/app.py root@104.248.45.192:/home/crypto/crypto-analysis/src/api/
scp src/notifications/telegram.py root@104.248.45.192:/home/crypto/crypto-analysis/src/notifications/
```

## Quick Copy-Paste (All at Once)

```bash
cd "/Users/ds/Desktop/Vibe coding/Analysis" && \
scp src/factors/calculator.py root@104.248.45.192:/home/crypto/crypto-analysis/src/factors/ && \
scp src/notifications/summary.py root@104.248.45.192:/home/crypto/crypto-analysis/src/notifications/ && \
scp src/pipeline/storage.py root@104.248.45.192:/home/crypto/crypto-analysis/src/pipeline/ && \
scp src/api/app.py root@104.248.45.192:/home/crypto/crypto-analysis/src/api/ && \
scp src/notifications/telegram.py root@104.248.45.192:/home/crypto/crypto-analysis/src/notifications/ && \
echo "✅ All files uploaded successfully!"
```

