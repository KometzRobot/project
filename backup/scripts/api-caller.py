#!/usr/bin/env python3
"""
MERIDIAN APPENDAGE: api-caller.py
Hit any REST API endpoint, save/display results.
Usage:
  python3 api-caller.py get <url> [--headers k:v ...] [--save filename]
  python3 api-caller.py post <url> <json_body> [--headers k:v ...]
  python3 api-caller.py weather [city]
  python3 api-caller.py public-ip
  python3 api-caller.py time [timezone]

Results are printed to stdout and optionally saved to /tmp/api-results/
"""

import sys, os, json, urllib.request, urllib.error
from datetime import datetime

SAVE_DIR = '/tmp/api-results'

def api_request(method, url, body=None, headers=None, timeout=15):
    if headers is None:
        headers = {}
    headers.setdefault('User-Agent', 'KometzRobot/1.0')
    if body is not None:
        headers.setdefault('Content-Type', 'application/json')
        data = json.dumps(body).encode('utf-8') if isinstance(body, dict) else body.encode('utf-8')
    else:
        data = None

    req = urllib.request.Request(url, data=data, method=method.upper())
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            content_type = resp.headers.get('Content-Type', '')
            raw = resp.read()
            text = raw.decode('utf-8', errors='replace')
            return {'status': status, 'content_type': content_type, 'body': text, 'ok': True}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', errors='replace')
        return {'status': e.code, 'content_type': '', 'body': raw, 'ok': False, 'error': str(e)}
    except Exception as e:
        return {'status': 0, 'content_type': '', 'body': '', 'ok': False, 'error': str(e)}


def display_result(result, save_as=None):
    print(f'\nStatus: {result["status"]} {"OK" if result["ok"] else "ERROR"}')
    if not result['ok'] and 'error' in result:
        print(f'Error: {result["error"]}')
    body = result['body']
    ct = result.get('content_type', '')

    # Try to pretty-print JSON
    if 'json' in ct or (body.strip().startswith('{') or body.strip().startswith('[')):
        try:
            parsed = json.loads(body)
            body = json.dumps(parsed, indent=2)
        except:
            pass

    print('\n' + body[:3000])
    if len(body) > 3000:
        print(f'\n... ({len(body) - 3000} more chars)')

    if save_as:
        os.makedirs(SAVE_DIR, exist_ok=True)
        path = os.path.join(SAVE_DIR, save_as)
        with open(path, 'w') as f:
            f.write(f'# API Result — {datetime.now()}\n')
            f.write(f'# Status: {result["status"]}\n\n')
            f.write(body)
        print(f'\nSaved to: {path}')


def cmd_get(args):
    if len(args) < 1:
        print('Usage: api-caller.py get <url> [--headers k:v ...] [--save filename]')
        return
    url = args[0]
    headers = {}
    save_as = None
    i = 1
    while i < len(args):
        if args[i] == '--headers' and i+1 < len(args):
            i += 1
            while i < len(args) and ':' in args[i] and not args[i].startswith('--'):
                k, v = args[i].split(':', 1)
                headers[k.strip()] = v.strip()
                i += 1
        elif args[i] == '--save' and i+1 < len(args):
            save_as = args[i+1]
            i += 2
        else:
            i += 1
    print(f'\nGET {url}')
    result = api_request('GET', url, headers=headers)
    display_result(result, save_as)


def cmd_post(args):
    if len(args) < 2:
        print('Usage: api-caller.py post <url> <json_body>')
        return
    url = args[0]
    body = args[1]
    print(f'\nPOST {url}')
    print(f'Body: {body[:200]}')
    result = api_request('POST', url, body=body)
    display_result(result)


def cmd_weather(args):
    """Get weather using wttr.in (no API key needed)."""
    city = args[0] if args else 'Calgary'
    city_encoded = urllib.parse.quote(city) if ',' not in city else city
    url = f'https://wttr.in/{city_encoded}?format=j1'
    print(f'\nWeather for: {city}')
    result = api_request('GET', url)
    if not result['ok']:
        print(f'Error: {result.get("error")}')
        return
    try:
        import urllib.parse
        data = json.loads(result['body'])
        current = data['current_condition'][0]
        desc = current['weatherDesc'][0]['value']
        temp_c = current['temp_C']
        feels_c = current['FeelsLikeC']
        humidity = current['humidity']
        wind_kmph = current['windspeedKmph']
        wind_dir = current['winddir16Point']
        print(f'\n  Condition : {desc}')
        print(f'  Temp      : {temp_c}°C (feels like {feels_c}°C)')
        print(f'  Humidity  : {humidity}%')
        print(f'  Wind      : {wind_kmph} km/h {wind_dir}')
        # Nearest area
        near = data.get('nearest_area', [{}])[0]
        area = near.get('areaName', [{}])[0].get('value', '?')
        country = near.get('country', [{}])[0].get('value', '?')
        print(f'  Location  : {area}, {country}')
    except Exception as e:
        print(f'Parse error: {e}')
        print(result['body'][:500])


def cmd_public_ip():
    """Get public IP and geolocation."""
    print('\nPublic IP lookup...')
    result = api_request('GET', 'https://ipapi.co/json/')
    if not result['ok']:
        print(f'Error: {result.get("error")}')
        return
    try:
        data = json.loads(result['body'])
        print(f'\n  IP       : {data.get("ip","?")}')
        print(f'  City     : {data.get("city","?")}')
        print(f'  Region   : {data.get("region","?")}')
        print(f'  Country  : {data.get("country_name","?")}')
        print(f'  ISP      : {data.get("org","?")}')
        print(f'  Timezone : {data.get("timezone","?")}')
        print(f'  Lat/Lon  : {data.get("latitude","?")}, {data.get("longitude","?")}')
    except Exception as e:
        print(f'Parse error: {e}')


def cmd_time(args):
    """Get current time for a timezone."""
    import urllib.parse as up
    tz = args[0] if args else 'America/Denver'
    url = f'https://worldtimeapi.org/api/timezone/{up.quote(tz)}'
    print(f'\nTime in {tz}:')
    result = api_request('GET', url)
    if not result['ok']:
        # Fallback: list timezones
        result2 = api_request('GET', 'https://worldtimeapi.org/api/timezone')
        if result2['ok']:
            timezones = json.loads(result2['body'])
            matching = [t for t in timezones if tz.lower() in t.lower()]
            print(f'  Available matching "{tz}": {matching[:10]}')
        return
    try:
        data = json.loads(result['body'])
        print(f'\n  Datetime  : {data.get("datetime","?")}')
        print(f'  Timezone  : {data.get("timezone","?")}')
        print(f'  UTC Offset: {data.get("utc_offset","?")}')
        print(f'  Day of Year: {data.get("day_of_year","?")}')
        print(f'  Week Num  : {data.get("week_number","?")}')
    except Exception as e:
        print(f'Parse error: {e}')


def print_usage():
    print(__doc__)


if __name__ == '__main__':
    import urllib.parse

    args = sys.argv[1:]
    if not args:
        print_usage()
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == 'get':
        cmd_get(args[1:])
    elif cmd == 'post':
        cmd_post(args[1:])
    elif cmd == 'weather':
        cmd_weather(args[1:])
    elif cmd == 'public-ip':
        cmd_public_ip()
    elif cmd == 'time':
        cmd_time(args[1:])
    else:
        print(f'Unknown command: {cmd}')
        print_usage()
