#!/bin/bash

APP_DIR="/home/ubuntu/KZG_FB_Scraper"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
BOT_LOG="$LOG_DIR/bot.log"
CLOUDFLARED_LOG="$LOG_DIR/cloudflared.log"

mkdir -p "$LOG_DIR"
truncate -s 10M "$BOT_LOG" 2>/dev/null
truncate -s 10M "$CLOUDFLARED_LOG" 2>/dev/null

cd "$APP_DIR"
source "$VENV_DIR/bin/activate"

# === Check if gunicorn (Flask app) is running ===
if pgrep -f "gunicorn.*main_app:app" > /dev/null; then
    echo "Gunicorn already running. Skipping restart."
else
    echo "Gunicorn not running. Starting..."
    nohup gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --log-level info main_app:app > "$BOT_LOG" 2>&1 &
    sleep 2
fi

# === Check if Cloudflare is running ===
if pgrep -f "cloudflared.*kzg-chat" > /dev/null; then
    echo "Cloudflared already running. Skipping restart."
else
    echo "Cloudflared not running. Starting..."
    nohup cloudflared tunnel --config /home/ubuntu/.cloudflared/config.yml run kzg-chat > "$CLOUDFLARED_LOG" 2>&1 &
fi

echo "Startup script completed."
