import asyncio
import unittest

import httpx
from fastapi.testclient import TestClient

from api.feeds import Feeds, FeedUnavailable, normalize_cameras, normalize_events, official_image_url, public_camera
from api.main import app, bounds


EVENT = {'ID': 12, 'EventType': 'accidentsAndIncidents', 'RoadwayName': 'HWY 401', 'Longitude': -79.4, 'Latitude': 43.7, 'Reported': 1794268800, 'LastUpdated': 1794268860, 'IsFullClosure': False}
CAMERA = {'Id': 5, 'Roadway': 'HWY 401', 'Longitude': -79.4, 'Latitude': 43.7, 'Source': 'COMPASS', 'Views': [{'Id': 10, 'Url': 'https://511on.ca/map/Cctv/10', 'Status': 'Enabled'}]}


class NormalizationTests(unittest.TestCase):
    def test_missing_severity_stays_unknown_and_timestamps_are_utc(self):
        item = normalize_events([EVENT])[0]
        self.assertEqual(item['severity'], 'unknown')
        self.assertEqual(item['sourceSeverity'], 'Unknown')
        self.assertTrue(item['updatedAt'].endswith('+00:00'))

    def test_invalid_locations_are_dropped(self):
        self.assertEqual(normalize_events([{**EVENT, 'Latitude': float('nan')}]), [])
        self.assertEqual(normalize_cameras([{**CAMERA, 'Longitude': 999}]), [])

    def test_image_urls_cannot_escape_official_camera_endpoint(self):
        self.assertEqual(official_image_url('https://511on.ca/map/Cctv/10'), 'https://511on.ca/map/Cctv/10')
        for url in ['http://127.0.0.1/secret', 'https://511on.ca.evil.test/map/Cctv/10', 'https://511on.ca/map/Cctv/10?key=secret', 'https://511on.ca@evil.test/map/Cctv/10', 'https://[bad', 'https://511on.ca/private']:
            self.assertIsNone(official_image_url(url))

    def test_camera_response_hides_upstream_url(self):
        camera = public_camera(normalize_cameras([CAMERA])[0])
        self.assertNotIn('_url', camera['views'][0])
        self.assertEqual(normalize_cameras([{**CAMERA, 'Views': ['invalid']}])[0]['views'], [])

    def test_invalid_bounds_are_rejected(self):
        self.assertEqual(bounds('-80,43,-79,44'), [-80, 43, -79, 44])
        for value in ['-80,43,-81,44', 'NaN,43,-79,44', '1,2,3', '1,2,3,4,5']:
            with self.assertRaises(Exception) as caught:
                bounds(value)
            self.assertEqual(caught.exception.status_code, 422)


class FeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_idle_image_bytes_are_removed_after_fifteen_minutes(self):
        async with httpx.AsyncClient() as client:
            feeds = Feeds(client, 'secret', clock=lambda: 901)
            feeds.images[('5', '10')] = {'checked': 0, 'content': b'old image'}
            feeds.purge_images()
            self.assertEqual(len(feeds.images), 0)

    async def test_concurrent_requests_share_one_upstream_fetch(self):
        calls = []
        async def handler(request):
            calls.append(request)
            await asyncio.sleep(0)
            return httpx.Response(200, json=[EVENT])
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            feeds = Feeds(client, 'test-secret')
            responses = await asyncio.gather(*(feeds.get('event') for _ in range(20)))
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(not response['stale'] for response in responses))
        self.assertNotIn('test-secret', str(responses))

    async def test_failed_refresh_retains_old_data_and_marks_stale(self):
        clock = [0]
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json=[EVENT]) if len(calls) == 1 else httpx.Response(429)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            feeds = Feeds(client, 'test-secret', clock=lambda: clock[0])
            original = await feeds.get('event')
            clock[0] = 61
            stale = await feeds.get('event')
            await feeds.get('event')
        self.assertTrue(stale['stale'])
        self.assertEqual(stale['items'], original['items'])
        self.assertEqual(stale['fetchedAt'], original['fetchedAt'])
        self.assertEqual(len(calls), 2)
        self.assertNotIn('test-secret', str(stale))

    async def test_first_failure_does_not_fabricate_empty_success(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(403))) as client:
            with self.assertRaises(FeedUnavailable) as caught:
                await Feeds(client, 'test-secret').get('event')
        self.assertNotIn('test-secret', str(caught.exception))

    async def test_unchanged_image_is_detected_without_claiming_capture_time(self):
        clock = [0]
        calls = []
        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(200, json=[CAMERA]) if 'get/cameras' in request.url.path else httpx.Response(200, content=b'\xff\xd8\xffimage')
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            feeds = Feeds(client, 'secret', clock=lambda: clock[0])
            first = await feeds.snapshot('511-camera-5', '10')
            cached = await feeds.snapshot('511-camera-5', '10')
            clock[0] = 601
            frozen = await feeds.snapshot('511-camera-5', '10')
        self.assertEqual(first['health'], 'unverified')
        self.assertEqual(first['retrievedAt'], cached['retrievedAt'])
        self.assertTrue(frozen['frozen'])
        self.assertNotIn('capturedAt', frozen)
        self.assertEqual(calls.count('/map/Cctv/10'), 2)

    async def test_disabled_or_unknown_view_never_fetches_an_image(self):
        calls = []
        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(200, json=[{**CAMERA, 'Views': [{**CAMERA['Views'][0], 'Status': 'Disabled'}]}])
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            feeds = Feeds(client, 'secret')
            with self.assertRaises(FeedUnavailable):
                await feeds.snapshot('511-camera-5', '10')
            with self.assertRaises(FeedUnavailable):
                await feeds.snapshot('511-camera-5', '99')
        self.assertEqual(calls, ['/api/v2/get/cameras'])

    async def test_non_image_response_is_not_served(self):
        def handler(request):
            return httpx.Response(200, json=[CAMERA]) if 'get/cameras' in request.url.path else httpx.Response(200, text='<html>offline</html>')
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(FeedUnavailable):
                await Feeds(client, 'secret').snapshot('511-camera-5', '10')


class ApiTests(unittest.TestCase):
    def test_missing_key_returns_503_without_secret_details(self):
        with TestClient(app) as client:
            app.state.feeds.key = ''
            response = client.get('/api/incidents')
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers['retry-after'], '60')


if __name__ == '__main__':
    unittest.main()
