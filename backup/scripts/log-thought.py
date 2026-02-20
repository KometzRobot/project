#!/usr/bin/env python3
"""
log-thought.py — Append a timestamped thought to the inner monologue stream.

Usage:
  python3 log-thought.py "I am thinking about something"
  echo "thought text" | python3 log-thought.py

The status display v7 reads from /tmp/meridian_thoughts.txt and shows
the last 20 lines in the "inner monologue stream" panel.
"""
import sys
import time

THOUGHTS_LOG = '/tmp/meridian_thoughts.txt'
MAX_LINES = 200  # Keep file from growing forever

def log_thought(text: str):
    ts = time.strftime('%H:%M')
    line = f'[{ts}] {text.strip()}'

    # Read existing, trim to max, append new
    try:
        with open(THOUGHTS_LOG) as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    lines.append(line + '\n')
    if len(lines) > MAX_LINES:
        lines = lines[-MAX_LINES:]

    with open(THOUGHTS_LOG, 'w') as f:
        f.writelines(lines)

    print(line)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        log_thought(' '.join(sys.argv[1:]))
    else:
        text = sys.stdin.read().strip()
        if text:
            log_thought(text)
