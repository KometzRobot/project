#!/usr/bin/env python3
"""
web-fetch.py — Fetch a URL and extract readable text content.
Gives Meridian eyes on the web.
Usage: python3 web-fetch.py <url> [max_chars]
"""
import sys, urllib.request, urllib.error, re

def fetch_url(url, max_chars=4000):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; KometzRobot/1.0; +https://kometzrobot.github.io)'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get('Content-Type', '')
            raw = resp.read()

            # Detect encoding
            enc = 'utf-8'
            if 'charset=' in content_type:
                enc = content_type.split('charset=')[-1].split(';')[0].strip()

            html = raw.decode(enc, errors='replace')
            return html
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except Exception as e:
        return f"Error: {e}"

def strip_html(html):
    # Remove scripts and styles
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    # Convert common tags to text
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<p[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</p>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<h[1-6][^>]*>', '\n## ', html, flags=re.IGNORECASE)
    html = re.sub(r'</h[1-6]>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li[^>]*>', '\n- ', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    # Clean whitespace
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'&lt;', '<', html)
    html = re.sub(r'&gt;', '>', html)
    html = re.sub(r'&quot;', '"', html)
    html = re.sub(r'&#\d+;', '', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    html = re.sub(r'  +', ' ', html)
    return html.strip()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 web-fetch.py <url> [max_chars]")
        sys.exit(1)

    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 4000

    print(f"Fetching: {url}")
    html = fetch_url(url)

    if html.startswith('HTTP Error') or html.startswith('Error:'):
        print(html)
        sys.exit(1)

    text = strip_html(html)
    print(f"\n{'='*60}")
    print(text[:max_chars])
    if len(text) > max_chars:
        print(f"\n... [truncated — {len(text)} total chars]")
