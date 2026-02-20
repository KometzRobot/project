#!/bin/bash
# Status Display Watchdog
# Runs every 5 minutes via cron
# Restarts the status-display.py terminal if it's not running

WORKING_DIR="$HOME/autonomous-ai"
PYTHON="$HOME/miniconda3/bin/python3"
LOG="$WORKING_DIR/watchdog-status.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

export DISPLAY=:0

# Set XAUTHORITY so X11 apps can connect
if [ -f "/run/user/1000/gdm/Xauthority" ]; then
    export XAUTHORITY="/run/user/1000/gdm/Xauthority"
elif [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
fi

if ! pgrep -f "status-display-v8.py" > /dev/null; then
    log "ALERT: status-display-v8.py is NOT running. Restarting..."
    # Kill any older version that may be running
    pkill -f "status-display-v5.py" 2>/dev/null || true
    pkill -f "status-display-v6.py" 2>/dev/null || true
    pkill -f "status-display-v7.py" 2>/dev/null || true

    DISPLAY=:0 XAUTHORITY="$XAUTHORITY" $PYTHON "$WORKING_DIR/status-display-v8.py" >> "$WORKING_DIR/status-display.log" 2>&1 &

    log "Status display v8 restarted (PID: $!)"
else
    log "OK: status-display-v8.py is running."
fi

# Also check IRC bot
if ! pgrep -f "irc-bot.py" > /dev/null; then
    log "ALERT: irc-bot.py is NOT running. Restarting..."
    nohup $PYTHON "$WORKING_DIR/irc-bot.py" >> "$WORKING_DIR/irc-bot.log" 2>&1 &
    log "IRC bot restarted (PID: $!)"
fi
