
# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Health check with multiple verification methods
check_health() {
    # 1. Check if port is open
    if ! lsof -i :5000 >/dev/null 2>&1; then
        log "Port 5000 not in use"
        return 1
    fi

    # 2. Check if processes are running
    if ! pgrep -f "gunicorn.*main_app:app" >/dev/null; then
        log "Gunicorn process not found"
        return 1
    fi

    # 3. Check health endpoint
    RESPONSE=$(curl -sS --max-time 5 "$URL" 2>&1)
    if [[ $? -ne 0 ]]; then
        log "Curl failed: $RESPONSE"
        return 1
    fi

    # 4. Flexible status checking
    if [[ "$RESPONSE" == *'"status":"ok"'* ]] ||
       [[ "$RESPONSE" == *'"status": "ok"'* ]]; then
        log "Health check passed"
        return 0
    fi

    log "Unexpected response: $RESPONSE"
    return 1
}

# Main check with retries
log "Starting health check..."
for ((i=1; i<=MAX_RETRIES; i++)); do
    if check_health; then
        exit 0
    fi

    if [ $i -lt $MAX_RETRIES ]; then
        log "Attempt $i failed. Retrying in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
    fi
done

log "Health check failed after $MAX_RETRIES attempts. Restarting..."
bash "$RESTART_SCRIPT" >> "$LOG_FILE" 2>&1