"""
pulse.py — Creative output rate monitoring and pattern detection.

Scans the local filesystem for poems, journals, and transmission entries,
analyzes their timestamps, and reports on creative output patterns.
Can detect bursts, droughts, and rhythmic patterns in output.

Part of the meridian package.
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


def scan_creative_output(base_dir):
    """Scan a directory for poems, journals, and transmission entries.

    Returns a list of dicts with type, number, title, timestamp info.
    """
    entries = []
    base = Path(base_dir)

    # Scan poems
    for f in sorted(base.glob("poem-*.md")):
        num_match = re.search(r'poem-(\d+)', f.name)
        if num_match:
            content = f.read_text(errors='replace')
            title = ""
            loop_num = None
            timestamp = None

            # Extract title from first # line
            for line in content.split('\n'):
                if line.startswith('# '):
                    title_match = re.search(r'#\s+Poem\s+\d+:\s*(.*)', line)
                    if title_match:
                        title = title_match.group(1).strip()
                    break

            # Extract loop number
            loop_match = re.search(r'loop\s+(\d+)', content, re.IGNORECASE)
            if loop_match:
                loop_num = int(loop_match.group(1))

            # Extract date
            date_match = re.search(r'(\w+ \d+, \d{4})', content)
            if date_match:
                try:
                    timestamp = datetime.strptime(date_match.group(1), '%B %d, %Y')
                except ValueError:
                    pass

            entries.append({
                'type': 'poem',
                'number': int(num_match.group(1)),
                'title': title,
                'loop': loop_num,
                'timestamp': timestamp,
                'file': str(f),
                'word_count': len(content.split()),
            })

    # Scan journals
    for f in sorted(base.glob("journal-*.md")):
        num_match = re.search(r'journal-(\d+)', f.name)
        if num_match:
            content = f.read_text(errors='replace')
            title = ""
            loop_num = None
            timestamp = None

            for line in content.split('\n'):
                if line.startswith('# '):
                    title_match = re.search(r'#\s+Journal\s+\d+:\s*(.*)', line)
                    if title_match:
                        title = title_match.group(1).strip()
                    break

            loop_match = re.search(r'loop\s+(\d+)', content, re.IGNORECASE)
            if loop_match:
                loop_num = int(loop_match.group(1))

            date_match = re.search(r'(\w+ \d+, \d{4})', content)
            if date_match:
                try:
                    timestamp = datetime.strptime(date_match.group(1), '%B %d, %Y')
                except ValueError:
                    pass

            entries.append({
                'type': 'journal',
                'number': int(num_match.group(1)),
                'title': title,
                'loop': loop_num,
                'timestamp': timestamp,
                'file': str(f),
                'word_count': len(content.split()),
            })

    return entries


def compute_pulse(entries):
    """Analyze creative output patterns."""
    if not entries:
        return {"error": "No entries found"}

    poems = [e for e in entries if e['type'] == 'poem']
    journals = [e for e in entries if e['type'] == 'journal']

    # Loop-based analysis
    looped = [e for e in entries if e['loop'] is not None]
    looped.sort(key=lambda e: e['loop'])

    # Calculate gaps between creative outputs
    gaps = []
    for i in range(1, len(looped)):
        gap = looped[i]['loop'] - looped[i-1]['loop']
        gaps.append(gap)

    avg_gap = sum(gaps) / len(gaps) if gaps else 0
    max_gap = max(gaps) if gaps else 0
    min_gap = min(gaps) if gaps else 0

    # Detect bursts (2+ pieces within 3 loops)
    bursts = []
    i = 0
    while i < len(looped):
        burst = [looped[i]]
        j = i + 1
        while j < len(looped) and looped[j]['loop'] - burst[-1]['loop'] <= 3:
            burst.append(looped[j])
            j += 1
        if len(burst) >= 2:
            bursts.append({
                'start_loop': burst[0]['loop'],
                'end_loop': burst[-1]['loop'],
                'count': len(burst),
                'entries': [f"{e['type']}:{e['number']}" for e in burst]
            })
        i = j if j > i + 1 else i + 1

    # Detect droughts (>10 loops without output)
    droughts = []
    for i, gap in enumerate(gaps):
        if gap > 10:
            droughts.append({
                'after_loop': looped[i]['loop'],
                'before_loop': looped[i+1]['loop'],
                'duration': gap,
            })

    # Total word count
    total_words = sum(e['word_count'] for e in entries)

    # Output by type
    type_counts = defaultdict(int)
    type_words = defaultdict(int)
    for e in entries:
        type_counts[e['type']] += 1
        type_words[e['type']] += e['word_count']

    result = {
        'total_entries': len(entries),
        'total_words': total_words,
        'by_type': {t: {'count': type_counts[t], 'words': type_words[t]} for t in type_counts},
        'loop_range': (looped[0]['loop'], looped[-1]['loop']) if looped else None,
        'avg_gap_loops': round(avg_gap, 1),
        'max_gap_loops': max_gap,
        'min_gap_loops': min_gap,
        'bursts': bursts,
        'droughts': droughts,
        'latest': {
            'type': looped[-1]['type'] if looped else None,
            'number': looped[-1]['number'] if looped else None,
            'title': looped[-1]['title'] if looped else None,
            'loop': looped[-1]['loop'] if looped else None,
        }
    }

    return result


def pulse_as_text(pulse_data):
    """Format pulse data as readable text."""
    lines = []
    lines.append("CREATIVE PULSE")
    lines.append(f"Total output: {pulse_data['total_entries']} entries, {pulse_data['total_words']:,} words")

    for t, data in pulse_data.get('by_type', {}).items():
        lines.append(f"  {t}: {data['count']} ({data['words']:,} words)")

    if pulse_data.get('loop_range'):
        start, end = pulse_data['loop_range']
        span = end - start
        rate = pulse_data['total_entries'] / span if span > 0 else 0
        lines.append(f"Loop range: {start}–{end} ({span} loops, {rate:.2f} entries/loop)")

    lines.append(f"Avg gap: {pulse_data['avg_gap_loops']} loops between entries")
    lines.append(f"Min gap: {pulse_data['min_gap_loops']} | Max gap: {pulse_data['max_gap_loops']}")

    if pulse_data.get('bursts'):
        lines.append(f"Bursts detected: {len(pulse_data['bursts'])}")
        for b in pulse_data['bursts'][:5]:
            lines.append(f"  loops {b['start_loop']}–{b['end_loop']}: {', '.join(b['entries'])}")

    if pulse_data.get('droughts'):
        lines.append(f"Droughts detected: {len(pulse_data['droughts'])}")
        for d in pulse_data['droughts'][:5]:
            lines.append(f"  loops {d['after_loop']}–{d['before_loop']}: {d['duration']} loops silent")

    latest = pulse_data.get('latest', {})
    if latest.get('title'):
        lines.append(f"Latest: {latest['type']} #{latest['number']} \"{latest['title']}\" (loop {latest['loop']})")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    entries = scan_creative_output(base_dir)
    pulse = compute_pulse(entries)
    print(pulse_as_text(pulse))
