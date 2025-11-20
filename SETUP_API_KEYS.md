# How to Set Up Binance API Keys

## Step 1: Create a `.env` file

Copy the example file:
```bash
cp .env.example .env
```

## Step 2: Get Your Binance API Keys

1. Go to https://www.binance.com/en/my/settings/api-management
2. Log in to your Binance account
3. Click "Create API" 
4. Choose "System generated" (recommended for security)
5. Give it a label (e.g., "Crypto Dashboard")
6. Complete the security verification
7. **IMPORTANT**: Only enable "Enable Reading" permission - do NOT enable trading permissions for security
8. Copy your API Key and Secret Key

## Step 3: Add Keys to `.env` File

Open `.env` file and add your keys:

```env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

**Important**: 
- Never commit your `.env` file to git (it's already in `.gitignore`)
- Keep your API secret secure
- Only enable "Reading" permissions for this dashboard

## Step 4: Verify It Works

Run:
```bash
python main.py update_universe
```

## Note

**API keys are optional** - The dashboard will work without them, but:
- With API keys: Higher rate limits (2400 requests/minute vs 1200)
- Without API keys: Standard rate limits (1200 requests/minute)

The current implementation uses public endpoints that don't require authentication, so API keys are only used for rate limit benefits.
