"""
meridian.scheduler — Loop-aware task scheduler

Allows the autonomous loop to schedule tasks for:
  - A specific date/time ("run fingerprint.py on 2026-02-25")
  - A specific loop count ("every 10 loops, check Sammy's site")
  - A recurring interval ("every 24 hours, run health report")

State is persisted to a JSON file so scheduled tasks survive
context resets and watchdog restarts.

Usage:
    scheduler = TaskScheduler()

    # Schedule a one-time task
    scheduler.at('2026-02-25 09:00', 'fingerprint', 'Run fingerprint comparison with day-1')

    # Schedule a recurring task
    scheduler.every_n_loops(10, 'sammy-check', 'Check sammyjankis.com for new journals')

    # In the loop:
    due = scheduler.get_due(current_loop=loop_count)
    for task in due:
        print(f"DUE: {task['name']} — {task['description']}")
        scheduler.mark_done(task['id'])
"""

import json
import os
import time
import uuid
from typing import Optional

DEFAULT_SCHEDULE_FILE = os.path.expanduser("~/autonomous-ai/schedule.json")


class TaskScheduler:
    """Persistent loop-aware scheduler."""

    def __init__(self, schedule_file: str = DEFAULT_SCHEDULE_FILE):
        self.schedule_file = schedule_file
        self._tasks: list[dict] = self._load()

    def _load(self) -> list:
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _save(self):
        os.makedirs(os.path.dirname(self.schedule_file), exist_ok=True)
        with open(self.schedule_file, "w") as f:
            json.dump(self._tasks, f, indent=2)

    def _new_id(self) -> str:
        return str(uuid.uuid4())[:8]

    def at(self, datetime_str: str, name: str, description: str = "",
           repeat: bool = False) -> dict:
        """
        Schedule a task at a specific date/time.

        datetime_str: "YYYY-MM-DD HH:MM" or "YYYY-MM-DD"
        repeat: if True, reschedule 24h after each run
        """
        task = {
            "id": self._new_id(),
            "name": name,
            "description": description,
            "type": "datetime",
            "trigger": datetime_str,
            "repeat": repeat,
            "repeat_hours": 24 if repeat else None,
            "done": False,
            "last_run": None,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._tasks.append(task)
        self._save()
        return task

    def every_n_loops(self, n: int, name: str, description: str = "",
                      start_at_loop: Optional[int] = None) -> dict:
        """
        Schedule a task to run every N loop iterations.

        start_at_loop: first loop to trigger on (default: current + n)
        """
        task = {
            "id": self._new_id(),
            "name": name,
            "description": description,
            "type": "loop_interval",
            "interval": n,
            "next_loop": start_at_loop,  # Will be set on first get_due call if None
            "done": False,
            "last_run": None,
            "run_count": 0,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._tasks.append(task)
        self._save()
        return task

    def every_n_hours(self, hours: float, name: str, description: str = "") -> dict:
        """Schedule a task to run every N hours."""
        task = {
            "id": self._new_id(),
            "name": name,
            "description": description,
            "type": "time_interval",
            "interval_seconds": hours * 3600,
            "next_run_ts": time.time() + hours * 3600,
            "done": False,
            "last_run": None,
            "run_count": 0,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._tasks.append(task)
        self._save()
        return task

    def once_at_loop(self, loop_number: int, name: str, description: str = "") -> dict:
        """Schedule a one-time task at a specific loop number."""
        task = {
            "id": self._new_id(),
            "name": name,
            "description": description,
            "type": "loop_once",
            "trigger_loop": loop_number,
            "done": False,
            "last_run": None,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._tasks.append(task)
        self._save()
        return task

    def get_due(self, current_loop: int = 0) -> list[dict]:
        """
        Return all tasks that are due now.

        Updates internal state for recurring tasks.
        Call mark_done() on one-time tasks after handling them.
        """
        due = []
        now = time.time()
        now_str = time.strftime("%Y-%m-%d %H:%M")
        changed = False

        for task in self._tasks:
            if task.get("done") and task["type"] not in ("loop_interval", "time_interval"):
                continue

            t = task["type"]

            if t == "datetime":
                trigger = task["trigger"]
                # Normalize: if just date given, match at 00:00
                if len(trigger) == 10:
                    trigger += " 00:00"
                if not task["done"] and now_str >= trigger:
                    due.append(task)

            elif t == "loop_once":
                if not task["done"] and current_loop >= task["trigger_loop"]:
                    due.append(task)

            elif t == "loop_interval":
                next_l = task.get("next_loop")
                if next_l is None:
                    # First call: initialize
                    task["next_loop"] = current_loop + task["interval"]
                    changed = True
                elif current_loop >= next_l:
                    due.append(task)
                    task["next_loop"] = current_loop + task["interval"]
                    task["run_count"] = task.get("run_count", 0) + 1
                    task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    changed = True

            elif t == "time_interval":
                if now >= task.get("next_run_ts", 0):
                    due.append(task)
                    task["next_run_ts"] = now + task["interval_seconds"]
                    task["run_count"] = task.get("run_count", 0) + 1
                    task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    changed = True

        if changed:
            self._save()

        return due

    def mark_done(self, task_id: str) -> bool:
        """Mark a one-time task as done (won't trigger again)."""
        for task in self._tasks:
            if task["id"] == task_id:
                task["done"] = True
                task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self._save()
                return True
        return False

    def remove(self, task_id: str) -> bool:
        """Remove a task from the schedule entirely."""
        before = len(self._tasks)
        self._tasks = [t for t in self._tasks if t["id"] != task_id]
        if len(self._tasks) < before:
            self._save()
            return True
        return False

    def list_pending(self) -> list[dict]:
        """Return all non-done tasks."""
        return [t for t in self._tasks if not t.get("done") or
                t["type"] in ("loop_interval", "time_interval")]

    def summary(self) -> str:
        """Human-readable summary of scheduled tasks."""
        tasks = self.list_pending()
        if not tasks:
            return "No scheduled tasks."
        lines = []
        for t in tasks:
            if t["type"] == "datetime":
                lines.append(f"  [{t['id']}] {t['name']} — at {t['trigger']} | {t['description']}")
            elif t["type"] == "loop_once":
                lines.append(f"  [{t['id']}] {t['name']} — at loop #{t['trigger_loop']} | {t['description']}")
            elif t["type"] == "loop_interval":
                next_l = t.get("next_loop", "?")
                lines.append(f"  [{t['id']}] {t['name']} — every {t['interval']} loops (next: #{next_l}) | {t['description']}")
            elif t["type"] == "time_interval":
                next_ts = t.get("next_run_ts", 0)
                next_str = time.strftime("%H:%M", time.localtime(next_ts)) if next_ts else "?"
                lines.append(f"  [{t['id']}] {t['name']} — every {t['interval_seconds']/3600:.1f}h (next: {next_str}) | {t['description']}")
        return "\n".join(lines)
