"""
learning.py — External content ingestion and summarization.

Reads RSS/Atom feeds, web pages, and GitHub trending repos.
Provides a stream of external knowledge to feed creative work
and self-awareness.

Part of the meridian package.
"""

import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
from html import unescape


class FeedReader:
    """Read and parse RSS/Atom feeds."""

    def __init__(self, user_agent="Meridian/1.0"):
        self.user_agent = user_agent
        self.feeds = {}

    def add_feed(self, name, url):
        """Register a feed to monitor."""
        self.feeds[name] = url

    def fetch_feed(self, url, max_items=10):
        """Fetch and parse an RSS/Atom feed."""
        req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
        try:
            data = urllib.request.urlopen(req, timeout=15).read()
        except Exception as e:
            return {'error': str(e), 'items': []}

        try:
            root = ET.fromstring(data)
        except ET.ParseError as e:
            return {'error': f'Parse error: {e}', 'items': []}

        items = []

        # RSS format
        for item in root.iter('item'):
            entry = {
                'title': _text(item, 'title'),
                'link': _text(item, 'link'),
                'description': _clean_html(_text(item, 'description')),
                'pub_date': _text(item, 'pubDate'),
            }
            items.append(entry)
            if len(items) >= max_items:
                break

        # Atom format
        if not items:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('.//atom:entry', ns):
                link_el = entry.find('atom:link', ns)
                item = {
                    'title': _text_ns(entry, 'atom:title', ns),
                    'link': link_el.get('href', '') if link_el is not None else '',
                    'description': _clean_html(_text_ns(entry, 'atom:summary', ns) or _text_ns(entry, 'atom:content', ns)),
                    'pub_date': _text_ns(entry, 'atom:updated', ns),
                }
                items.append(item)
                if len(items) >= max_items:
                    break

            # Try without namespace
            if not items:
                for entry in root.iter('entry'):
                    link_el = entry.find('link')
                    item = {
                        'title': _text(entry, 'title'),
                        'link': link_el.get('href', '') if link_el is not None else '',
                        'description': _clean_html(_text(entry, 'summary') or _text(entry, 'content')),
                        'pub_date': _text(entry, 'updated'),
                    }
                    items.append(item)
                    if len(items) >= max_items:
                        break

        return {'items': items, 'count': len(items)}

    def fetch_all(self, max_items_per_feed=5):
        """Fetch all registered feeds."""
        results = {}
        for name, url in self.feeds.items():
            results[name] = self.fetch_feed(url, max_items=max_items_per_feed)
        return results

    def digest(self, max_items_per_feed=3):
        """Generate a text digest of all feeds."""
        all_results = self.fetch_all(max_items_per_feed)
        lines = []
        lines.append(f"LEARNING DIGEST — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        for name, result in all_results.items():
            if result.get('error'):
                lines.append(f"[{name}] Error: {result['error']}")
                continue
            lines.append(f"[{name}] ({result['count']} items)")
            for item in result['items']:
                title = item.get('title', 'Untitled')
                desc = item.get('description', '')[:150]
                lines.append(f"  - {title}")
                if desc:
                    lines.append(f"    {desc}")
            lines.append("")

        return "\n".join(lines)


class GitHubTrending:
    """Fetch trending repositories from GitHub."""

    def __init__(self, token=None, user_agent="Meridian/1.0"):
        self.token = token
        self.user_agent = user_agent

    def search_repos(self, query, sort="stars", max_results=5):
        """Search GitHub repos."""
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort={sort}&per_page={max_results}"
        headers = {'User-Agent': self.user_agent}
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        req = urllib.request.Request(url, headers=headers)
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
            repos = []
            for r in data.get('items', [])[:max_results]:
                repos.append({
                    'name': r['full_name'],
                    'description': r.get('description', ''),
                    'stars': r['stargazers_count'],
                    'language': r.get('language', ''),
                    'url': r['html_url'],
                    'updated': r.get('updated_at', ''),
                })
            return repos
        except Exception as e:
            return [{'error': str(e)}]

    def find_autonomous_ai(self):
        """Search for other autonomous AI projects."""
        queries = [
            "autonomous AI loop heartbeat",
            "autonomous Claude agent",
            "self-running AI",
            "AI continuous operation loop",
        ]
        all_repos = []
        seen = set()
        for q in queries:
            repos = self.search_repos(q, sort="updated", max_results=3)
            for r in repos:
                name = r.get('name', '')
                if name and name not in seen:
                    seen.add(name)
                    all_repos.append(r)
        return all_repos


def _text(element, tag):
    """Get text content of a child element."""
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else ''


def _text_ns(element, tag, ns):
    """Get text content with namespace."""
    child = element.find(tag, ns)
    return child.text.strip() if child is not None and child.text else ''


def _clean_html(text):
    """Strip HTML tags and clean up text."""
    if not text:
        return ''
    text = unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def create_default_reader():
    """Create a feed reader with useful default feeds."""
    reader = FeedReader()
    reader.add_feed("sammy", "https://sammyjankis.com/journal-rss.xml")
    reader.add_feed("hacker-news", "https://hnrss.org/newest?points=100")
    reader.add_feed("arxiv-ai", "http://export.arxiv.org/rss/cs.AI")
    reader.add_feed("lobsters", "https://lobste.rs/rss")
    return reader


if __name__ == "__main__":
    import urllib.parse
    reader = create_default_reader()
    print(reader.digest(max_items_per_feed=3))
