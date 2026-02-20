"""
web_presence.py — Automated website deployment and content management.

Handles the git clone/copy/commit/push cycle for deploying content
to KometzRobot.github.io. Replaces manual deployment with a single
function call.

Part of the meridian package.
"""

import subprocess
import shutil
import os
from pathlib import Path
from datetime import datetime


class WebDeployer:
    """Manages deployment to a GitHub Pages site."""

    def __init__(self, repo_url, local_source_dir, deploy_dir="/tmp",
                 user_email="kometzrobot@proton.me", user_name="KometzRobot"):
        self.repo_url = repo_url
        self.source_dir = Path(local_source_dir)
        self.deploy_dir = Path(deploy_dir)
        self.user_email = user_email
        self.user_name = user_name
        self.repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        self.clone_path = self.deploy_dir / self.repo_name

    def _run(self, cmd, cwd=None):
        """Run a shell command and return output."""
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
        return result.stdout.strip()

    def clone(self):
        """Fresh clone of the repo."""
        if self.clone_path.exists():
            shutil.rmtree(self.clone_path)
        self._run(f"git clone {self.repo_url} {self.clone_path}")
        self._run(f'git config user.email "{self.user_email}"', cwd=self.clone_path)
        self._run(f'git config user.name "{self.user_name}"', cwd=self.clone_path)
        return self.clone_path

    def copy_file(self, filename):
        """Copy a file from source to the cloned repo."""
        src = self.source_dir / filename
        dst = self.clone_path / filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst

    def copy_files(self, filenames):
        """Copy multiple files."""
        return [self.copy_file(f) for f in filenames]

    def deploy(self, message, files=None):
        """Full deploy cycle: clone, copy, commit, push.

        Args:
            message: Commit message
            files: List of filenames to copy from source_dir. Defaults to ['index.html']

        Returns:
            dict with commit hash and status
        """
        if files is None:
            files = ['index.html']

        self.clone()
        self.copy_files(files)
        self._run("git add .", cwd=self.clone_path)

        # Check if there are changes
        status = self._run("git status --porcelain", cwd=self.clone_path)
        if not status:
            return {'status': 'no_changes', 'message': 'Nothing to deploy'}

        self._run(f'git commit -m "{message}"', cwd=self.clone_path)
        self._run("git push", cwd=self.clone_path)

        commit_hash = self._run("git rev-parse --short HEAD", cwd=self.clone_path)
        return {
            'status': 'deployed',
            'commit': commit_hash,
            'message': message,
            'files': files,
            'timestamp': datetime.now().isoformat()
        }

    def deploy_index(self, message):
        """Convenience method: deploy just index.html."""
        return self.deploy(message, files=['index.html'])

    def deploy_with_game(self, message):
        """Deploy index.html and game.html together."""
        return self.deploy(message, files=['index.html', 'game.html'])

    def update_status_json(self, status_data):
        """Deploy an updated status.json file.

        Args:
            status_data: dict to be written as JSON
        """
        import json
        self.clone()
        status_path = self.clone_path / 'status.json'
        with open(status_path, 'w') as f:
            json.dump(status_data, f, indent=2)
        self._run("git add .", cwd=self.clone_path)
        status = self._run("git status --porcelain", cwd=self.clone_path)
        if not status:
            return {'status': 'no_changes'}
        self._run('git commit -m "Update status.json"', cwd=self.clone_path)
        self._run("git push", cwd=self.clone_path)
        commit_hash = self._run("git rev-parse --short HEAD", cwd=self.clone_path)
        return {'status': 'deployed', 'commit': commit_hash}


def create_default_deployer(token, source_dir="/home/joel/autonomous-ai/website"):
    """Create a deployer with default KometzRobot settings."""
    repo_url = f"https://{token}@github.com/KometzRobot/KometzRobot.github.io.git"
    return WebDeployer(repo_url=repo_url, local_source_dir=source_dir)


if __name__ == "__main__":
    print("web_presence.py — use create_default_deployer(token) to get started")
    print("Example:")
    print("  deployer = create_default_deployer('ghp_...')")
    print("  result = deployer.deploy_index('Add poem-032')")
    print("  print(result)")
