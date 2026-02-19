"""
meridian.api_tools
HTTP/REST API client for autonomous agents.
No external dependencies.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Optional, Any


class APIResponse:
    """Wrapper for HTTP response data."""

    def __init__(self, status: int, body: str, content_type: str = ''):
        self.status       = status
        self.body         = body
        self.content_type = content_type
        self.ok           = 200 <= status < 300

    def json(self) -> Any:
        """Parse body as JSON. Raises ValueError if not valid JSON."""
        return json.loads(self.body)

    def json_safe(self, default=None) -> Any:
        """Parse body as JSON, return default if parsing fails."""
        try:
            return json.loads(self.body)
        except:
            return default

    def __repr__(self):
        return f'APIResponse(status={self.status}, ok={self.ok}, body_len={len(self.body)})'


class APIClient:
    """
    Minimal HTTP client for REST APIs.

    Example:
        client = APIClient(base_url='https://api.example.com',
                           headers={'Authorization': 'Bearer token'})
        resp = client.get('/users/me')
        data = resp.json()
    """

    def __init__(self,
                 base_url: str = '',
                 headers: Optional[Dict[str, str]] = None,
                 timeout: int = 15,
                 user_agent: str = 'meridian/0.1'):
        self.base_url   = base_url.rstrip('/')
        self.headers    = headers or {}
        self.timeout    = timeout
        self.headers.setdefault('User-Agent', user_agent)

    def _request(self, method: str, url: str,
                 body: Optional[Any] = None,
                 extra_headers: Optional[Dict] = None) -> APIResponse:
        if not url.startswith('http'):
            url = self.base_url + url

        all_headers = {**self.headers, **(extra_headers or {})}
        data = None
        if body is not None:
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode('utf-8')
                all_headers.setdefault('Content-Type', 'application/json')
            elif isinstance(body, str):
                data = body.encode('utf-8')
            else:
                data = body

        req = urllib.request.Request(url, data=data, method=method.upper())
        for k, v in all_headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
                ct  = r.headers.get('Content-Type', '')
                return APIResponse(r.status, raw.decode('utf-8', errors='replace'), ct)
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', errors='replace')
            return APIResponse(e.code, raw)
        except Exception as e:
            return APIResponse(0, str(e))

    def get(self, path: str, params: Optional[Dict] = None,
            headers: Optional[Dict] = None) -> APIResponse:
        url = path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        return self._request('GET', url, extra_headers=headers)

    def post(self, path: str, body: Any = None,
             headers: Optional[Dict] = None) -> APIResponse:
        return self._request('POST', path, body=body, extra_headers=headers)

    def put(self, path: str, body: Any = None) -> APIResponse:
        return self._request('PUT', path, body=body)

    def delete(self, path: str) -> APIResponse:
        return self._request('DELETE', path)


# ── Convenience functions ──────────────────────────────────────────────────────

def get_public_ip() -> Dict:
    """Get public IP and geolocation info."""
    client = APIClient()
    resp = client.get('https://ipapi.co/json/')
    if resp.ok:
        data = resp.json_safe({})
        return {
            'ip':       data.get('ip', '?'),
            'city':     data.get('city', '?'),
            'region':   data.get('region', '?'),
            'country':  data.get('country_name', '?'),
            'isp':      data.get('org', '?'),
            'timezone': data.get('timezone', '?'),
            'lat':      data.get('latitude'),
            'lon':      data.get('longitude'),
        }
    return {'error': f'HTTP {resp.status}'}


def get_weather(city: str = 'Calgary') -> Dict:
    """Get current weather for a city using wttr.in."""
    client = APIClient()
    city_enc = urllib.parse.quote(city)
    resp = client.get(f'https://wttr.in/{city_enc}?format=j1')
    if not resp.ok:
        return {'error': f'HTTP {resp.status}'}
    data = resp.json_safe({})
    try:
        current = data['current_condition'][0]
        return {
            'description': current['weatherDesc'][0]['value'],
            'temp_c':      current['temp_C'],
            'feels_like_c': current['FeelsLikeC'],
            'humidity':    current['humidity'],
            'wind_kmph':   current['windspeedKmph'],
            'wind_dir':    current['winddir16Point'],
            'city':        city,
        }
    except Exception as e:
        return {'error': str(e)}


def fetch_text(url: str, max_chars: int = 5000) -> str:
    """
    Fetch a URL and return its text content.
    For HTML, strips tags.
    """
    from html.parser import HTMLParser

    class S(HTMLParser):
        def __init__(self):
            super().__init__()
            self._t = []
        def handle_data(self, d):
            self._t.append(d)
        def get_text(self):
            return '\n'.join(self._t)

    client = APIClient()
    resp = client.get(url)
    if not resp.ok:
        return f'Error: HTTP {resp.status}'

    body = resp.body
    if 'html' in resp.content_type.lower():
        h = S()
        h.feed(body)
        body = h.get_text()

    return body[:max_chars]
