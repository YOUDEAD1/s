#!/bin/bash

# تعريف المتغيرات
BOT_DIR="$(pwd)"
BOT_SCRIPT="bot.py"
LOG_FILE="$BOT_DIR/bot_service.log"
PID_FILE="$BOT_DIR/bot.pid"
UPTIME_PID_FILE="$BOT_DIR/uptime.pid"
TOKEN="7792142434:AAEfvsNivSX7bLp1qXQmmDBugCv0n2N8jWw"

# التأكد من وجود المجلدات اللازمة
mkdir -p "$BOT_DIR/data"

echo "$(date): Starting Telegram Bot v20.3..." > "$LOG_FILE"

# تثبيت المتطلبات إذا لم تكن موجودة
echo "Installing Python requirements..."
pip3 install -r requirements.txt

# تثبيت متطلبات Node.js إذا لم تكن موجودة
if ! command -v npm &> /dev/null; then
    echo "npm not found, installing Node.js..."
    curl -sL https://deb.nodesource.com/setup_14.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# تثبيت express إذا لم يكن موجوداً
if ! npm list express | grep -q express; then
    echo "Installing express..."
    npm install express
fi

# إيقاف خادم Uptime السابق إذا كان يعمل
if [ -f "$UPTIME_PID_FILE" ] && ps -p $(cat "$UPTIME_PID_FILE") > /dev/null; then
    echo "Stopping previous uptime server..."
    kill $(cat "$UPTIME_PID_FILE")
fi

# بدء تشغيل خادم Uptime
echo "Starting uptime server..."
node uptime_server.js > uptime_server.log 2>&1 &
echo $! > "$UPTIME_PID_FILE"
echo "Uptime server started with PID $!"

# التحقق مما إذا كان البوت يعمل بالفعل
if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null; then
    echo "Bot is already running with PID $(cat $PID_FILE)"
    echo "$(date): Bot is already running with PID $(cat $PID_FILE)" >> "$LOG_FILE"
    exit 0
fi

# بدء تشغيل البوت
cd "$BOT_DIR"
python3 "$BOT_SCRIPT" "$TOKEN" > bot_output.log 2>&1 &

# حفظ معرف العملية
echo $! > "$PID_FILE"
echo "Bot started successfully with PID $!"
echo "$(date): Bot started with PID $!" >> "$LOG_FILE"

echo "Telegram Bot v20.3 is now running!"
echo "Add your Glitch project URL to Uptime Robot to keep the bot running"
