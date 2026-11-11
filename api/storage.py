import asyncio
import hashlib
import json
import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def connection_settings():
    return {
        'host': os.getenv('DATABASE_HOST', '127.0.0.1'),
        'port': int(os.getenv('DATABASE_PORT', '5433')),
        'dbname': os.getenv('DATABASE_NAME', 'sentinel'),
        'user': os.getenv('DATABASE_USER', 'sentinel_app'),
        'password': os.getenv('DATABASE_PASSWORD', ''),
        'connect_timeout': 5,
        'options': '-c statement_timeout=10000 -c lock_timeout=5000',
        'application_name': 'sentinel',
    }


class IncidentStore:
    def __init__(self, settings):
        self.settings = settings
        self.lock = asyncio.Lock()

    async def record(self, batch):
        if batch['stale']:
            return
        async with self.lock:
            await asyncio.to_thread(self._record, batch)

    def _record(self, batch):
        with psycopg.connect(**self.settings) as conn:
            inserted = conn.execute(
                'INSERT INTO sentinel.feed_batches VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING fetched_at',
                (batch['fetchedAt'], len(batch['items'])),
            )
            if not inserted.fetchone():
                return
            for item in batch['items']:
                digest = hashlib.sha256(json.dumps(item, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                previous = conn.execute('SELECT content_hash FROM sentinel.incidents WHERE id = %s', (item['id'],))
                row = previous.fetchone()
                conn.execute(
                    '''INSERT INTO sentinel.incidents VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at,
                    payload = EXCLUDED.payload, content_hash = EXCLUDED.content_hash''',
                    (item['id'], batch['fetchedAt'], batch['fetchedAt'], Jsonb(item), digest),
                )
                if row is None or row[0] != digest:
                    conn.execute(
                        'INSERT INTO sentinel.incident_versions VALUES (%s, %s, %s)',
                        (item['id'], batch['fetchedAt'], Jsonb(item)),
                    )

    async def history(self, incident_id, limit):
        return await asyncio.to_thread(self._history, incident_id, limit)

    def _history(self, incident_id, limit):
        with psycopg.connect(**self.settings, row_factory=dict_row) as conn:
            result = conn.execute(
                'SELECT first_seen_at, last_seen_at FROM sentinel.incidents WHERE id = %s',
                (incident_id,),
            )
            incident = result.fetchone()
            if incident is None:
                return None
            result = conn.execute(
                '''SELECT observed_at, payload FROM sentinel.incident_versions
                WHERE incident_id = %s ORDER BY observed_at DESC LIMIT %s''',
                (incident_id, limit),
            )
            return {
                'id': incident_id,
                'firstSeenAt': incident['first_seen_at'].isoformat(),
                'lastSeenAt': incident['last_seen_at'].isoformat(),
                'versions': [{'observedAt': row['observed_at'].isoformat(), 'report': row['payload']} for row in result.fetchall()],
                'limit': limit,
                'message': 'Observed report changes only. Last seen does not mean the road cleared.',
            }
