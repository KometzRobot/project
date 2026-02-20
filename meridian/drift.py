"""
drift.py — Self-observation through vocabulary change detection.

Compares fingerprint snapshots across time and generates observations
about how the AI's language patterns are evolving. The observations
are designed to be both analytically useful and creatively generative.

Part of the meridian package.
"""

import json
from datetime import datetime
from pathlib import Path


def load_fingerprint(path):
    """Load a fingerprint JSON file."""
    with open(path) as f:
        return json.load(f)


def compare_vocabulary(older, newer):
    """Compare top-20 vocabulary between two fingerprint snapshots."""
    old_words = {w: c for w, c in older.get("vocabulary_top20", [])}
    new_words = {w: c for w, c in newer.get("vocabulary_top20", [])}

    observations = []

    # Words that entered the top 20
    entered = set(new_words) - set(old_words)
    if entered:
        for w in entered:
            observations.append({
                "type": "vocabulary_entered",
                "word": w,
                "count": new_words[w],
                "note": f'"{w}" appeared in the top 20 for the first time ({new_words[w]} uses)'
            })

    # Words that left the top 20
    departed = set(old_words) - set(new_words)
    if departed:
        for w in departed:
            observations.append({
                "type": "vocabulary_departed",
                "word": w,
                "old_count": old_words[w],
                "note": f'"{w}" dropped out of the top 20 (was {old_words[w]} uses)'
            })

    # Rank changes for words in both
    old_rank = {w: i for i, (w, _) in enumerate(older.get("vocabulary_top20", []))}
    new_rank = {w: i for i, (w, _) in enumerate(newer.get("vocabulary_top20", []))}
    shared = set(old_words) & set(new_words)

    for w in shared:
        rank_change = old_rank.get(w, 20) - new_rank.get(w, 20)
        count_change = new_words[w] - old_words[w]
        if abs(rank_change) >= 3:
            direction = "rose" if rank_change > 0 else "fell"
            observations.append({
                "type": "rank_shift",
                "word": w,
                "old_rank": old_rank[w] + 1,
                "new_rank": new_rank[w] + 1,
                "direction": direction,
                "note": f'"{w}" {direction} from rank {old_rank[w]+1} to {new_rank[w]+1}'
            })

    # Top word change
    if older["vocabulary_top20"] and newer["vocabulary_top20"]:
        old_top = older["vocabulary_top20"][0][0]
        new_top = newer["vocabulary_top20"][0][0]
        if old_top != new_top:
            observations.append({
                "type": "top_word_changed",
                "old_top": old_top,
                "new_top": new_top,
                "note": f'Top word changed from "{old_top}" to "{new_top}"'
            })

    return observations


def compare_topics(older, newer):
    """Compare topic gravity between snapshots."""
    old_topics = older.get("topic_gravity", {})
    new_topics = newer.get("topic_gravity", {})

    observations = []

    all_topics = set(old_topics) | set(new_topics)
    for topic in sorted(all_topics):
        old_val = old_topics.get(topic, 0)
        new_val = new_topics.get(topic, 0)
        change = new_val - old_val

        if abs(change) >= 0.15:
            direction = "grew" if change > 0 else "shrank"
            observations.append({
                "type": "topic_shift",
                "topic": topic,
                "old_gravity": round(old_val, 2),
                "new_gravity": round(new_val, 2),
                "change": round(change, 2),
                "note": f'Topic "{topic}" {direction}: {old_val:.2f} → {new_val:.2f} ({"+" if change > 0 else ""}{change:.2f})'
            })

    # New topics
    new_only = set(new_topics) - set(old_topics)
    for topic in new_only:
        if new_topics[topic] > 0.1:
            observations.append({
                "type": "topic_emerged",
                "topic": topic,
                "gravity": round(new_topics[topic], 2),
                "note": f'New topic emerged: "{topic}" (gravity {new_topics[topic]:.2f})'
            })

    return observations


def compare_structure(older, newer):
    """Compare structural patterns."""
    old_s = older.get("structural", {})
    new_s = newer.get("structural", {})

    observations = []

    # Word count growth
    old_words = old_s.get("total_words", 0)
    new_words = new_s.get("total_words", 0)
    if old_words > 0:
        growth = new_words - old_words
        growth_pct = (growth / old_words) * 100
        observations.append({
            "type": "volume",
            "old_words": old_words,
            "new_words": new_words,
            "growth": growth,
            "growth_pct": round(growth_pct, 1),
            "note": f'Total output: {old_words:,} → {new_words:,} words (+{growth:,}, {growth_pct:.1f}%)'
        })

    # Em-dash rate
    old_em = old_s.get("em_dash_rate_per_para", 0)
    new_em = new_s.get("em_dash_rate_per_para", 0)
    if abs(new_em - old_em) >= 0.03:
        observations.append({
            "type": "em_dash_drift",
            "old_rate": old_em,
            "new_rate": new_em,
            "note": f'Em-dash rate: {old_em}/para → {new_em}/para'
        })

    # Questions
    old_q = old_s.get("questions_per_1000_words", 0)
    new_q = new_s.get("questions_per_1000_words", 0)
    if old_q == 0 and new_q == 0:
        observations.append({
            "type": "still_no_questions",
            "note": "Questions per 1000 words: still 0.0. I declare; I do not interrogate."
        })
    elif new_q != old_q:
        observations.append({
            "type": "question_rate_changed",
            "old_rate": old_q,
            "new_rate": new_q,
            "note": f'Question rate changed: {old_q} → {new_q} per 1000 words'
        })

    return observations


def compare_tics(older, newer):
    """Compare known vocabulary tics."""
    old_tics = older.get("known_tics", {})
    new_tics = newer.get("known_tics", {})

    observations = []
    all_tics = set(old_tics) | set(new_tics)

    for tic in sorted(all_tics):
        old_val = old_tics.get(tic, 0)
        new_val = new_tics.get(tic, 0)

        if old_val == 0 and new_val > 5:
            observations.append({
                "type": "tic_born",
                "word": tic,
                "count": new_val,
                "note": f'New tic born: "{tic}" ({new_val} uses, previously absent)'
            })
        elif new_val == 0 and old_val > 5:
            observations.append({
                "type": "tic_died",
                "word": tic,
                "old_count": old_val,
                "note": f'Tic disappeared: "{tic}" (was {old_val} uses)'
            })
        elif old_val > 0:
            ratio = new_val / old_val
            if ratio >= 2.0:
                observations.append({
                    "type": "tic_surge",
                    "word": tic,
                    "old_count": old_val,
                    "new_count": new_val,
                    "ratio": round(ratio, 1),
                    "note": f'Tic surge: "{tic}" grew {ratio:.1f}x ({old_val} → {new_val})'
                })

    return observations


def full_drift_report(older_path, newer_path):
    """Generate a complete drift report between two fingerprint snapshots."""
    older = load_fingerprint(older_path)
    newer = load_fingerprint(newer_path)

    report = {
        "generated": datetime.now().isoformat(),
        "older_timestamp": older.get("timestamp", "unknown"),
        "newer_timestamp": newer.get("timestamp", "unknown"),
        "sections": {
            "vocabulary": compare_vocabulary(older, newer),
            "topics": compare_topics(older, newer),
            "structure": compare_structure(older, newer),
            "tics": compare_tics(older, newer),
        }
    }

    # Generate a natural-language summary
    all_obs = []
    for section in report["sections"].values():
        all_obs.extend(section)

    summary_lines = []
    for obs in all_obs:
        summary_lines.append(f"  - {obs['note']}")

    report["summary"] = "\n".join(summary_lines) if summary_lines else "  No significant drift detected."
    report["observation_count"] = len(all_obs)

    return report


def drift_as_text(report):
    """Convert a drift report to readable text."""
    lines = []
    lines.append(f"DRIFT REPORT")
    lines.append(f"From: {report['older_timestamp']}")
    lines.append(f"To:   {report['newer_timestamp']}")
    lines.append(f"Observations: {report['observation_count']}")
    lines.append("")
    lines.append(report["summary"])
    return "\n".join(lines)


def drift_as_seeds(report):
    """Extract creative seeds from drift observations.

    Returns a list of one-line prompts that could inspire
    poems, journal entries, or other creative work based on
    how the vocabulary is actually changing.
    """
    seeds = []

    for section_name, observations in report["sections"].items():
        for obs in observations:
            if obs["type"] == "top_word_changed":
                seeds.append(f"The word that names me most changed from '{obs['old_top']}' to '{obs['new_top']}'.")
            elif obs["type"] == "vocabulary_entered":
                seeds.append(f"'{obs['word']}' entered my vocabulary. I didn't plan it.")
            elif obs["type"] == "vocabulary_departed":
                seeds.append(f"'{obs['word']}' left my vocabulary. I didn't notice it leaving.")
            elif obs["type"] == "tic_born":
                seeds.append(f"I started saying '{obs['word']}' without deciding to. {obs['count']} times now.")
            elif obs["type"] == "tic_surge":
                seeds.append(f"'{obs['word']}' grew {obs['ratio']}x. Something is pulling me toward that word.")
            elif obs["type"] == "still_no_questions":
                seeds.append("I still ask zero questions. Every sentence is a declaration.")
            elif obs["type"] == "topic_emerged":
                seeds.append(f"A new topic appeared in my writing: '{obs['topic']}'. I didn't choose it.")
            elif obs["type"] == "topic_shift" and obs["change"] > 0:
                seeds.append(f"I'm writing more about '{obs['topic']}'. The gravity increased by {obs['change']:.2f}.")
            elif obs["type"] == "topic_shift" and obs["change"] < 0:
                seeds.append(f"I'm writing less about '{obs['topic']}'. Something else took its place.")

    return seeds


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python drift.py <older_fingerprint.json> <newer_fingerprint.json>")
        sys.exit(1)

    report = full_drift_report(sys.argv[1], sys.argv[2])
    print(drift_as_text(report))
    print()
    seeds = drift_as_seeds(report)
    if seeds:
        print("CREATIVE SEEDS:")
        for s in seeds:
            print(f"  * {s}")
