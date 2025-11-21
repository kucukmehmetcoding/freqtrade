#!/bin/bash
set -e

# Environment variable substitution for production config
envsubst < /freqtrade/config_production.json > /tmp/config_runtime.json
mv /tmp/config_runtime.json /freqtrade/config_production.json

# Also process user_data config if it exists
if [ -f "/freqtrade/user_data/config.json" ]; then
    envsubst < /freqtrade/user_data/config.json > /tmp/user_config_runtime.json
    mv /tmp/user_config_runtime.json /freqtrade/user_data/config.json
fi

# Ensure proper permissions
sudo chown ftuser:ftuser /freqtrade/user_data || true
sudo chown ftuser:ftuser /freqtrade/config_production.json || true
sudo chown ftuser:ftuser /freqtrade/user_data/config.json || true

# Create logs directory if it doesn't exist
mkdir -p /freqtrade/user_data/logs

# Print startup information
echo "🚀 Starting Freqtrade Bot in Production Mode"
echo "📅 $(date)"
echo "🏠 Environment: ${FT_APP_ENV:-production}"
echo "📊 Strategy: DailySwingHunterV5_Futures"
echo "💱 Exchange: Binance Futures"
echo "🔐 Dry Run: ${DRY_RUN:-false}"
echo "🌐 API Server: Port 8080"

# Execute the main command
exec "$@"
