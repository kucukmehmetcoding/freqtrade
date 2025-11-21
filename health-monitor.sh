#!/bin/bash
# Freqtrade Health Monitor Script for Production
# This script monitors the health of your Freqtrade bot and sends alerts

set -e

CONTAINER_NAME="freqtrade-production"
API_ENDPOINT="http://localhost:8080"
LOG_FILE="/var/log/freqtrade-monitor.log"
ALERT_WEBHOOK="${DISCORD_WEBHOOK_URL}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

send_alert() {
    local message="$1"
    local status="$2"

    log_message "ALERT: $message"

    # Send Discord webhook if configured
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -H "Content-Type: application/json" \
             -X POST \
             -d "{\"content\": \"🤖 **Freqtrade Alert** [$status]\n\`\`\`$message\`\`\`\"}" \
             "$ALERT_WEBHOOK" 2>/dev/null || true
    fi
}

check_container_status() {
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        send_alert "Container $CONTAINER_NAME is not running!" "CRITICAL"
        return 1
    fi
    return 0
}

check_api_health() {
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT/api/v1/ping" 2>/dev/null || echo "000")

    if [ "$response" != "200" ]; then
        send_alert "API endpoint unreachable. HTTP code: $response" "WARNING"
        return 1
    fi
    return 0
}

check_bot_status() {
    local status
    status=$(curl -s "$API_ENDPOINT/api/v1/status" 2>/dev/null | jq -r '.state // "unknown"' 2>/dev/null || echo "unknown")

    if [ "$status" != "running" ]; then
        send_alert "Bot is not in running state. Current state: $status" "WARNING"
        return 1
    fi
    return 0
}

check_recent_trades() {
    local trade_count
    trade_count=$(curl -s "$API_ENDPOINT/api/v1/trades" 2>/dev/null | jq '.trades | length' 2>/dev/null || echo "0")

    # Alert if no trades in the last 24 hours (adjust as needed)
    if [ "$trade_count" -eq 0 ]; then
        log_message "INFO: No recent trades found"
    else
        log_message "INFO: Found $trade_count recent trades"
    fi
}

check_system_resources() {
    local memory_usage
    local cpu_usage

    memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" "$CONTAINER_NAME" 2>/dev/null | sed 's/%//' || echo "0")
    cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" "$CONTAINER_NAME" 2>/dev/null | sed 's/%//' || echo "0")

    # Alert if memory usage > 90%
    if (( $(echo "$memory_usage > 90" | bc -l) )); then
        send_alert "High memory usage detected: ${memory_usage}%" "WARNING"
    fi

    # Alert if CPU usage > 80%
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        send_alert "High CPU usage detected: ${cpu_usage}%" "WARNING"
    fi

    log_message "RESOURCES: CPU: ${cpu_usage}%, Memory: ${memory_usage}%"
}

main() {
    log_message "Starting Freqtrade health check..."

    local issues=0

    # Run all health checks
    check_container_status || ((issues++))
    check_api_health || ((issues++))
    check_bot_status || ((issues++))
    check_recent_trades
    check_system_resources

    if [ $issues -eq 0 ]; then
        log_message "✅ All health checks passed"
        printf "${GREEN}✅ Freqtrade is healthy${NC}\n"
    else
        log_message "❌ Health check completed with $issues issues"
        printf "${RED}❌ Found $issues issues${NC}\n"
        exit 1
    fi
}

# Run the main function
main "$@"
