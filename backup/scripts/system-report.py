#!/usr/bin/env python3
"""
system-report.py — Comprehensive system diagnostic for Meridian.
Prints a full report: processes, ports, disk, network, key services.
"""
import subprocess, os, socket, datetime

def run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str))
        return r.stdout.strip()
    except Exception as e:
        return f"[error: {e}]"

def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

def main():
    print(f"MERIDIAN SYSTEM REPORT")
    print(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S MST')}")
    print(f"Hostname: {socket.gethostname()}")

    section("UPTIME & LOAD")
    print(run('uptime'))

    section("DISK USAGE")
    print(run('df -h /'))

    section("MEMORY")
    print(run('free -h'))

    section("KEY PROCESSES")
    procs = [
        ("Claude (main loop)", "claude --dangerously"),
        ("Proton Bridge",       "protonmail-bridge"),
        ("IRC Bot",             "irc-bot.py"),
        ("Status Display",      "status-display"),
        ("HTTP Server",         "http.server 8080"),
        ("Localtunnel",         "lt --port 8080"),
        ("Watchdog daemon",     "watchdogd"),
    ]
    for name, pattern in procs:
        pids = run(f"pgrep -f '{pattern}'")
        status = f"RUNNING ({pids.split()[0]})" if pids and not pids.startswith('[') else "DOWN"
        print(f"  {name:<25} {status}")

    section("LISTENING PORTS")
    print(run('ss -tlnp'))

    section("NETWORK INTERFACES")
    print(run('ip addr show | grep -E "inet |^[0-9]+"'))

    section("RECENT PROCESSES (top 10 by CPU)")
    print(run("ps aux --sort=-%cpu | head -11"))

    section("DISK INODES")
    print(run('df -i /'))

    section("CRONTAB")
    print(run('crontab -l'))

    section("RECENT SYSTEM JOURNAL (errors only)")
    print(run('journalctl -p err -n 5 --no-pager 2>/dev/null || echo "[no journal access]"'))

    section("KEY FILES (heartbeat age)")
    hb = "/home/joel/autonomous-ai/.heartbeat"
    if os.path.exists(hb):
        age = int(datetime.datetime.now().timestamp() - os.path.getmtime(hb))
        print(f"  .heartbeat: {age}s old")
    else:
        print("  .heartbeat: MISSING")

    print("\n" + "="*50)
    print("  END REPORT")
    print("="*50 + "\n")

if __name__ == '__main__':
    main()
