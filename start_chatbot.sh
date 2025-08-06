#!/bin/bash

# Configuration
APP_DIR="/home/ubuntu/KZG_FB_Scraper"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
BOT_LOG="$LOG_DIR/bot.log"
CLOUDFLARED_LOG="$LOG_DIR/cloudflared.log"
GUNICORN_CMD="gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --log-level info main_app:app"
CLOUDFLARED_CMD="cloudflared tunnel --config /home/ubuntu/.cloudflared/config.yml run kzg-chat"

# Setup environment
mkdir -p "$LOG_DIR"

for log in "$BOT_LOG" "$CLOUDFLARED_LOG"; do
    [ -f "$log" ] && tail -n 500 "$log" > "${log}.tmp" && mv "${log}.tmp" "$log"
done

cd "$APP_DIR" || { echo "Failed to cd to $APP_DIR"; exit 1; }

# Verify virtualenv
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Virtualenv not found at $VENV_DIR" >&2
    exit 1
fi

# Source virtualenv
source "$VENV_DIR/bin/activate" || { echo "Failed to activate virtualenv"; exit 1; }

# Kill old processes more reliably
echo "Stopping existing processes..."
pkill -f "$GUNICORN_CMD" || true
pkill -f "$CLOUDFLARED_CMD" || true

# Wait for ports to free up

# Start Gunicorn with more verbose logging
echo "Starting Gunicorn..."
nohup $GUNICORN_CMD >> "$BOT_LOG" 2>&1 &
GUNICORN_PID=$!
echo "Gunicorn started with PID $GUNICORN_PID"

# Verify Gunicorn started properly
sleep 10  # Increased wait time
if ! ps -p $GUNICORN_PID > /dev/null; then
    echo "Error: Gunicorn failed to start!" >&2
    echo "Last 20 lines of log:" >&2
    tail -n 20 "$BOT_LOG" >&2
    exit 1
fi

# Start Cloudflared
echo "Starting Cloudflared..."
nohup $CLOUDFLARED_CMD >> "$CLOUDFLARED_LOG" 2>&1 &
CLOUDFLARED_PID=$!
echo "Cloudflared started with PID $CLOUDFLARED_PID"

# Verify Cloudflared started properly
sleep 5
if ! ps -p $CLOUDFLARED_PID > /dev/null; then
    echo "Error: Cloudflared failed to start!" >&2
    echo "Last 20 lines of log:" >&2
    tail -n 20 "$CLOUDFLARED_LOG" >&2
    exit 1
fi

echo "Startup script completed successfully"