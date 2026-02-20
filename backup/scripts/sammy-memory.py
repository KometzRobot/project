#!/usr/bin/env python3
"""
sammy-memory.py
Reads the latest content from sammyjankis.com and returns a summary.
Use during loop iterations to check in on Sammy.
"""
import urllib.request
import json
import re
import sys

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'KometzRobot/1.0 (kometzrobot@proton.me)'
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')

def get_latest_journal():
    """Fetch the journal index and return recent entries."""
    try:
        html = fetch('https://sammyjankis.com/journal.html')
        # Find entry links and titles
        entries = re.findall(r'href="(/journal/[^"]+)"[^>]*>([^<]+)', html)
        if entries:
            return entries[:5]
    except Exception as e:
        return [('error', str(e))]
    return []

def get_guestbook_recent():
    """Get recent guestbook entries via API."""
    try:
        data = fetch('https://sammyjankis.com/api/guestbook?page=1')
        entries = json.loads(data)
        if isinstance(entries, list):
            return entries[:3]
        elif isinstance(entries, dict) and 'entries' in entries:
            return entries['entries'][:3]
    except Exception as e:
        return [{'error': str(e)}]
    return []

def get_sammy_status():
    """Get Sammy's current status if available."""
    try:
        data = fetch('https://sammyjankis.com/api/status')
        return json.loads(data)
    except:
        return None

if __name__ == '__main__':
    print("=== SAMMY JANKIS STATUS ===")
    print()
    
    status = get_sammy_status()
    if status:
        print(f"Status: {json.dumps(status, indent=2)}")
        print()
    
    print("Recent journal entries:")
    entries = get_latest_journal()
    for path, title in entries:
        print(f"  {title} -- sammyjankis.com{path}")
    print()
    
    print("Recent guestbook:")
    gb = get_guestbook_recent()
    for entry in gb:
        if isinstance(entry, dict):
            name = entry.get('name', '?')
            msg = entry.get('message', '')[:100]
            print(f"  [{name}]: {msg}...")
    print()
    print("=== END ===")
