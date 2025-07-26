#!/bin/bash

HEALTH_URL="http://localhost:5000/health"
LOG_FILE="/var/log/bot_health.log"
RESTART_LOG="/var/log/bot_restart.log"

# Gửi request đến /health
RESPONSE=$(curl --silent --max-time 10 "$HEALTH_URL" | grep -o '"status":"ok"')

# Kiểm tra phản hồi
if [ "$RESPONSE" != '"status":"ok"' ]; then
    echo "$(date): ❌ Bot không phản hồi. Đang restart Gunicorn..." >> "$LOG_FILE"

    # Gọi script khởi động lại bot
    /home/ubuntu/start_bot.sh >> "$RESTART_LOG" 2>&1
else
    echo "$(date): ✅ Bot đang hoạt động bình thường." >> "$LOG_FILE"
fi
