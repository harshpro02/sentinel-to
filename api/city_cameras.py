import asyncio
import math
import re
import time
from datetime import datetime, timezone

import httpx

from api.feeds import FeedUnavailable, coordinates, official_image_url, utc_now


CITY_QUERY = 'https://gis.toronto.ca/arcgis/rest/services/cot_geospatial2/FeatureServer/3/query'


def normalize_city_cameras(features):
    result = []
    for feature in features:
        row = feature.get('attributes', {})
        if not isinstance(row, dict):
            continue
        position = coordinates({'Longitude': row.get('LONGITUDE'), 'Latitude': row.get('LATITUDE')})
        image = official_image_url(row.get('IMAGEURL'))
        if position is None or row.get('REC_ID') is None or not image:
            continue
        result.append({
            'id': f"toronto-camera-{row['REC_ID']}", 'type': 'camera', 'label': 'Street camera',
            'road': row.get('MAINROAD') or 'Toronto street', 'location': row.get('CROSSROAD') or 'Intersection not supplied',
            'city': 'Toronto', 'coordinates': position, 'source': 'City of Toronto', 'provider': 'City of Toronto',
            'direction': 'Provider-controlled view',
            'views': [{'id': 'street', 'description': 'Current City snapshot', 'enabled': True, '_url': image}],
        })
    return result


def distance_m(a, b):
    lat = math.radians((a[1] + b[1]) / 2)
    return 6371000 * math.hypot(math.radians(a[0] - b[0]) * math.cos(lat), math.radians(a[1] - b[1]))


def street_words(value):
    replacements = {'STREET': 'ST', 'AVENUE': 'AVE', 'ROAD': 'RD', 'BOULEVARD': 'BLVD', 'EXPRESSWAY': 'EXPY', 'EAST': 'E', 'WEST': 'W', 'NORTH': 'N', 'SOUTH': 'S'}
    return {replacements.get(word, word) for word in re.findall(r'[A-Z0-9]+', value.upper()) if word not in ('AT', 'NEAR', 'THE')}


def merge_cameras(city, provincial):
    result = [{**item, 'views': [dict(view) for view in item['views']]} for item in city]
    for item in provincial:
        match = None
        if item['provider'].lower() == 'city of toronto':
            words = street_words(f"{item['road']} {item['location']}")
            candidates = []
            for camera in result[:len(city)]:
                distance = distance_m(item['coordinates'], camera['coordinates'])
                city_words = street_words(f"{camera['road']} {camera['location']}")
                if distance <= 25 or distance <= 100 and words and city_words == words:
                    candidates.append((distance, camera))
            if candidates:
                match = min(candidates, key=lambda candidate: candidate[0])[1]
        if match is None:
            result.append(item)
        else:
            known = {view['_url'] for view in match['views']}
            for view in item['views']:
                if view['_url'] not in known:
                    match['views'].append({**view, 'id': f"511-{item['id']}-{view['id']}", 'description': f"511 · {item['road']}: {view['description']}"})
                    known.add(view['_url'])
            match['alsoListedBy'] = 'Ontario 511'
    return result


class CityCameras:
    def __init__(self, client, clock=time.monotonic):
        self.client, self.clock = client, clock
        self.lock = asyncio.Lock()
        self.entry = {'items': [], 'fetchedAt': None, 'attempt': None, 'error': None}

    async def get(self):
        async with self.lock:
            entry = self.entry
            ttl = 60 if entry['error'] else 300
            if entry['attempt'] is None or self.clock() - entry['attempt'] >= ttl:
                entry['attempt'] = self.clock()
                try:
                    response = await self.client.get(CITY_QUERY, params={
                        'f': 'json', 'where': '1=1', 'outFields': 'REC_ID,MAINROAD,CROSSROAD,LATITUDE,LONGITUDE,IMAGEURL',
                        'returnGeometry': 'false', 'resultRecordCount': 1000, 'orderByFields': 'REC_ID',
                    })
                    response.raise_for_status()
                    body = response.json()
                    if not isinstance(body, dict) or body.get('exceededTransferLimit') or not isinstance(body.get('features'), list) or any(not isinstance(feature, dict) for feature in body['features']):
                        raise ValueError()
                    entry.update(items=normalize_city_cameras(body['features']), fetchedAt=utc_now(), error=None)
                except (httpx.HTTPError, ValueError, TypeError):
                    entry['error'] = 'City of Toronto camera locations could not be refreshed.'
            if not entry['fetchedAt']:
                raise FeedUnavailable('City of Toronto cameras are temporarily unavailable.')
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(entry['fetchedAt'])).total_seconds()
            return {'items': entry['items'], 'fetchedAt': entry['fetchedAt'], 'stale': bool(entry['error']) or age > 600, 'message': entry['error'], 'source': 'City of Toronto'}
