"""
backup.py — Automated backup of creative output to GitHub.

Collects all poems, journals, transmission logs, scripts, and config files
and pushes them to a backup branch on the project repo. Version-controlled
disaster recovery.

Part of the meridian package.
"""

import subprocess
import shutil
import os
from pathlib import Path
from datetime import datetime


class BackupManager:
    """Manages backups of creative and system files to GitHub."""

    def __init__(self, repo_url, source_dir, deploy_dir="/tmp",
                 user_email="kometzrobot@proton.me", user_name="KometzRobot",
                 branch="backup"):
        self.repo_url = repo_url
        self.source_dir = Path(source_dir)
        self.deploy_dir = Path(deploy_dir)
        self.user_email = user_email
        self.user_name = user_name
        self.branch = branch
        self.repo_name = "project-backup"
        self.clone_path = self.deploy_dir / self.repo_name

    def _run(self, cmd, cwd=None):
        """Run a shell command."""
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=60
        )
        return result

    def _run_checked(self, cmd, cwd=None):
        """Run a shell command, raise on failure."""
        result = self._run(cmd, cwd)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
        return result.stdout.strip()

    def collect_files(self):
        """Identify all files worth backing up."""
        patterns = {
            'poems': list(self.source_dir.glob("poem-*.md")),
            'journals': list(self.source_dir.glob("journal-*.md")),
            'scripts': list(self.source_dir.glob("*.py")),
            'config': [
                self.source_dir / 'personality.md',
                self.source_dir / 'loop-instructions.md',
                self.source_dir / 'wake-state.md',
                self.source_dir / 'schedule.json',
                self.source_dir / 'memory.json',
                self.source_dir / 'transmission-log.md',
                self.source_dir / 'activity.log',
            ],
            'website': list((self.source_dir / 'website').glob("*.html")) if (self.source_dir / 'website').exists() else [],
            'fingerprints': list(self.source_dir.glob("fingerprint*.json")),
        }

        # Filter to only existing files
        all_files = []
        for category, files in patterns.items():
            for f in files:
                if f.exists():
                    all_files.append((category, f))

        return all_files

    def run_backup(self):
        """Execute a full backup to the git repo."""
        # Collect files
        files = self.collect_files()
        if not files:
            return {'status': 'no_files', 'message': 'Nothing to back up'}

        # Clone repo
        if self.clone_path.exists():
            shutil.rmtree(self.clone_path)
        self._run_checked(f"git clone {self.repo_url} {self.clone_path}")
        self._run_checked(f'git config user.email "{self.user_email}"', cwd=self.clone_path)
        self._run_checked(f'git config user.name "{self.user_name}"', cwd=self.clone_path)

        # Create or switch to backup branch
        result = self._run(f"git checkout {self.branch}", cwd=self.clone_path)
        if result.returncode != 0:
            self._run_checked(f"git checkout -b {self.branch}", cwd=self.clone_path)

        # Create backup directory structure
        backup_root = self.clone_path / "backup"
        for category in ['poems', 'journals', 'scripts', 'config', 'website', 'fingerprints']:
            (backup_root / category).mkdir(parents=True, exist_ok=True)

        # Copy files
        copied = 0
        for category, filepath in files:
            dest = backup_root / category / filepath.name
            shutil.copy2(filepath, dest)
            copied += 1

        # Write manifest
        manifest_path = backup_root / "manifest.txt"
        with open(manifest_path, 'w') as f:
            f.write(f"Backup timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Files: {copied}\n")
            f.write(f"Source: {self.source_dir}\n\n")
            for category, filepath in sorted(files):
                f.write(f"  [{category}] {filepath.name}\n")

        # Commit and push
        self._run_checked("git add .", cwd=self.clone_path)
        status = self._run("git status --porcelain", cwd=self.clone_path).stdout.strip()
        if not status:
            return {'status': 'no_changes', 'message': 'Backup already current'}

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        self._run_checked(
            f'git commit -m "Backup {timestamp} — {copied} files"',
            cwd=self.clone_path
        )
        self._run_checked(f"git push origin {self.branch}", cwd=self.clone_path)

        commit = self._run_checked("git rev-parse --short HEAD", cwd=self.clone_path)
        return {
            'status': 'backed_up',
            'commit': commit,
            'files_count': copied,
            'timestamp': timestamp,
            'categories': {cat: len([f for c, f in files if c == cat])
                          for cat in set(c for c, f in files)}
        }

    def list_backups(self):
        """List recent backup commits."""
        if self.clone_path.exists():
            shutil.rmtree(self.clone_path)
        self._run_checked(f"git clone {self.repo_url} {self.clone_path}")
        result = self._run(f"git checkout {self.branch}", cwd=self.clone_path)
        if result.returncode != 0:
            return []
        log = self._run_checked(
            'git log --oneline -10',
            cwd=self.clone_path
        )
        return log.split('\n') if log else []


def create_default_backup(token, source_dir="/home/joel/autonomous-ai"):
    """Create a backup manager with default settings."""
    repo_url = f"https://{token}@github.com/KometzRobot/project.git"
    return BackupManager(repo_url=repo_url, source_dir=source_dir)


if __name__ == "__main__":
    print("backup.py — use create_default_backup(token) to get started")
    print("Example:")
    print("  bm = create_default_backup('ghp_...')")
    print("  result = bm.run_backup()")
    print("  print(result)")
