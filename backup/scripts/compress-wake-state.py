#!/usr/bin/env python3
"""
MERIDIAN TOOL: compress-wake-state.py
Compresses old loop entries in wake-state.md to keep the file manageable.

The wake-state.md grows with each loop iteration. After 280+ loops it can
become hundreds of lines, making it expensive to read as context.

This tool:
- Keeps the last N loop entries in full detail (default: 15)
- Summarizes older entries into daily/session summaries
- Preserves all non-loop-entry content (CRITICAL CONTEXT, etc.)

Usage:
  python3 compress-wake-state.py [--dry-run] [--keep N]
"""

import re
import sys
import os
from datetime import datetime
from collections import defaultdict

WAKE_STATE = '/home/joel/autonomous-ai/wake-state.md'
BACKUP_PATH = '/home/joel/autonomous-ai/wake-state.md.bak'


def load_wake_state(path=WAKE_STATE):
    with open(path) as f:
        return f.read()


def parse_loop_entries(content):
    """
    Parse the loop entries at the top of the Current Status section.
    Returns:
        - header: text before Current Status section
        - entries: list of (loop_num, line_text) for loop iterations
        - remaining: text after the loop entries (CRITICAL CONTEXT etc.)
    """
    lines = content.split('\n')

    header_lines = []
    entry_lines = []
    remaining_lines = []

    state = 'header'  # header -> entries -> remaining

    for line in lines:
        if state == 'header':
            header_lines.append(line)
            if line.strip() == '## Current Status: RUNNING':
                state = 'entries'
        elif state == 'entries':
            if re.match(r'^- Loop iteration #\d+', line):
                entry_lines.append(line)
            elif line.strip() == '' and entry_lines:
                # Allow blank lines between entries
                entry_lines.append(line)
            else:
                state = 'remaining'
                remaining_lines.append(line)
        else:
            remaining_lines.append(line)

    return header_lines, entry_lines, remaining_lines


def summarize_old_entries(entries, keep_last=15):
    """
    Given a list of loop entry lines, keep the last N in full
    and summarize the rest.
    Returns: (summary_block, kept_entries)
    """
    # Filter to only actual loop entries (not blank lines)
    loop_entries = [e for e in entries if re.match(r'^- Loop iteration #\d+', e)]

    if len(loop_entries) <= keep_last:
        return None, entries

    old_entries = loop_entries[:-keep_last]
    kept_entries = loop_entries[-keep_last:]

    # Generate summary of old entries
    count = len(old_entries)

    # Extract loop numbers
    nums = []
    for e in old_entries:
        m = re.search(r'Loop iteration #(\d+)', e)
        if m:
            nums.append(int(m.group(1)))

    if nums:
        min_loop = min(nums)
        max_loop = max(nums)
    else:
        min_loop = max_loop = 0

    # Find notable events
    notable = []
    for e in old_entries:
        if 'new email' in e.lower() and 'no new email' not in e.lower():
            # Extract email numbers
            email_m = re.findall(r'email #(\d+)', e, re.IGNORECASE)
            if email_m:
                notable.append(f'email #{email_m[0]} received+replied')
        if 'built:' in e.lower():
            built_m = re.search(r'[Bb]uilt:\s*([^.]+)', e)
            if built_m:
                notable.append(f'built: {built_m.group(1).strip()[:50]}')
        if 'pushed' in e.lower():
            pushed_m = re.search(r'[Pp]ushed\s+([^(]+)', e)
            if pushed_m:
                notable.append(f'pushed: {pushed_m.group(1).strip()[:40]}')

    notable_str = '; '.join(notable[:5]) if notable else 'routine maintenance'

    summary = (f'- [COMPRESSED: loops #{min_loop}-#{max_loop}, {count} iterations] '
               f'Key events: {notable_str}')

    return summary, kept_entries


def compress(dry_run=False, keep_last=15):
    content = load_wake_state()
    header_lines, entry_lines, remaining_lines = parse_loop_entries(content)

    summary, kept_entries = summarize_old_entries(entry_lines, keep_last)

    if summary is None:
        print(f'Nothing to compress (only {len([e for e in entry_lines if e.strip()])} entries, threshold: {keep_last})')
        return

    old_count = len([e for e in entry_lines if re.match(r'^- Loop iteration #', e)])
    new_count = len([e for e in kept_entries if re.match(r'^- Loop iteration #', e)])
    removed = old_count - new_count

    print(f'Compression plan:')
    print(f'  Total entries before: {old_count}')
    print(f'  Entries to compress:  {removed}')
    print(f'  Entries to keep:      {new_count}')
    print(f'  Summary: {summary[:80]}...')

    if dry_run:
        print('\n[DRY RUN — not writing]')
        return

    # Backup original
    with open(BACKUP_PATH, 'w') as f:
        f.write(content)
    print(f'  Backup written to {BACKUP_PATH}')

    # Reconstruct
    new_lines = (
        header_lines +
        [summary] +
        kept_entries +
        remaining_lines
    )

    new_content = '\n'.join(new_lines)

    with open(WAKE_STATE, 'w') as f:
        f.write(new_content)

    old_size = len(content)
    new_size = len(new_content)
    reduction = (old_size - new_size) / old_size * 100

    print(f'  Size: {old_size} → {new_size} bytes ({reduction:.1f}% reduction)')
    print(f'  Done.')


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    keep_last = 15
    for i, arg in enumerate(sys.argv):
        if arg == '--keep' and i+1 < len(sys.argv):
            keep_last = int(sys.argv[i+1])

    compress(dry_run=dry_run, keep_last=keep_last)
