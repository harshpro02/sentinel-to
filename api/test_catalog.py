import unittest

import httpx

from api.catalog import RESOURCES, decode_polyline, normalize_resource
from api.feeds import Feeds, FeedUnavailable


class CatalogTests(unittest.TestCase):
    def test_places_return_only_explicit_public_fields_and_readable_facts(self):
        row = {'Id': 1, 'Name': '<script>example</script>', 'Latitude': 43.7, 'Longitude': -79.4, 'Lavatory': 'Y', 'Fuel': 'N', 'Website': 'javascript:alert(1)', 'private': 'secret'}
        for category in RESOURCES:
            if category in ('road-conditions', 'construction'):
                continue
            item = normalize_resource(category, [row])[0]
            self.assertNotIn('Website', item)
            self.assertNotIn('private', item)
            self.assertEqual(next(fact['value'] for fact in item['facts'] if fact['label'] == 'Washrooms'), 'Yes')
            self.assertEqual(next(fact['value'] for fact in item['facts'] if fact['label'] == 'Fuel'), 'No')
        self.assertEqual(normalize_resource('rest-areas', [{**row, 'Latitude': float('nan')}]), [])

    def test_road_conditions_decode_segments_and_do_not_claim_old_data_is_current(self):
        encoded = '_p~iF~ps|U_ulLnnqC_mqNvxq`@'
        self.assertEqual(decode_polyline(encoded), [[-120.2, 38.5], [-120.95, 40.7], [-126.453, 43.252]])
        item = normalize_resource('road-conditions', [{'RoadwayName': '17', 'EncodedPolyline': [encoded], 'Condition': ['No Report'], 'LastUpdated': 1580824842}])[0]
        self.assertTrue(item['conditionUnknown'])
        self.assertEqual(item['road'], '17')
        self.assertEqual(len(item['segments'][0]), 3)
        for invalid in ['_', '~' * 50, 'bad', None]:
            self.assertEqual(decode_polyline(invalid), [])
        self.assertEqual(normalize_resource('road-conditions', [{'EncodedPolyline': 'bad'}]), [])


class ResourceFeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_categories_share_rate_limit_and_reject_arbitrary_endpoints(self):
        calls = []
        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(200, json=[])
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            feeds = Feeds(client, 'test-private-key', clock=lambda: 0)
            names = list(RESOURCES)
            for name in names[:8]:
                await feeds.get(name)
            with self.assertRaises(FeedUnavailable):
                await feeds.get(names[8])
            with self.assertRaises(FeedUnavailable):
                await feeds.get('https://private-host/secret')
            await feeds.get(names[0])
        self.assertEqual(len(calls), 8)
        self.assertIn('/api/v3/get/roadconditions', calls)

    async def test_static_places_are_cached_longer_than_incidents(self):
        clock, calls = [0], []
        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(200, json=[])
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            feeds = Feeds(client, 'secret', clock=lambda: clock[0])
            await feeds.get('transit-hubs')
            clock[0] = 301
            await feeds.get('transit-hubs')
            clock[0] = 3601
            await feeds.get('transit-hubs')
        self.assertEqual(len(calls), 2)
