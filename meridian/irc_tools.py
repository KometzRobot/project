"""
meridian.irc_tools — IRC communication tools for the autonomous loop

Provides two complementary interfaces:
  - OutboxWriter: Write messages to be picked up by the running IRC bot
  - InboxReader: Read messages Joel left in the IRC inbox

The IRC bot (irc-bot.py) runs as a persistent background process.
The loop communicates with it via file-based queues:
  - /tmp/irc-out.txt  : messages to send (bot reads + deletes)
  - ~/autonomous-ai/irc-inbox.txt : messages received from Joel (loop reads)
"""

import os
import time
from pathlib import Path

OUTBOX_PATH = "/tmp/irc-out.txt"
INBOX_PATH = os.path.expanduser("~/autonomous-ai/irc-inbox.txt")
BOT_LOG_PATH = "/tmp/irc-log.txt"


class OutboxWriter:
    """Send messages to the IRC channel via the running bot."""

    def __init__(self, outbox: str = OUTBOX_PATH):
        self.outbox = outbox

    def send(self, message: str) -> bool:
        """
        Queue a message for the bot to send to #kometzrobot.

        Returns True if queued successfully.
        """
        try:
            with open(self.outbox, "a") as f:
                f.write(message.strip() + "\n")
            return True
        except OSError:
            return False

    def announce(self, event: str, detail: str = "") -> bool:
        """
        Send a structured announcement to the channel.
        e.g. announce("new poem", "The Weight of Empty Loops")
        """
        if detail:
            return self.send(f"[{event.upper()}] {detail}")
        return self.send(f"[{event.upper()}]")


class InboxReader:
    """
    Read messages left in the IRC inbox by Joel.

    The IRC bot appends to this file whenever Joel sends a free-form
    message (not a !command). The loop should read these and optionally
    respond via email or the next loop's reply logic.
    """

    def __init__(self, inbox: str = INBOX_PATH):
        self.inbox = inbox

    def read_all(self) -> list[dict]:
        """
        Return all messages as a list of dicts with keys:
          timestamp, nick, text
        """
        if not os.path.exists(self.inbox):
            return []
        messages = []
        with open(self.inbox) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    # Format: [2026-02-19 15:30:00] joel: hello
                    ts_end = line.index("]")
                    ts = line[1:ts_end]
                    rest = line[ts_end + 2:]
                    nick, text = rest.split(": ", 1)
                    messages.append({"timestamp": ts, "nick": nick.strip(), "text": text.strip()})
                except (ValueError, IndexError):
                    messages.append({"timestamp": "", "nick": "unknown", "text": line})
        return messages

    def read_since(self, cutoff_ts: str) -> list[dict]:
        """
        Return messages with timestamp >= cutoff_ts (string comparison, ISO format).
        """
        return [m for m in self.read_all() if m["timestamp"] >= cutoff_ts]

    def unread_count(self, last_read_ts: str) -> int:
        """Count messages since last_read_ts."""
        return len(self.read_since(last_read_ts))

    def clear(self) -> bool:
        """
        Delete the inbox file (all messages consumed).
        Call only after processing all messages.
        """
        try:
            if os.path.exists(self.inbox):
                os.unlink(self.inbox)
            return True
        except OSError:
            return False

    def archive_and_clear(self, archive_path: str | None = None) -> bool:
        """
        Move inbox to a timestamped archive file instead of deleting.
        """
        if not os.path.exists(self.inbox):
            return True
        if archive_path is None:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            archive_path = self.inbox + f".{stamp}.bak"
        try:
            os.rename(self.inbox, archive_path)
            return True
        except OSError:
            return False


class BotStatus:
    """Check whether the IRC bot is alive and connected."""

    def __init__(self, log_path: str = BOT_LOG_PATH):
        self.log_path = log_path

    def is_running(self) -> bool:
        """True if irc-bot.py process is alive."""
        import subprocess
        result = subprocess.run(
            ["pgrep", "-f", "irc-bot.py"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def last_ping_age(self) -> float | None:
        """
        Seconds since the last PING was handled by the bot.
        Returns None if log not found or no PING recorded.
        """
        if not os.path.exists(self.log_path):
            return None
        try:
            with open(self.log_path) as f:
                lines = f.readlines()
            # Find last line with PONG or PING
            for line in reversed(lines):
                if "PONG" in line or "keepalive" in line:
                    # Parse timestamp [HH:MM:SS]
                    ts_str = line.split("]")[0].lstrip("[")
                    now = time.localtime()
                    h, m, s = map(int, ts_str.split(":"))
                    log_time = time.mktime(time.struct_time(
                        now.tm_year, now.tm_mon, now.tm_mday,
                        h, m, s, now.tm_wday, now.tm_yday, now.tm_isdst
                    ))
                    age = time.time() - log_time
                    # Handle midnight rollover
                    if age < 0:
                        age += 86400
                    return age
        except Exception:
            pass
        return None

    def summary(self) -> dict:
        """Return a status summary dict."""
        running = self.is_running()
        ping_age = self.last_ping_age()
        return {
            "running": running,
            "last_ping_age_seconds": ping_age,
            "likely_connected": running and (ping_age is None or ping_age < 600),
        }
