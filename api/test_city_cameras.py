import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from api.city_cameras import CityCameras, merge_cameras, normalize_city_cameras
from api.feeds import Feeds, FeedUnavailable, normalize_cameras, official_image_url, public_camera
from api.main import app


CITY_IMAGE = 'https://opendata.toronto.ca/transportation/tmc/rescucameraimages/CameraImages/loc8032.jpg'
FEATURE = {'attributes': {'REC_ID': 8032, 'MAINROAD': 'YONGE ST', 'CROSSROAD': 'DUNDAS ST', 'LATITUDE': 43.656238, 'LONGITUDE': -79.381033, 'IMAGEURL': CITY_IMAGE}}
PROVINCIAL = {'Id': 10, 'Roadway': 'Yonge Street', 'Location': 'Dundas Street', 'Latitude': 43.65624, 'Longitude': -79.38103, 'Source': 'City of Toronto', 'Views': [{'Id': 20, 'Url': 'https://511on.ca/map/Cctv/20', 'Status': 'Enabled'}]}


class CityNormalizationTests(unittest.TestCase):
    def test_city_urls_are_tightly_restricted_and_private_urls_stay_hidden(self):
        self.assertEqual(official_image_url(CITY_IMAGE), CITY_IMAGE)
        for url in [CITY_IMAGE + '?token=private', CITY_IMAGE.replace('opendata.toronto.ca', 'opendata.toronto.ca.evil.test'), CITY_IMAGE.replace('https:', 'http:'), 'https://opendata.toronto.ca/private', 'https://opendata.toronto.ca/transportation/tmc/rescucameraimages/CameraImages/../secret', 'https://127.0.0.1/loc8032.jpg']:
            self.assertIsNone(official_image_url(url))
            self.assertEqual(normalize_city_cameras([{'attributes': {**FEATURE['attributes'], 'IMAGEURL': url}}]), [])
        item = normalize_city_cameras([FEATURE])[0]
        self.assertEqual(item['source'], 'City of Toronto')
        self.assertNotIn('_url', public_camera(item)['views'][0])
        self.assertEqual(normalize_city_cameras([{'attributes': None}]), [])

    def test_duplicate_locations_merge_views_without_merging_other_providers(self):
        city = normalize_city_cameras([FEATURE])
        provincial = normalize_cameras([PROVINCIAL, {**PROVINCIAL, 'Id': 11, 'Source': 'COMPASS'}])
        result = merge_cameras(city, provincial)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'toronto-camera-8032')
        self.assertEqual(len(result[0]['views']), 2)
        self.assertEqual(result[0]['alsoListedBy'], 'Ontario 511')
        self.assertEqual(len(city[0]['views']), 1)
        nearby = normalize_cameras([{**PROVINCIAL, 'Location': 'Nearby pole', 'Latitude': 43.656418}])
        self.assertEqual(len(merge_cameras(city, nearby)), 1)
        far = normalize_cameras([{**PROVINCIAL, 'Latitude': 44}])
        self.assertEqual(len(merge_cameras(city, far)), 2)


class CityFeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_city_requests_share_cache_and_preserve_stale_metadata(self):
        calls, clock = [], [0]
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={'features': [FEATURE]}) if len(calls) == 1 else httpx.Response(503)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = CityCameras(client, clock=lambda: clock[0])
            results = await asyncio.gather(*(source.get() for _ in range(10)))
            self.assertEqual(len(calls), 1)
            self.assertNotIn('key', calls[0].url.params)
            clock[0] = 301
            stale = await source.get()
            self.assertTrue(stale['stale'])
            self.assertEqual(stale['items'], results[0]['items'])
            await source.get()
            self.assertEqual(len(calls), 2)

    async def test_incomplete_city_metadata_is_not_reported_as_complete(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'features': [FEATURE], 'exceededTransferLimit': True}))) as client:
            with self.assertRaises(FeedUnavailable):
                await CityCameras(client).get()

    async def test_city_png_with_jpeg_header_is_served_as_png_and_redirects_are_rejected(self):
        camera = normalize_city_cameras([FEATURE])[0]
        catalog = {'items': [camera]}
        content = b'\x89PNG\r\n\x1a\nimage'
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=content, headers={'content-type': 'image/jpeg'}))) as client:
            image = await Feeds(client, '').snapshot(camera['id'], 'street', catalog=catalog)
            self.assertEqual(image['media_type'], 'image/png')
        calls = []
        def redirect(request):
            calls.append(request.url.host)
            return httpx.Response(302, headers={'location': 'http://127.0.0.1/private'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(redirect), follow_redirects=False) as client:
            with self.assertRaises(FeedUnavailable):
                await Feeds(client, '').snapshot(camera['id'], 'street', catalog=catalog)
        self.assertEqual(calls, ['opendata.toronto.ca'])


class CombinedCameraApiTests(unittest.TestCase):
    def test_city_cameras_work_without_511_and_partial_coverage_is_explicit(self):
        with patch.dict(os.environ, {'DATABASE_PASSWORD': '', 'ONTARIO_511_API_KEY': ''}), TestClient(app) as client:
            city = normalize_city_cameras([FEATURE])
            app.state.city_cameras.get = AsyncMock(return_value={'items': city, 'fetchedAt': '2026-11-10T12:00:00+00:00', 'stale': False, 'message': None})
            app.state.feeds.get = AsyncMock(side_effect=FeedUnavailable('test'))
            response = client.get('/api/cameras?bbox=-79.42,43.63,-79.35,43.68')
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(len(body['items']), 1)
            self.assertTrue(body['stale'])
            self.assertIn('incomplete', body['message'])
            self.assertNotIn(CITY_IMAGE, response.text)
            app.state.city_cameras.get = AsyncMock(side_effect=FeedUnavailable('test'))
            self.assertEqual(client.get('/api/cameras').status_code, 503)
