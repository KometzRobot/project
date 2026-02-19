"""
meridian.system_tools
Linux system monitoring and control for autonomous agents.
"""

import os
import time
import shutil
import subprocess
import glob
from typing import List, Dict, Optional, Tuple


class SystemMonitor:
    """
    Monitor and interact with the Linux system.

    Example:
        monitor = SystemMonitor()
        health = monitor.get_stats()
        print(health['load1'], health['disk_pct'], health['ram_pct'])

        procs = monitor.find_process('irc-bot')
        monitor.kill_process(procs[0]['pid'])
    """

    def get_stats(self) -> Dict:
        """Get comprehensive system health stats."""
        s = {}

        # Disk
        try:
            d = shutil.disk_usage('/')
            s['disk_pct']  = round(d.used / d.total * 100, 1)
            s['disk_used'] = d.used
            s['disk_total'] = d.total
            s['disk_free_gb'] = round(d.free / (1 << 30), 1)
        except:
            s['disk_pct'] = s['disk_used'] = s['disk_total'] = 0
            s['disk_free_gb'] = 0

        # Memory
        try:
            mem = {}
            with open('/proc/meminfo') as f:
                for ln in f:
                    k, v = ln.split(':')
                    mem[k.strip()] = int(v.split()[0])
            total = mem['MemTotal']
            avail = mem['MemAvailable']
            used  = total - avail
            s['ram_pct']   = round(used / total * 100, 1)
            s['ram_used_mb']  = used // 1024
            s['ram_total_mb'] = total // 1024
            s['ram_avail_mb'] = avail // 1024
        except:
            s['ram_pct'] = s['ram_used_mb'] = s['ram_total_mb'] = 0

        # Load average
        try:
            load = os.getloadavg()
            s['load1']  = load[0]
            s['load5']  = load[1]
            s['load15'] = load[2]
        except:
            s['load1'] = s['load5'] = s['load15'] = 0.0

        # Uptime
        try:
            with open('/proc/uptime') as f:
                secs = float(f.read().split()[0])
            s['uptime_secs'] = secs
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            s['uptime_str'] = f'{h}h {m:02d}m'
        except:
            s['uptime_secs'] = 0
            s['uptime_str'] = '?'

        # Network interfaces
        try:
            r = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=3)
            interfaces = {}
            current = None
            for ln in r.stdout.splitlines():
                if ln[0].isdigit():
                    current = ln.split(':')[1].strip()
                    interfaces[current] = []
                elif 'inet ' in ln and current:
                    ip = ln.strip().split()[1]
                    interfaces[current].append(ip)
            s['interfaces'] = interfaces
        except:
            s['interfaces'] = {}

        return s

    def get_top_processes(self, n: int = 20, sort_by: str = 'cpu') -> List[Dict]:
        """Get top N processes sorted by CPU or memory."""
        sort_flag = '-%cpu' if sort_by == 'cpu' else '-%mem'
        try:
            r = subprocess.run(
                ['ps', 'aux', f'--sort={sort_flag}'],
                capture_output=True, text=True, timeout=3
            )
            procs = []
            for ln in r.stdout.splitlines()[1:]:
                parts = ln.split(None, 10)
                if len(parts) >= 11:
                    procs.append({
                        'user': parts[0],
                        'pid':  parts[1],
                        'cpu':  float(parts[2]),
                        'mem':  float(parts[3]),
                        'cmd':  parts[10],
                    })
            return procs[:n]
        except:
            return []

    def find_process(self, pattern: str) -> List[Dict]:
        """Find processes matching a pattern."""
        try:
            r = subprocess.run(['pgrep', '-a', '-f', pattern],
                               capture_output=True, text=True, timeout=3)
            if r.returncode != 0:
                return []
            procs = []
            for ln in r.stdout.strip().splitlines():
                parts = ln.split(None, 1)
                if len(parts) >= 2:
                    procs.append({'pid': parts[0], 'cmd': parts[1]})
            return procs
        except:
            return []

    def is_running(self, pattern: str) -> bool:
        """Check if a process matching pattern is running."""
        r = subprocess.run(['pgrep', '-f', pattern], capture_output=True)
        return r.returncode == 0

    def kill_process(self, pid_or_pattern: str, signal: int = 9) -> bool:
        """Kill a process by PID or pattern. Returns True on success."""
        try:
            if str(pid_or_pattern).isdigit():
                r = subprocess.run(['kill', f'-{signal}', str(pid_or_pattern)],
                                   capture_output=True)
            else:
                r = subprocess.run(['pkill', f'-{signal}', '-f', str(pid_or_pattern)],
                                   capture_output=True)
            return r.returncode == 0
        except:
            return False

    def run_command(self, cmd: str, timeout: int = 30, cwd: Optional[str] = None) -> Dict:
        """Run a shell command. Returns dict with stdout, stderr, returncode."""
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd
            )
            return {
                'stdout':     r.stdout,
                'stderr':     r.stderr,
                'returncode': r.returncode,
                'ok':         r.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {'stdout': '', 'stderr': f'Timeout after {timeout}s',
                    'returncode': -1, 'ok': False}
        except Exception as e:
            return {'stdout': '', 'stderr': str(e), 'returncode': -1, 'ok': False}

    def get_crontab(self) -> List[str]:
        """Get current crontab entries."""
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if r.returncode != 0:
            return []
        return [ln for ln in r.stdout.splitlines() if ln.strip() and not ln.startswith('#')]

    def add_cron_job(self, schedule: str, command: str) -> bool:
        """Add a cron job. schedule is e.g. '*/5 * * * *'."""
        current = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        existing = current.stdout if current.returncode == 0 else ''
        new_job = f'{schedule} {command}'
        if new_job in existing:
            return True  # already exists
        new_crontab = existing.rstrip() + '\n' + new_job + '\n'
        r = subprocess.run(['crontab', '-'], input=new_crontab.encode(),
                           capture_output=True)
        return r.returncode == 0

    def get_disk_usage(self, path: str = '/') -> Dict:
        """Get disk usage for a path."""
        try:
            d = shutil.disk_usage(path)
            return {
                'path':     path,
                'total_gb': round(d.total / (1 << 30), 1),
                'used_gb':  round(d.used / (1 << 30), 1),
                'free_gb':  round(d.free / (1 << 30), 1),
                'pct':      round(d.used / d.total * 100, 1),
            }
        except Exception as e:
            return {'path': path, 'error': str(e)}

    def find_files(self, base_dir: str, pattern: str = '*',
                   max_results: int = 100) -> List[str]:
        """Find files matching a glob pattern."""
        full_pattern = os.path.join(base_dir, '**', pattern)
        results = glob.glob(full_pattern, recursive=True)
        return sorted(results)[:max_results]


class Heartbeat:
    """
    Manage a heartbeat file for watchdog monitoring.

    Example:
        hb = Heartbeat('/path/.heartbeat')
        hb.touch()
        print(hb.age_seconds())
        print(hb.is_healthy(threshold=400))
    """

    def __init__(self, path: str):
        self.path = path

    def touch(self):
        """Update heartbeat timestamp."""
        open(self.path, 'w').close()

    def age_seconds(self) -> float:
        """Seconds since last heartbeat touch."""
        try:
            return time.time() - os.path.getmtime(self.path)
        except:
            return float('inf')

    def is_healthy(self, threshold: int = 400) -> bool:
        """True if heartbeat is recent enough."""
        return self.age_seconds() < threshold

    def exists(self) -> bool:
        return os.path.exists(self.path)
