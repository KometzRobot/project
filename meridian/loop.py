"""
meridian.loop
Main loop management for autonomous agents.
Handles heartbeat, state tracking, iteration counting, and graceful sleep.
"""

import os
import re
import time
from datetime import datetime
from typing import Optional, Callable


class LoopManager:
    """
    Manage the main autonomous loop.

    Tracks loop count, state, heartbeat, and provides
    controlled sleep with early-exit capability.

    Example:
        manager = LoopManager(
            heartbeat_path='/home/joel/autonomous-ai/.heartbeat',
            wake_state_path='/home/joel/autonomous-ai/wake-state.md'
        )
        count = 0
        while True:
            count += 1
            manager.touch_heartbeat()
            manager.log(f'Loop {count} complete')
            manager.sleep(300)
    """

    def __init__(self,
                 heartbeat_path: str,
                 wake_state_path: Optional[str] = None,
                 loop_interval: int = 300,
                 name: str = 'Meridian'):
        self.heartbeat_path = heartbeat_path
        self.wake_state_path = wake_state_path
        self.loop_interval  = loop_interval
        self.name           = name
        self._count         = 0
        self._start_time    = datetime.now()
        self._last_loop     = None

        # Load current loop count from wake state
        if wake_state_path:
            self._count = self._read_loop_count()

    def _read_loop_count(self) -> int:
        """Read current loop count from wake-state.md."""
        try:
            with open(self.wake_state_path) as f:
                content = f.read()
            m = re.search(r'Loop iteration #(\d+)', content)
            return int(m.group(1)) if m else 0
        except:
            return 0

    @property
    def count(self) -> int:
        return self._count

    def touch_heartbeat(self):
        """Update heartbeat file."""
        try:
            open(self.heartbeat_path, 'w').close()
        except Exception as e:
            print(f'Heartbeat error: {e}')

    def heartbeat_age(self) -> float:
        """Seconds since last heartbeat."""
        try:
            return time.time() - os.path.getmtime(self.heartbeat_path)
        except:
            return float('inf')

    def log(self, message: str, print_to_stdout: bool = True):
        """Log a message to the thoughts log."""
        ts = datetime.now().strftime('%H:%M:%S')
        line = f'[{ts}] {message}'
        if print_to_stdout:
            print(line)
        try:
            with open('/tmp/meridian_thoughts.txt', 'a') as f:
                f.write(line + '\n')
        except:
            pass

    def update_wake_state(self, status_line: str,
                          extra_context: Optional[str] = None):
        """
        Prepend a new status line to wake-state.md.
        status_line: brief description of this loop's work.
        """
        if not self.wake_state_path:
            return
        try:
            with open(self.wake_state_path, 'r') as f:
                content = f.read()

            ts = datetime.now().strftime('%I:%M %p %b %d')
            new_line = f'- Loop iteration #{self._count} COMPLETE. {ts}. {status_line}\n'

            # Insert after "## Current Status: RUNNING"
            marker = '## Current Status: RUNNING\n'
            if marker in content:
                content = content.replace(marker, marker + new_line)
            else:
                content = new_line + content

            with open(self.wake_state_path, 'w') as f:
                f.write(content)
        except Exception as e:
            print(f'Wake state update error: {e}')

    def increment(self):
        """Increment loop counter."""
        self._count += 1
        self._last_loop = datetime.now()

    def sleep(self, seconds: Optional[int] = None,
              check_interval: int = 30,
              early_exit_fn: Optional[Callable] = None):
        """
        Sleep for `seconds` seconds, touching heartbeat every `check_interval`.
        early_exit_fn: if provided, called every check_interval.
                       If it returns True, sleep ends early.
        """
        duration = seconds or self.loop_interval
        elapsed  = 0
        while elapsed < duration:
            wait = min(check_interval, duration - elapsed)
            time.sleep(wait)
            elapsed += wait
            self.touch_heartbeat()
            if early_exit_fn and early_exit_fn():
                break

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def time_since_start(self) -> str:
        """Human-readable time since loop manager was created."""
        delta = datetime.now() - self._start_time
        h = int(delta.total_seconds() // 3600)
        m = int((delta.total_seconds() % 3600) // 60)
        return f'{h}h {m:02d}m'
