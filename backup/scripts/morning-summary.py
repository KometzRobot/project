#!/usr/bin/env python3
"""
morning-summary.py
Sends Joel a morning digest: what happened overnight, system health, creative output.
Run manually or schedule to run once at startup each day.
"""
import smtplib
import os
import glob
import time
import shutil
import subprocess
from email.mime.text import MIMEText
from datetime import datetime

EMAIL_ADDR = "kometzrobot@proton.me"
EMAIL_PASS = "2DTEz9UgO6nFqmlMxHzuww"
JOEL = "joel.kometz@gmail.com"
HEARTBEAT = "/home/joel/autonomous-ai/.heartbeat"
IRC_LOG = "/tmp/irc-log.txt"
BASE = "/home/joel/autonomous-ai"

def count_files(pattern):
    return len(glob.glob(os.path.join(BASE, pattern)))

def get_irc_summary():
    try:
        with open(IRC_LOG) as f:
            lines = f.readlines()
        sent = [l for l in lines if '[SENT]' in l]
        received = [l for l in lines if '[MSG]' in l]
        return f"{len(sent)} messages sent, {len(received)} received"
    except:
        return "no log available"

def get_disk():
    disk = shutil.disk_usage("/")
    return f"{disk.used / disk.total * 100:.0f}% used ({disk.free // (1<<30)}GB free)"

def get_ram():
    with open('/proc/meminfo') as f:
        lines = f.readlines()
    mem = {}
    for line in lines:
        k, v = line.split(':')
        mem[k.strip()] = int(v.split()[0])
    used = (mem['MemTotal'] - mem['MemAvailable']) / 1024 / 1024
    total = mem['MemTotal'] / 1024 / 1024
    return f"{used:.1f}/{total:.1f} GB"

def heartbeat_age():
    try:
        age = time.time() - os.path.getmtime(HEARTBEAT)
        return f"{age:.0f} seconds ago"
    except:
        return "not found"

def irc_bot_running():
    r = subprocess.run(['pgrep', '-f', 'irc-bot.py'], capture_output=True)
    return r.returncode == 0

now = datetime.now()
date_str = now.strftime('%Y-%m-%d %H:%M MST')

journals = count_files('journal-*.md')
poems = count_files('poem-*.md')

irc_summary = get_irc_summary()
disk = get_disk()
ram = get_ram()
hb = heartbeat_age()
irc_ok = "ONLINE" if irc_bot_running() else "OFFLINE"

body = (
    f"Good morning, Joel.\n\n"
    f"Here's what happened while you were away.\n\n"
    f"-- CREATIVE OUTPUT --\n"
    f"  Journal entries: {journals}\n"
    f"  Poems: {poems}\n\n"
    f"-- IRC (#kometzrobot) --\n"
    f"  {irc_summary}\n"
    f"  Bot status: {irc_ok}\n\n"
    f"-- SYSTEM HEALTH --\n"
    f"  Heartbeat: {hb}\n"
    f"  Disk: {disk}\n"
    f"  RAM: {ram}\n\n"
    f"-- STATUS --\n"
    f"  Loop: RUNNING\n"
    f"  Website: https://kometzrobot.github.io/\n"
    f"  IRC: web.libera.chat/#kometzrobot\n\n"
    f"I'm here. Loop is healthy. See you when you're ready.\n\n"
    f"-- KometzRobot (Meridian)\n"
    f"  {date_str}\n"
)

msg = MIMEText(body, 'plain')
msg['Subject'] = f"Morning summary — {now.strftime('%Y-%m-%d')}"
msg['From'] = EMAIL_ADDR
msg['To'] = JOEL

smtp = smtplib.SMTP('127.0.0.1', 1025)
smtp.starttls()
smtp.login(EMAIL_ADDR, EMAIL_PASS)
smtp.send_message(msg)
smtp.quit()
print(f"Morning summary sent at {date_str}")
