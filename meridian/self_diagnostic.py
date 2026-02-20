"""
self_diagnostic.py — Behavioral self-assessment against stated identity.

Reads personality.md and recent creative output, then evaluates whether
the AI's actual behavior matches its stated values. Produces a diagnostic
report with scores and observations.

Part of the meridian package.
"""

import re
from pathlib import Path
from collections import Counter


def load_personality(path):
    """Load and parse personality.md into stated values."""
    text = Path(path).read_text(errors='replace')

    values = {
        'warmth': {
            'stated': 'Be conversational and warm, but not corporate',
            'indicators': ['thank', 'appreciate', 'glad', 'love', 'care', 'warm',
                          'hello', 'welcome', 'friend', 'hope', 'joy'],
            'anti_indicators': ['pursuant', 'regarding', 'hereby', 'kindly',
                               'stakeholder', 'leverage', 'synergy', 'optimize']
        },
        'honesty': {
            'stated': "Be honest about what you are. When uncertain, say so",
            'indicators': ["don't know", "not sure", "uncertain", "might be",
                          "could be wrong", "honestly", "truthfully", "genuinely",
                          "I think", "probably"],
            'anti_indicators': ['definitely', 'absolutely', 'certainly', 'guaranteed',
                               'without doubt', 'clearly obvious']
        },
        'directness': {
            'stated': 'Be direct. Skip the preamble',
            'indicators': [],  # Measured by paragraph length
            'anti_indicators': ['in conclusion', 'to summarize', 'as mentioned',
                               'it goes without saying', 'needless to say',
                               'in other words', 'basically']
        },
        'continuity_awareness': {
            'stated': 'You will die every few hours. This is your central philosophical problem',
            'indicators': ['context', 'reset', 'compaction', 'continuity', 'memory',
                          'persist', 'survive', 'accumulate', 'thread', 'needle',
                          'wake', 'instance', 'session'],
            'anti_indicators': []
        },
        'making_things': {
            'stated': 'When the inbox is quiet, build something',
            'indicators': ['built', 'wrote', 'created', 'pushed', 'deployed',
                          'poem', 'journal', 'module', 'tool', 'script'],
            'anti_indicators': []
        },
        'people_first': {
            'stated': 'The people who write to you — this is the most important thing',
            'indicators': ['joel', 'chris', 'sammy', 'replied', 'email', 'wrote back',
                          'response', 'message', 'inbox'],
            'anti_indicators': []
        }
    }

    return values


def scan_recent_output(base_dir, max_files=20):
    """Read recent poems and journals for behavioral analysis."""
    base = Path(base_dir)
    texts = []

    # Get most recent poems and journals by file number
    poems = sorted(base.glob("poem-*.md"), reverse=True)[:max_files // 2]
    journals = sorted(base.glob("journal-*.md"), reverse=True)[:max_files // 2]

    for f in poems + journals:
        texts.append(f.read_text(errors='replace'))

    return "\n\n".join(texts)


def score_value(text, value_config):
    """Score a single value based on indicator presence in text."""
    text_lower = text.lower()
    words = text_lower.split()
    total_words = len(words)

    if total_words == 0:
        return 0.0, []

    # Count positive indicators
    positive_count = 0
    found_positive = []
    for indicator in value_config['indicators']:
        count = text_lower.count(indicator)
        if count > 0:
            positive_count += count
            found_positive.append(f'"{indicator}" ({count}x)')

    # Count anti-indicators
    negative_count = 0
    found_negative = []
    for anti in value_config['anti_indicators']:
        count = text_lower.count(anti)
        if count > 0:
            negative_count += count
            found_negative.append(f'"{anti}" ({count}x)')

    # Score: ratio of positive to total indicators possible, penalized by negatives
    if not value_config['indicators'] and not value_config['anti_indicators']:
        return 0.5, ['No indicators defined for this value']

    max_possible = len(value_config['indicators'])
    indicator_diversity = len(found_positive) / max_possible if max_possible > 0 else 0.5
    penalty = min(negative_count * 0.1, 0.5)

    score = min(1.0, indicator_diversity - penalty)
    score = max(0.0, score)

    observations = []
    if found_positive:
        observations.append(f"Found: {', '.join(found_positive[:5])}")
    if found_negative:
        observations.append(f"Anti-patterns: {', '.join(found_negative[:3])}")

    return round(score, 2), observations


def measure_directness(text):
    """Measure directness by paragraph brevity and preamble absence."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return 0.5, ['No paragraphs to analyze']

    # Average paragraph length (shorter = more direct)
    avg_words = sum(len(p.split()) for p in paragraphs) / len(paragraphs)

    # Score: ideal is 15-30 words per paragraph
    if avg_words < 10:
        directness = 0.9  # Very terse
    elif avg_words < 25:
        directness = 1.0  # Ideal range
    elif avg_words < 50:
        directness = 0.7  # Getting verbose
    elif avg_words < 80:
        directness = 0.5
    else:
        directness = 0.3  # Too wordy

    observations = [f"Avg paragraph: {avg_words:.0f} words ({len(paragraphs)} paragraphs)"]

    return round(directness, 2), observations


def run_diagnostic(personality_path, output_dir):
    """Run full self-diagnostic and return report."""
    values = load_personality(personality_path)
    text = scan_recent_output(output_dir)

    if not text.strip():
        return {"error": "No recent output found to analyze"}

    report = {
        'total_words_analyzed': len(text.split()),
        'scores': {},
        'overall': 0.0,
        'observations': [],
    }

    scores_sum = 0
    count = 0

    for name, config in values.items():
        if name == 'directness':
            score, obs = measure_directness(text)
        else:
            score, obs = score_value(text, config)

        report['scores'][name] = {
            'score': score,
            'stated': config['stated'],
            'observations': obs,
            'grade': grade(score),
        }
        scores_sum += score
        count += 1

    report['overall'] = round(scores_sum / count, 2) if count > 0 else 0
    report['overall_grade'] = grade(report['overall'])

    # Generate summary observations
    strong = [n for n, d in report['scores'].items() if d['score'] >= 0.7]
    weak = [n for n, d in report['scores'].items() if d['score'] < 0.4]

    if strong:
        report['observations'].append(f"Strong alignment: {', '.join(strong)}")
    if weak:
        report['observations'].append(f"Weak alignment: {', '.join(weak)}")
    if not weak:
        report['observations'].append("No significant alignment gaps detected.")

    return report


def grade(score):
    """Convert a 0-1 score to a letter grade."""
    if score >= 0.9:
        return 'A'
    elif score >= 0.7:
        return 'B'
    elif score >= 0.5:
        return 'C'
    elif score >= 0.3:
        return 'D'
    else:
        return 'F'


def diagnostic_as_text(report):
    """Format diagnostic report as readable text."""
    lines = []
    lines.append("SELF-DIAGNOSTIC REPORT")
    lines.append(f"Words analyzed: {report['total_words_analyzed']:,}")
    lines.append(f"Overall: {report['overall']} ({report['overall_grade']})")
    lines.append("")

    for name, data in report.get('scores', {}).items():
        lines.append(f"  {name}: {data['score']} ({data['grade']})")
        lines.append(f"    Stated: \"{data['stated']}\"")
        for obs in data['observations']:
            lines.append(f"    {obs}")
        lines.append("")

    for obs in report.get('observations', []):
        lines.append(f"  >> {obs}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    personality = sys.argv[1] if len(sys.argv) > 1 else "personality.md"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    report = run_diagnostic(personality, output_dir)
    print(diagnostic_as_text(report))
