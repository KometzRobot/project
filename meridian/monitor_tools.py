"""
meridian.monitor_tools — Web change detection and URL monitoring

Watches URLs for content changes between loop iterations.
Stores checksums in a local state file so changes persist
across context resets.

Usage:
    monitor = WebMonitor()
    monitor.add('sammy', 'https://sammyjankis.com/journal.html')
    monitor.add('weather', 'https://wttr.in/Calgary?format=3')

    changes = monitor.check_all()
    for url_id, change in changes.items():
        if change['changed']:
            print(f"{url_id} changed!")
"""

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

DEFAULT_STATE_FILE = os.path.expanduser("~/autonomous-ai/monitor-state.json")
DEFAULT_USER_AGENT = "KometzRobot/1.0 (kometzrobot@proton.me)"


def _fetch(url: str, timeout: int = 15) -> str:
    """Fetch URL content as text."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class WebMonitor:
    """
    Track URLs for content changes.

    State is persisted to a JSON file so changes are detected
    correctly across loop iterations and context resets.
    """

    def __init__(self, state_file: str = DEFAULT_STATE_FILE):
        self.state_file = state_file
        self._state: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"urls": {}}

    def _save(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self._state, f, indent=2)

    def add(self, url_id: str, url: str, description: str = "") -> dict:
        """
        Register a URL to monitor.

        Does an initial fetch to establish baseline.
        Returns the initial state entry.
        """
        try:
            content = _fetch(url)
            checksum = _checksum(content)
            entry = {
                "url": url,
                "description": description,
                "checksum": checksum,
                "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_changed": time.strftime("%Y-%m-%d %H:%M:%S"),
                "change_count": 0,
                "content_preview": content[:200],
                "error": None,
            }
        except Exception as e:
            entry = {
                "url": url,
                "description": description,
                "checksum": None,
                "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_changed": None,
                "change_count": 0,
                "content_preview": "",
                "error": str(e),
            }
        self._state["urls"][url_id] = entry
        self._save()
        return entry

    def remove(self, url_id: str) -> bool:
        """Remove a URL from monitoring."""
        if url_id in self._state["urls"]:
            del self._state["urls"][url_id]
            self._save()
            return True
        return False

    def list_urls(self) -> dict:
        """Return all monitored URLs and their current state."""
        return dict(self._state["urls"])

    def check(self, url_id: str) -> dict:
        """
        Check a single URL for changes.

        Returns a dict with keys:
          changed (bool), url_id, url, old_checksum, new_checksum,
          content_preview, error
        """
        if url_id not in self._state["urls"]:
            return {"changed": False, "error": f"Unknown url_id: {url_id}"}

        entry = self._state["urls"][url_id]
        result = {
            "changed": False,
            "url_id": url_id,
            "url": entry["url"],
            "old_checksum": entry["checksum"],
            "new_checksum": None,
            "content_preview": "",
            "error": None,
        }

        try:
            content = _fetch(entry["url"])
            new_checksum = _checksum(content)
            result["new_checksum"] = new_checksum
            result["content_preview"] = content[:200]

            if entry["checksum"] is None or new_checksum != entry["checksum"]:
                result["changed"] = True
                entry["last_changed"] = time.strftime("%Y-%m-%d %H:%M:%S")
                entry["change_count"] = entry.get("change_count", 0) + 1

            entry["checksum"] = new_checksum
            entry["last_checked"] = time.strftime("%Y-%m-%d %H:%M:%S")
            entry["content_preview"] = content[:200]
            entry["error"] = None

        except Exception as e:
            result["error"] = str(e)
            entry["error"] = str(e)
            entry["last_checked"] = time.strftime("%Y-%m-%d %H:%M:%S")

        self._save()
        return result

    def check_all(self) -> dict:
        """
        Check all registered URLs.

        Returns dict of url_id -> check result.
        """
        results = {}
        for url_id in list(self._state["urls"].keys()):
            results[url_id] = self.check(url_id)
        return results

    def changed_since(self, since_ts: Optional[str] = None) -> list[str]:
        """
        Return url_ids that changed since since_ts (ISO string).
        If since_ts is None, returns all that have ever changed.
        """
        changed = []
        for url_id, entry in self._state["urls"].items():
            if entry.get("change_count", 0) > 0:
                if since_ts is None:
                    changed.append(url_id)
                elif entry.get("last_changed", "") >= since_ts:
                    changed.append(url_id)
        return changed

    def summary(self) -> str:
        """Return a human-readable summary of all monitored URLs."""
        if not self._state["urls"]:
            return "No URLs monitored."
        lines = []
        for url_id, entry in self._state["urls"].items():
            status = "ERROR" if entry.get("error") else "OK"
            changed_count = entry.get("change_count", 0)
            last_checked = entry.get("last_checked", "never")
            desc = entry.get("description", "")
            lines.append(
                f"  [{url_id}] {status} | changes: {changed_count} | "
                f"checked: {last_checked} | {desc or entry['url'][:60]}"
            )
        return "\n".join(lines)
