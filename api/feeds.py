import asyncio
import hashlib
import math
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat() if value else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def coordinates(row):
    try:
        lon, lat = float(row['Longitude']), float(row['Latitude'])
        return [lon, lat] if math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90 else None
    except (KeyError, ValueError, TypeError):
        return None


def official_image_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme == 'https' and parsed.netloc == '511on.ca' and re.fullmatch(r'/map/Cctv/\d+', parsed.path) and not parsed.query and not parsed.fragment:
        return value
    return None


def normalize_events(rows):
    result = []
    types = {'roadwork': ('construction', 'Roadwork'), 'closures': ('incident', 'Closure'), 'accidentsAndIncidents': ('incident', 'Road incident')}
    for row in rows:
        position = coordinates(row)
        kind = types.get(row.get('EventType'))
        if not position or not kind or row.get('ID') is None:
            continue
        result.append({
            'id': f"511-event-{row['ID']}", 'type': kind[0], 'label': kind[1],
            'road': row.get('RoadwayName') or 'Unnamed road',
            'location': row.get('DirectionOfTravel') or 'Direction not supplied',
            'city': '', 'title': row.get('LanesAffected') or 'See official report',
            'description': row.get('Description') or 'No description supplied.',
            'coordinates': position, 'severity': 'high' if row.get('IsFullClosure') else 'medium' if kind[0] == 'construction' else 'unknown',
            'source': 'Ontario 511', 'organization': row.get('Organization') or 'Not supplied',
            'reportedAt': timestamp(row.get('Reported')), 'updatedAt': timestamp(row.get('LastUpdated')),
            'startsAt': timestamp(row.get('StartDate')), 'plannedEndAt': timestamp(row.get('PlannedEndDate')),
            'schedule': row.get('Recurrence') or '', 'comment': row.get('Comment') or '',
            'fullClosure': bool(row.get('IsFullClosure')), 'sourceSeverity': row.get('Severity') or 'Unknown',
        })
    return sorted(result, key=lambda item: (item['type'] == 'construction', -(datetime.fromisoformat(item['updatedAt']).timestamp() if item['updatedAt'] else 0)))


def normalize_cameras(rows):
    result = []
    for row in rows:
        position = coordinates(row)
        if not position or row.get('Id') is None:
            continue
        views = []
        raw_views = row.get('Views')
        for view in raw_views if isinstance(raw_views, list) else []:
            if not isinstance(view, dict):
                continue
            url = official_image_url(view.get('Url'))
            if url and view.get('Id') is not None:
                views.append({'id': str(view['Id']), 'description': view.get('Description') or 'Camera view', 'enabled': view.get('Status') == 'Enabled', '_url': url})
        result.append({'id': f"511-camera-{row['Id']}", 'type': 'camera', 'label': 'Camera', 'road': row.get('Roadway') or 'Unnamed road', 'location': row.get('Location') or 'Location not supplied', 'city': '', 'coordinates': position, 'source': 'Ontario 511', 'provider': row.get('Source') or 'Unknown provider', 'direction': row.get('Direction') or 'Unknown', 'views': views})
    return result


class FeedUnavailable(Exception):
    pass


class Feeds:
    def __init__(self, client, key, clock=time.monotonic):
        self.client, self.key, self.clock = client, key, clock
        self.cache = {}
        self.locks = {'event': asyncio.Lock(), 'cameras': asyncio.Lock()}
        self.images = OrderedDict()
        self.image_lock = asyncio.Lock()

    def purge_images(self):
        for key, entry in list(self.images.items()):
            if self.clock() - entry['checked'] >= 900:
                self.images.pop(key, None)

    async def get(self, name):
        async with self.locks[name]:
            entry = self.cache.setdefault(name, {'items': [], 'fetchedAt': None, 'attempt': None, 'error': None})
            ttl = 60 if name == 'event' or entry['error'] else 300
            if entry['attempt'] is None or self.clock() - entry['attempt'] >= ttl:
                entry['attempt'] = self.clock()
                try:
                    if not self.key:
                        raise FeedUnavailable()
                    response = await self.client.get(f'https://511on.ca/api/v2/get/{name}', params={'key': self.key, 'format': 'json'})
                    response.raise_for_status()
                    rows = response.json()
                    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                        raise ValueError()
                    entry['items'] = normalize_events(rows) if name == 'event' else normalize_cameras(rows)
                    entry['fetchedAt'] = utc_now()
                    entry['error'] = None
                except (httpx.HTTPError, ValueError, TypeError, FeedUnavailable):
                    entry['error'] = 'Ontario 511 could not be refreshed. Conditions may have changed.'
            if not entry['fetchedAt']:
                raise FeedUnavailable('Ontario 511 is unavailable. Check the server configuration and try again shortly.')
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(entry['fetchedAt'])).total_seconds()
            return {'items': entry['items'], 'fetchedAt': entry['fetchedAt'], 'stale': bool(entry['error']) or age > (120 if name == 'event' else 600), 'message': entry['error'], 'source': 'Ontario 511'}

    async def snapshot(self, camera_id, view_id):
        self.purge_images()
        cameras = await self.get('cameras')
        camera = next((item for item in cameras['items'] if item['id'] == camera_id), None)
        view = next((item for item in camera['views'] if item['id'] == view_id), None) if camera else None
        if not view or not view['enabled']:
            raise FeedUnavailable('This official camera view is unavailable.')
        key = (camera_id, view_id)
        async with self.image_lock:
            now = self.clock()
            previous = self.images.get(key)
            if previous and now - previous['checked'] < 60:
                self.images.move_to_end(key)
                return previous
            try:
                async with self.client.stream('GET', view['_url']) as response:
                    response.raise_for_status()
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 3_000_000:
                            raise ValueError()
                content = bytes(data)
                media_type = 'image/jpeg' if content.startswith(b'\xff\xd8\xff') else 'image/png' if content.startswith(b'\x89PNG\r\n\x1a\n') else None
                if not media_type:
                    raise ValueError()
            except (httpx.HTTPError, ValueError):
                raise FeedUnavailable('Camera image unavailable. Road conditions are unknown.') from None
            digest = hashlib.sha256(content).hexdigest()
            changed = previous['changed'] if previous and previous['hash'] == digest else now
            entry = {'content': content, 'media_type': media_type, 'hash': digest, 'checked': now, 'changed': changed, 'retrievedAt': utc_now(), 'health': 'unchanged' if previous and digest == previous['hash'] else 'unverified', 'frozen': now - changed >= 600}
            self.images[key] = entry
            self.images.move_to_end(key)
            while len(self.images) > 64:
                self.images.popitem(last=False)
            return entry


def public_camera(item):
    return {**item, 'views': [{key: value for key, value in view.items() if key != '_url'} for view in item['views']]}
