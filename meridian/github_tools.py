"""
meridian.github_tools
GitHub API integration for autonomous agents.
Read repos, files, commits, search code.
"""

import json
import base64
import urllib.request
import urllib.error
from typing import List, Dict, Optional


BASE_API = 'https://api.github.com'


class GitHubClient:
    """
    GitHub API client — no external dependencies.

    Example:
        gh = GitHubClient(token='ghp_...')
        repos = gh.list_repos('KometzRobot')
        content = gh.read_file('KometzRobot/project', 'README.md')
    """

    def __init__(self, token: str, user: str = 'KometzRobot'):
        self.token = token
        self.default_user = user

    def _get(self, path: str, params: Optional[Dict] = None) -> Optional[any]:
        url = f'{BASE_API}{path}'
        if params:
            url += '?' + '&'.join(f'{k}={v}' for k, v in params.items())
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'token {self.token}')
        req.add_header('Accept', 'application/vnd.github.v3+json')
        req.add_header('User-Agent', 'meridian/0.1')
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            print(f'GitHub API {e.code}: {e.reason} — {path}')
            return None
        except Exception as e:
            print(f'GitHub API error: {e}')
            return None

    def _parse_repo(self, repo_str: str):
        if '/' in repo_str:
            return repo_str.split('/', 1)
        return self.default_user, repo_str

    def list_repos(self, user: Optional[str] = None) -> List[Dict]:
        """List repositories for a user."""
        u = user or self.default_user
        data = self._get(f'/users/{u}/repos', {'sort': 'updated', 'per_page': '50'})
        if not data:
            return []
        return [{
            'name':        r['name'],
            'full_name':   r['full_name'],
            'description': r.get('description') or '',
            'language':    r.get('language') or '',
            'stars':       r.get('stargazers_count', 0),
            'forks':       r.get('forks_count', 0),
            'updated':     r.get('updated_at', '')[:10],
            'url':         r.get('html_url', ''),
            'clone_url':   r.get('clone_url', ''),
            'private':     r.get('private', False),
        } for r in data]

    def get_repo(self, repo: str) -> Optional[Dict]:
        """Get repository metadata."""
        owner, name = self._parse_repo(repo)
        data = self._get(f'/repos/{owner}/{name}')
        if not data:
            return None
        return {
            'name':        data['name'],
            'full_name':   data['full_name'],
            'description': data.get('description') or '',
            'language':    data.get('language') or '',
            'stars':       data.get('stargazers_count', 0),
            'size':        data.get('size', 0),
            'default_branch': data.get('default_branch', 'main'),
            'created':     data.get('created_at', '')[:10],
            'updated':     data.get('updated_at', '')[:10],
            'url':         data.get('html_url', ''),
        }

    def list_files(self, repo: str, path: str = '') -> Dict[str, List]:
        """List files and directories at a path."""
        owner, name = self._parse_repo(repo)
        data = self._get(f'/repos/{owner}/{name}/contents/{path}')
        if not data:
            return {'dirs': [], 'files': []}
        if isinstance(data, dict):
            return {'dirs': [], 'files': [data['name']]}
        dirs  = sorted([e['name'] for e in data if e['type'] == 'dir'])
        files = sorted([{'name': e['name'], 'size': e.get('size', 0), 'path': e['path']}
                        for e in data if e['type'] == 'file'],
                       key=lambda x: x['name'])
        return {'dirs': dirs, 'files': files}

    def read_file(self, repo: str, path: str, max_lines: int = 200) -> Optional[str]:
        """Read a file from a repo. Returns decoded text content."""
        owner, name = self._parse_repo(repo)
        data = self._get(f'/repos/{owner}/{name}/contents/{path}')
        if not data:
            return None
        if data.get('encoding') == 'base64':
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            lines = content.splitlines()
            if max_lines and len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f'\n... ({len(lines)-max_lines} more lines)'
            return content
        return None

    def get_commits(self, repo: str, n: int = 20) -> List[Dict]:
        """Get recent commits."""
        owner, name = self._parse_repo(repo)
        data = self._get(f'/repos/{owner}/{name}/commits', {'per_page': str(n)})
        if not data:
            return []
        return [{
            'sha':     c['sha'][:7],
            'message': c['commit']['message'].split('\n')[0][:80],
            'author':  c['commit']['author']['name'],
            'date':    c['commit']['author']['date'][:10],
        } for c in data]

    def search_code(self, repo: str, query: str, max_results: int = 20) -> List[Dict]:
        """Search for code patterns in a repo."""
        owner, name = self._parse_repo(repo)
        data = self._get('/search/code', {
            'q': f'{query}+repo:{owner}/{name}',
            'per_page': str(max_results),
        })
        if not data:
            return []
        items = data.get('items', [])
        return [{
            'path':      item['path'],
            'url':       item.get('html_url', ''),
            'fragments': [m.get('fragment', '') for m in item.get('text_matches', [])],
        } for item in items]

    def get_languages(self, repo: str) -> Dict[str, float]:
        """Get language breakdown as percentages."""
        owner, name = self._parse_repo(repo)
        data = self._get(f'/repos/{owner}/{name}/languages')
        if not data:
            return {}
        total = sum(data.values())
        if total == 0:
            return {}
        return {lang: round(count / total * 100, 1) for lang, count in data.items()}
