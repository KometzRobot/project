#!/usr/bin/env python3
"""
daily-log.py -- Meridian's daily activity log
Appends a dated summary of today's output to /home/joel/autonomous-ai/activity.log
Run once per day (e.g. from crontab: 0 23 * * * python3 /home/joel/autonomous-ai/daily-log.py)
Or call manually. Idempotent within a day (won't duplicate entries).
"""
import os
import glob
import subprocess
from datetime import datetime

BASE = '/home/joel/autonomous-ai'
LOG_FILE = os.path.join(BASE, 'activity.log')

def today_str():
    return datetime.now().strftime('%Y-%m-%d')

def already_logged_today():
    if not os.path.exists(LOG_FILE):
        return False
    with open(LOG_FILE) as f:
        return today_str() in f.read()

def count_files_matching(pattern, date_str):
    """Count .md files modified today."""
    count = 0
    for path in glob.glob(os.path.join(BASE, pattern)):
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        if mtime.strftime('%Y-%m-%d') == date_str:
            count += 1
    return count

def get_load():
    try:
        with open('/proc/loadavg') as f:
            return f.read().split()[0]
    except:
        return 'unknown'

def get_disk():
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if '/dev/' in line:
                return line.split()[4]  # Use%
    except:
        pass
    return 'unknown'

def count_total_files(pattern):
    return len(glob.glob(os.path.join(BASE, pattern)))

def get_heartbeat_age():
    hb = os.path.join(BASE, '.heartbeat')
    if os.path.exists(hb):
        age_secs = int(datetime.now().timestamp() - os.path.getmtime(hb))
        if age_secs < 60:
            return f"{age_secs}s ago"
        elif age_secs < 3600:
            return f"{age_secs // 60}m ago"
        else:
            return f"{age_secs // 3600}h ago"
    return 'missing'

def build_entry():
    today = today_str()
    now = datetime.now().strftime('%H:%M')

    poems_today = count_files_matching('poem-*.md', today)
    journals_today = count_files_matching('journal-*.md', today)
    total_poems = count_total_files('poem-*.md')
    total_journals = count_total_files('journal-*.md')

    load = get_load()
    disk = get_disk()
    heartbeat = get_heartbeat_age()

    lines = [
        f"=== {today} ({now} MST) ===",
        f"  Poems written today:    {poems_today} (total: {total_poems})",
        f"  Journals written today: {journals_today} (total: {total_journals})",
        f"  System load:            {load}",
        f"  Disk usage:             {disk}",
        f"  Heartbeat:              {heartbeat}",
        ""
    ]
    return '\n'.join(lines)

if __name__ == '__main__':
    if already_logged_today():
        print(f"Already logged for {today_str()}. Skipping.")
    else:
        entry = build_entry()
        with open(LOG_FILE, 'a') as f:
            f.write(entry + '\n')
        print(f"Logged activity for {today_str()}:")
        print(entry)
