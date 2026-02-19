"""
meridian.memory — Persistent structured memory for the autonomous loop

A lightweight key-value store with tags and full-text search.
Survives context resets by persisting to a JSON file.

This is NOT a replacement for wake-state.md (which is the per-loop narrative log).
It's for structured facts that need to be queryable:
  - Credentials and endpoints
  - Known contacts and their details
  - Key dates and scheduled events
  - Learned facts about the environment

Usage:
    mem = Memory()
    mem.set('sammy.url', 'https://sammyjankis.com', tags=['contacts', 'external'])
    mem.set('joel.email', 'jkometz@hotmail.com', tags=['contacts'])
    mem.set('fingerprint.day1', '2026-02-19', tags=['milestones', 'fingerprint'])

    # Query
    contacts = mem.get_by_tag('contacts')
    url = mem.get('sammy.url')

    # Search
    results = mem.search('fingerprint')
"""

import json
import os
import time
from typing import Any, Optional

DEFAULT_MEMORY_FILE = os.path.expanduser("~/autonomous-ai/memory.json")


class Memory:
    """
    Persistent key-value store with tags and search.

    Keys use dot notation for namespacing:
      'joel.email', 'sammy.url', 'system.hostname'
    """

    def __init__(self, memory_file: str = DEFAULT_MEMORY_FILE):
        self.memory_file = memory_file
        self._data: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"entries": {}, "version": 1}

    def _save(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def set(self, key: str, value: Any, tags: list[str] = None,
            note: str = "") -> dict:
        """
        Store a value. Overwrites existing value for the same key.

        Returns the stored entry.
        """
        entry = {
            "value": value,
            "tags": tags or [],
            "note": note,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "created": self._data["entries"].get(key, {}).get(
                "created", time.strftime("%Y-%m-%d %H:%M:%S")
            ),
        }
        self._data["entries"][key] = entry
        self._save()
        return entry

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for a key, or default if not found."""
        entry = self._data["entries"].get(key)
        if entry is None:
            return default
        return entry["value"]

    def get_entry(self, key: str) -> Optional[dict]:
        """Return the full entry (value + metadata) for a key."""
        return self._data["entries"].get(key)

    def delete(self, key: str) -> bool:
        """Remove a key. Returns True if it existed."""
        if key in self._data["entries"]:
            del self._data["entries"][key]
            self._save()
            return True
        return False

    def get_by_tag(self, tag: str) -> dict:
        """Return all entries that have the given tag."""
        return {
            key: entry
            for key, entry in self._data["entries"].items()
            if tag in entry.get("tags", [])
        }

    def get_by_prefix(self, prefix: str) -> dict:
        """Return all entries whose key starts with prefix."""
        return {
            key: entry
            for key, entry in self._data["entries"].items()
            if key.startswith(prefix)
        }

    def search(self, query: str) -> dict:
        """
        Search keys, values, notes, and tags for the query string.
        Case-insensitive.
        """
        q = query.lower()
        results = {}
        for key, entry in self._data["entries"].items():
            if (q in key.lower() or
                    q in str(entry.get("value", "")).lower() or
                    q in entry.get("note", "").lower() or
                    any(q in t.lower() for t in entry.get("tags", []))):
                results[key] = entry
        return results

    def all_keys(self) -> list[str]:
        """Return all stored keys, sorted."""
        return sorted(self._data["entries"].keys())

    def all_tags(self) -> list[str]:
        """Return all unique tags in use."""
        tags = set()
        for entry in self._data["entries"].values():
            tags.update(entry.get("tags", []))
        return sorted(tags)

    def summary(self) -> str:
        """Human-readable summary of all entries."""
        if not self._data["entries"]:
            return "Memory is empty."
        lines = [f"Memory: {len(self._data['entries'])} entries, tags: {', '.join(self.all_tags())}"]
        for key in self.all_keys():
            entry = self._data["entries"][key]
            val = str(entry["value"])[:60]
            tags = ", ".join(entry.get("tags", []))
            lines.append(f"  {key}: {val} [{tags}]")
        return "\n".join(lines)

    def dump(self) -> dict:
        """Return a copy of all entries."""
        return dict(self._data["entries"])
