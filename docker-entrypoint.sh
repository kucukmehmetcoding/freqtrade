#!/bin/bash
set -e

echo "🔄 Initializing Freqtrade container..."

# Process config with environment variables
if [ -f "/freqtrade/user_data/config.json" ]; then
    echo "📝 Found config template, processing environment variables..."
    
    # Check for required variables
    if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_SECRET" ]; then
        echo "⚠️  WARNING: BINANCE_API_KEY or BINANCE_SECRET is missing!"
    fi

    # Substitute environment variables
    # We use a temp file to avoid issues with reading/writing same file
    envsubst < /freqtrade/user_data/config.json > /tmp/config_runtime.json
    mv /tmp/config_runtime.json /freqtrade/user_data/config.json
    
    echo "✅ Config file generated successfully at /freqtrade/user_data/config.json"
else
    echo "❌ ERROR: Config file /freqtrade/user_data/config.json not found!"
    exit 1
fi

# Ensure proper permissions
echo "wm Fixing permissions..."
sudo chown -R ftuser:ftuser /freqtrade/user_data || true

# Create logs directory if it doesn't exist
mkdir -p /freqtrade/user_data/logs

# Print startup information
echo "🚀 Starting Freqtrade Bot in Production Mode"
echo "📅 Date: $(date)"
echo "🏠 Environment: ${FT_APP_ENV:-production}"
echo "📊 Strategy: DailySwingHunterV5_Futures"
echo "💱 Exchange: Binance Futures"
echo "🔐 Dry Run: ${DRY_RUN:-false}"
echo "🌐 API Server: Port 8080"

# Execute the main command
exec "$@"
