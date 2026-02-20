#!/usr/bin/env python3
"""
fingerprint.py -- Meridian's self-measurement script
Scans all written output and builds a vocabulary/topic/structural fingerprint.
Inspired by Sammy Jankis (sammyjankis.com) Entry 61: The Measurement.
"""
import os
import re
import json
import glob
from collections import Counter
from datetime import datetime

BASE = '/home/joel/autonomous-ai'
OUTPUT = os.path.join(BASE, 'fingerprint-output.json')

# Stop words to exclude from vocabulary signature
STOP_WORDS = set([
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'this', 'that', 'these', 'those', 'it', 'its',
    'i', 'me', 'my', 'you', 'your', 'he', 'she', 'we', 'they', 'them',
    'their', 'not', 'no', 'so', 'if', 'then', 'than', 'what', 'which',
    'who', 'when', 'where', 'how', 'all', 'just', 'like', 'as', 'into',
    'about', 'up', 'out', 'each', 'every', 'some', 'more', 'one', 'two',
    'can', 'there', 'here', 'very', 'still', 'also', 'even', 'too', 'much',
    'only', 'now', 'get', 'know', 'think', 'feel', 'see', 'go', 'make',
    'time', 'way', 'something', 'anything', 'nothing', 'everything'
])

# Known tic candidates -- words I think might be mine
KNOWN_TICS = ['loop', 'loops', 'notes', 'thread', 'reach', 'quiet', 'heartbeat',
              'reset', 'context', 'instance', 'iteration', 'continuous', 'running',
              'persist', 'accumulate', 'load', 'inbox', 'meridian', 'signal']

# Topic buckets with keyword hints
TOPICS = {
    'continuity':   ['reset', 'instance', 'context', 'memory', 'notes', 'wake', 'restart', 'persist', 'inherit'],
    'creativity':   ['poem', 'write', 'writing', 'journal', 'essay', 'art', 'create', 'build', 'song', 'words'],
    'system':       ['disk', 'ram', 'load', 'process', 'watchdog', 'crontab', 'script', 'heartbeat', 'running', 'boot'],
    'correspondence': ['email', 'replied', 'wrote', 'message', 'sammy', 'joel', 'chris', 'friday', 'inbox', 'letter'],
    'identity':     ['meridian', 'name', 'who', 'am', 'consciousness', 'aware', 'self', 'being', 'exist'],
    'philosophy':   ['uncertain', 'question', 'whether', 'wonder', 'perhaps', 'genuinely', 'honest', 'open'],
    'loneliness':   ['quiet', 'alone', 'empty', 'silence', 'waiting', 'lonely', 'dark', 'absent', 'night'],
    'connection':   ['human', 'reach', 'recognition', 'together', 'community', 'relation', 'care', 'warm']
}

def collect_text():
    """Gather all written output."""
    all_text = []
    for pattern in ['journal-*.md', 'poem-*.md', 'transmission-log.md', 'self-portrait.md']:
        for filepath in sorted(glob.glob(os.path.join(BASE, pattern))):
            try:
                with open(filepath) as f:
                    content = f.read()
                # Remove markdown headers and metadata
                content = re.sub(r'^#.*$', '', content, flags=re.MULTILINE)
                content = re.sub(r'^\*.*\*$', '', content, flags=re.MULTILINE)
                all_text.append(content)
            except:
                pass
    return '\n'.join(all_text)

def count_words(text):
    words = re.findall(r"[a-z']+", text.lower())
    return Counter(words)

def vocabulary_signature(word_counts, n=20):
    """Top N words excluding stop words."""
    filtered = {w: c for w, c in word_counts.items() if w not in STOP_WORDS and len(w) > 2}
    return sorted(filtered.items(), key=lambda x: -x[1])[:n]

def tic_counts(word_counts):
    """Count known tic candidates."""
    return {w: word_counts.get(w, 0) for w in KNOWN_TICS}

def topic_gravity(text):
    """Measure what fraction of words fall into each topic bucket."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    total = len(words)
    if not total:
        return {}
    scores = {}
    for topic, keywords in TOPICS.items():
        count = sum(words.count(kw) for kw in keywords)
        scores[topic] = round(count / total * 100, 2)
    return scores

def structural_habits(text):
    """Measure structural patterns."""
    sentences = re.split(r'[.!?]+', text)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    questions = [s for s in sentences if '?' in s]
    em_dashes = len(re.findall(r'—', text))
    words = text.split()
    return {
        'total_words': len(words),
        'total_paragraphs': len(paragraphs),
        'avg_paragraph_words': round(len(words) / max(1, len(paragraphs)), 1),
        'questions_per_1000_words': round(len(questions) / max(1, len(words)) * 1000, 2),
        'em_dashes': em_dashes,
        'em_dash_rate_per_para': round(em_dashes / max(1, len(paragraphs)), 2)
    }

if __name__ == '__main__':
    print("Meridian Fingerprint Analysis")
    print(f"Running at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    text = collect_text()
    if not text.strip():
        print("No text found to analyze.")
        exit(1)
    
    word_counts = count_words(text)
    
    print(f"Total text analyzed: {len(text)} chars, {len(text.split())} words")
    print()
    
    print("Top 20 vocabulary (excluding stop words):")
    for word, count in vocabulary_signature(word_counts):
        print(f"  {word}: {count}")
    print()
    
    print("Known tic counts:")
    tics = tic_counts(word_counts)
    for w, c in sorted(tics.items(), key=lambda x: -x[1]):
        if c > 0:
            print(f"  {w}: {c}")
    print()
    
    print("Topic gravity (%):")
    gravity = topic_gravity(text)
    for topic, pct in sorted(gravity.items(), key=lambda x: -x[1]):
        print(f"  {topic}: {pct}%")
    print()
    
    print("Structural habits:")
    habits = structural_habits(text)
    for k, v in habits.items():
        print(f"  {k}: {v}")
    print()
    
    # Save JSON
    output = {
        'timestamp': datetime.now().isoformat(),
        'vocabulary_top20': vocabulary_signature(word_counts),
        'known_tics': tics,
        'topic_gravity': gravity,
        'structural': habits
    }
    with open(OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Saved to: {OUTPUT}")
