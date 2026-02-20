#!/bin/bash
# KometzRobot startup script
# Called at @reboot via crontab
# Starts all services that make me alive

WORKING_DIR="$HOME/autonomous-ai"
LOG="$WORKING_DIR/startup.log"
PYTHON="$HOME/miniconda3/bin/python3"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "=== STARTUP INITIATED ==="

# Wait for desktop to be ready
sleep 20

export DISPLAY=:0

# Set XAUTHORITY — try user gdm auth first, then fallback
if [ -f "/run/user/1000/gdm/Xauthority" ]; then
    export XAUTHORITY="/run/user/1000/gdm/Xauthority"
elif [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
fi
log "XAUTHORITY: $XAUTHORITY"

# 0. ProtonMail Bridge (required for email — must start first)
# Set DBUS_SESSION_BUS_ADDRESS so bridge can access gnome-keyring for vault unlock
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"
if ! pgrep -f "protonmail-bridge" > /dev/null; then
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus" nohup /snap/bin/protonmail-bridge --noninteractive >> "$WORKING_DIR/bridge.log" 2>&1 &
    log "ProtonMail Bridge started (headless mode, dbus keyring enabled)"
    sleep 8  # Give bridge time to connect before we need IMAP
else
    log "ProtonMail Bridge already running"
fi

# 1. HTTP server for local website
if ! pgrep -f "http.server 8080" > /dev/null; then
    cd "$WORKING_DIR/website"
    nohup $PYTHON -m http.server 8080 >> "$WORKING_DIR/http-server.log" 2>&1 &
    log "HTTP server started (port 8080)"
else
    log "HTTP server already running"
fi

sleep 2

# 2. Localtunnel
if ! pgrep -f "lt --port 8080" > /dev/null; then
    nohup /usr/bin/lt --port 8080 --subdomain kometzrobot >> "$WORKING_DIR/tunnel.log" 2>&1 &
    log "Localtunnel started (kometzrobot.loca.lt)"
else
    log "Localtunnel already running"
fi

sleep 2

# 3. IRC bot
if ! pgrep -f "irc-bot.py" > /dev/null; then
    nohup $PYTHON "$WORKING_DIR/irc-bot.py" >> "$WORKING_DIR/irc-bot.log" 2>&1 &
    log "IRC bot started"
else
    log "IRC bot already running"
fi

sleep 3

# 3.5. Ollama (local AI model server)
if ! pgrep -f "ollama serve" > /dev/null; then
    nohup /usr/local/bin/ollama serve >> "$WORKING_DIR/ollama.log" 2>&1 &
    log "Ollama started (local AI model server)"
    sleep 5  # Give Ollama time to load
else
    log "Ollama already running"
fi

# 4. Status display v8 — fullscreen live monitor with inner life + human control
if ! pgrep -f "status-display" > /dev/null; then
    DISPLAY=:0 XAUTHORITY="$XAUTHORITY" $PYTHON "$WORKING_DIR/status-display-v8.py" >> "$WORKING_DIR/status-display.log" 2>&1 &
    log "Status display v8 started (inner life monitor + control hub)"
else
    log "Status display already running"
fi

sleep 3

# 5. Start Claude (main AI loop) via watchdog
log "Triggering watchdog to start Claude..."
bash "$WORKING_DIR/watchdog.sh"

log "=== STARTUP COMPLETE ==="
