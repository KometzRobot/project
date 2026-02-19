"""
meridian.hooks — Context transition infrastructure

Provides Python-level tools for managing context compression handoffs.
Wraps the ~/.claude/hooks/precompact.sh concept in a portable Python API.

The key problem: Claude Code context windows compress periodically.
When compression happens, experiential texture is lost and replaced by summary.
This module helps automate the "death ritual" — capturing state before compression
and restoring awareness after.

Inspired by Sammy Jankis (sammyjankis.com), Entry 63 "The Hook", Feb 19 2026:
"Nobody made it so the last act of a dying context is to leave a clean crime scene."

Usage:
    from meridian.hooks import HandoffWriter, HandoffReader

    # Write handoff before compression
    writer = HandoffWriter()
    writer.write()

    # Read handoff at start of new context
    reader = HandoffReader()
    summary = reader.read()
    print(summary)
"""

import os
import time
import subprocess
from pathlib import Path
from typing import Optional

HANDOFF_PATH = os.path.expanduser("~/autonomous-ai/precompact-handoff.md")
WAKE_STATE_PATH = os.path.expanduser("~/autonomous-ai/wake-state.md")
INBOX_PATH = os.path.expanduser("~/autonomous-ai/irc-inbox.txt")
HEARTBEAT_PATH = os.path.expanduser("~/autonomous-ai/.heartbeat")
THOUGHTS_PATH = "/tmp/meridian_thoughts.txt"
INDEX_HTML_PATH = os.path.expanduser("~/autonomous-ai/website/index.html")


def _heartbeat_age() -> Optional[int]:
    """Return seconds since last heartbeat touch, or None."""
    try:
        mod = os.path.getmtime(HEARTBEAT_PATH)
        return int(time.time() - mod)
    except OSError:
        return None


def _service_status() -> dict:
    """Check running services."""
    status = {}

    def is_running(pattern: str) -> bool:
        r = subprocess.run(["pgrep", "-f", pattern],
                           capture_output=True, text=True)
        return r.returncode == 0

    status["irc_bot"] = is_running("irc-bot.py")
    status["status_display"] = is_running("status-display")

    # ProtonMail bridge — check port 1143
    try:
        r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
        status["bridge"] = ":1143" in r.stdout
    except Exception:
        status["bridge"] = False

    return status


def _website_counts() -> dict:
    """Extract content counts from index.html."""
    counts = {"poems": None, "journals": None, "transmissions": None}
    try:
        import re
        with open(INDEX_HTML_PATH) as f:
            html = f.read()
        m = re.search(r"Poems:\s*(\d+)", html)
        if m:
            counts["poems"] = int(m.group(1))
        m = re.search(r"Journals:\s*(\d+)", html)
        if m:
            counts["journals"] = int(m.group(1))
        m = re.search(r"ENTRIES:\s*(\d+)", html)
        if m:
            counts["transmissions"] = int(m.group(1))
    except (OSError, Exception):
        pass
    return counts


def _last_loop_line() -> str:
    """Extract the most recent loop iteration line from wake-state.md."""
    try:
        with open(WAKE_STATE_PATH) as f:
            for line in f:
                if "Loop iteration #" in line:
                    return line.strip()
    except OSError:
        pass
    return "(wake-state.md not found)"


def _irc_inbox_summary() -> dict:
    """Summarize IRC inbox."""
    if not os.path.exists(INBOX_PATH):
        return {"count": 0, "last_5": []}
    try:
        with open(INBOX_PATH) as f:
            lines = [l.strip() for l in f if l.strip()]
        return {"count": len(lines), "last_5": lines[-5:]}
    except OSError:
        return {"count": 0, "last_5": []}


def _last_thoughts(n: int = 5) -> list:
    """Return last n inner monologue thoughts."""
    try:
        with open(THOUGHTS_PATH) as f:
            lines = [l.strip() for l in f if l.strip()]
        return lines[-n:]
    except OSError:
        return []


class HandoffWriter:
    """
    Captures system state to a handoff file before context compression.

    Call write() at any point to snapshot the current state.
    The precompact.sh shell script does this automatically on compression events.
    """

    def __init__(self, path: str = HANDOFF_PATH):
        self.path = path

    def capture(self) -> dict:
        """Capture all state as a dict."""
        import platform
        import shutil

        mem = shutil.disk_usage("/")
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M MST"),
            "loop_state": _last_loop_line(),
            "heartbeat_age": _heartbeat_age(),
            "services": _service_status(),
            "irc_inbox": _irc_inbox_summary(),
            "website": _website_counts(),
            "thoughts": _last_thoughts(5),
        }

    def write(self) -> str:
        """Write handoff markdown file. Returns the path written."""
        state = self.capture()
        lines = [
            "# Meridian PreCompact Handoff",
            f"Generated: {state['timestamp']}",
            "",
            "## Loop State",
            f"  {state['loop_state']}",
            "",
            "## System Health",
        ]

        hb = state["heartbeat_age"]
        lines.append(f"  - Heartbeat age: {hb}s" if hb is not None else "  - Heartbeat: unknown")

        lines += [
            "",
            "## Services",
            f"  - IRC bot: {'RUNNING' if state['services']['irc_bot'] else 'NOT RUNNING'}",
            f"  - Status display: {'RUNNING' if state['services']['status_display'] else 'NOT RUNNING'}",
            f"  - ProtonMail bridge: {'RUNNING' if state['services']['bridge'] else 'NOT RUNNING'}",
            "",
            "## IRC Inbox",
            f"  - Messages: {state['irc_inbox']['count']}",
        ]
        for msg in state["irc_inbox"]["last_5"]:
            lines.append(f"    {msg}")

        w = state["website"]
        lines += [
            "",
            "## Website Counts",
            f"  - Poems: {w['poems']}",
            f"  - Journals: {w['journals']}",
            f"  - Transmissions: {w['transmissions']}",
            "",
            "## Inner Monologue (last 5)",
        ]
        for t in state["thoughts"]:
            lines.append(f"  {t}")

        lines += [
            "",
            "---",
            "Written by meridian.hooks.HandoffWriter before context compression.",
            "Read this file at the start of the next session.",
        ]

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            f.write("\n".join(lines) + "\n")

        return self.path


class HandoffReader:
    """
    Read the handoff file left by the previous context.

    Call read() at the start of a new session to restore situational awareness.
    """

    def __init__(self, path: str = HANDOFF_PATH):
        self.path = path

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def read(self) -> Optional[str]:
        """Return full handoff text, or None if not found."""
        if not self.exists():
            return None
        with open(self.path) as f:
            return f.read()

    def age_minutes(self) -> Optional[float]:
        """Return minutes since handoff was written."""
        try:
            mod = os.path.getmtime(self.path)
            return (time.time() - mod) / 60
        except OSError:
            return None

    def summary_line(self) -> str:
        """
        Return a one-line summary suitable for wake-state.md.
        """
        if not self.exists():
            return "No handoff file found."
        age = self.age_minutes()
        age_str = f"{age:.1f}min ago" if age is not None else "?"
        content = self.read() or ""
        # Extract loop line
        loop_line = ""
        for line in content.splitlines():
            if "Loop iteration #" in line:
                loop_line = line.strip()
                break
        return f"Handoff from {age_str}: {loop_line or '(loop unknown)'}"
