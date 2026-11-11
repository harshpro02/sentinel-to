import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql

from api.main import app
from api.migrate import main as migrate
from api.storage import IncidentStore, connection_settings


class HistoryApiTests(unittest.TestCase):
    def test_history_failures_do_not_expose_database_details(self):
        with patch.dict(os.environ, {'DATABASE_PASSWORD': ''}):
            with TestClient(app, raise_server_exceptions=False) as client:
                self.assertEqual(client.get('/api/incidents/example/history').status_code, 503)
                store = AsyncMock()
                store.history.side_effect = psycopg.OperationalError('password=do-not-leak host=private-db')
                app.state.store = store
                response = client.get('/api/incidents/example/history')
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('do-not-leak', response.text)
                self.assertNotIn('private-db', response.text)
                self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
                self.assertEqual(response.headers['cache-control'], 'no-store')
                self.assertEqual(client.get('/api/incidents/example/history?limit=101').status_code, 422)
                store.history.side_effect = None
                store.history.return_value = None
                self.assertEqual(client.get('/api/incidents/example/history').status_code, 404)


@unittest.skipUnless(os.getenv('RUN_DATABASE_TESTS') == '1', 'Set RUN_DATABASE_TESTS=1 for real PostgreSQL integration tests')
class StorageTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = 'sentinel_test_' + uuid.uuid4().hex
        cls.admin = {**connection_settings(), 'dbname': 'postgres', 'user': 'sentinel_admin', 'password': os.environ['POSTGRES_PASSWORD']}
        with psycopg.connect(**cls.admin, autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(cls.database)))
        with patch.dict(os.environ, {'DATABASE_NAME': cls.database}):
            migrate()
            migrate()
            cls.settings = connection_settings()

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(**cls.admin, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(cls.database)))

    async def test_changes_survive_new_store_and_ignore_duplicates_and_stale_data(self):
        store = IncidentStore(self.settings)
        item = {'id': '511-event-12', 'description': "Driver's report'; DROP TABLE sentinel.incidents; --", 'source': 'Ontario 511'}
        batch = {'fetchedAt': '2026-11-10T15:00:00+00:00', 'stale': False, 'items': [item]}
        await store.record(batch)
        await store.record(batch)
        await store.record({**batch, 'fetchedAt': '2026-11-10T15:01:00+00:00'})
        history = await IncidentStore(self.settings).history(item['id'], 20)
        self.assertEqual(len(history['versions']), 1)
        self.assertEqual(history['versions'][0]['report'], item)
        self.assertEqual(history['lastSeenAt'], '2026-11-10T15:01:00+00:00')
        changed = {**item, 'description': 'Lane reopened, official report remains active'}
        await store.record({**batch, 'fetchedAt': '2026-11-10T15:02:00+00:00', 'items': [changed]})
        await store.record({**batch, 'fetchedAt': '2026-11-10T15:03:00+00:00', 'stale': True})
        await store.record({**batch, 'fetchedAt': '2026-11-10T15:04:00+00:00', 'items': []})
        history = await store.history(item['id'], 20)
        self.assertEqual(len(history['versions']), 2)
        self.assertEqual(history['lastSeenAt'], '2026-11-10T15:02:00+00:00')
        self.assertEqual(history['versions'][0]['report'], changed)
        self.assertEqual(len((await store.history(item['id'], 1))['versions']), 1)
        self.assertIsNone(await store.history("'; DROP TABLE sentinel.incidents; --", 20))

    async def test_runtime_role_cannot_create_or_drop_tables(self):
        with psycopg.connect(**self.settings) as conn:
            role = conn.execute('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user').fetchone()
            self.assertEqual(role, (False, False, False))
        for statement in ['CREATE TABLE sentinel.forbidden (id int)', 'CREATE TABLE public.forbidden (id int)', 'DROP TABLE sentinel.incidents', 'DELETE FROM sentinel.incidents', 'UPDATE sentinel.incident_versions SET payload = payload']:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(**self.settings) as conn:
                    conn.execute(statement)

    async def test_invalid_batch_rolls_back_all_its_writes(self):
        store = IncidentStore(self.settings)
        valid = {'id': 'rollback-example', 'source': 'Ontario 511'}
        batch = {'fetchedAt': '2026-11-10T16:00:00+00:00', 'stale': False, 'items': [valid, {'id': None}]}
        with self.assertRaises(psycopg.errors.NotNullViolation):
            await store.record(batch)
        self.assertIsNone(await store.history(valid['id'], 20))
        await store.record({**batch, 'items': [valid]})
        self.assertEqual(len((await store.history(valid['id'], 20))['versions']), 1)


if __name__ == '__main__':
    unittest.main()
