import unittest
from datetime import datetime, timedelta, timezone

from api.trend import assess


def report(severity='medium', full_closure=False, title='Two lanes', source='Moderate', description='Lanes affected.'):
    return {'severity': severity, 'fullClosure': full_closure, 'title': title, 'sourceSeverity': source, 'description': description}


def version(report_payload, minutes_ago, base):
    observed = (base - timedelta(minutes=minutes_ago)).isoformat()
    return {'observedAt': observed, 'report': report_payload}


def history(versions, first_minutes, last_minutes, base):
    return {
        'firstSeenAt': (base - timedelta(minutes=first_minutes)).isoformat(),
        'lastSeenAt': (base - timedelta(minutes=last_minutes)).isoformat(),
        'versions': versions,
    }


class AssessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

    def test_no_history_is_unknown(self):
        outcome = assess(None, self.now)
        self.assertEqual(outcome['status'], 'unknown')
        self.assertEqual(outcome['confidence'], 'none')

    def test_single_recent_observation_is_unknown(self):
        versions = [version(report(), 2, self.now)]
        outcome = assess(history(versions, 2, 0, self.now), self.now)
        self.assertEqual(outcome['status'], 'unknown')
        self.assertEqual(outcome['observations'], 1)

    def test_single_long_lived_observation_is_report_unchanged(self):
        versions = [version(report(), 40, self.now)]
        outcome = assess(history(versions, 40, 0, self.now), self.now)
        self.assertEqual(outcome['status'], 'unchanged')
        self.assertEqual(outcome['confidence'], 'low')

    def test_escalation_to_full_closure_is_worse(self):
        versions = [
            version(report(severity='high', full_closure=True), 2, self.now),
            version(report(severity='medium'), 30, self.now),
        ]
        outcome = assess(history(versions, 30, 0, self.now), self.now)
        self.assertEqual(outcome['status'], 'increased')
        self.assertIn('fullClosure', outcome['changedFields'])

    def test_deescalation_is_reduced_report_impact(self):
        versions = [
            version(report(severity='medium'), 2, self.now),
            version(report(severity='high', full_closure=True), 30, self.now),
        ]
        outcome = assess(history(versions, 30, 0, self.now), self.now)
        self.assertEqual(outcome['status'], 'reduced')

    def test_version_count_does_not_increase_confidence(self):
        versions = [
            version(report(severity='high'), 2, self.now),
            version(report(severity='medium'), 15, self.now),
            version(report(severity='low'), 30, self.now),
        ]
        outcome = assess(history(versions, 30, 0, self.now), self.now)
        self.assertEqual(outcome['status'], 'increased')
        self.assertEqual(outcome['confidence'], 'low')

    def test_updates_without_severity_change_are_report_unchanged(self):
        versions = [
            version(report(description='Updated note.'), 2, self.now),
            version(report(description='First note.'), 30, self.now),
        ]
        outcome = assess(history(versions, 30, 0, self.now), self.now)
        self.assertEqual(outcome['status'], 'unchanged')
        self.assertIn('description', outcome['changedFields'])

    def test_confidence_remains_unvalidated_and_low(self):
        versions = [version(report(severity='high' if index % 2 else 'low'), index * 5, self.now) for index in range(6)]
        outcome = assess(history(versions, 30, 0, self.now), self.now)
        self.assertIn(outcome['confidence'], {'none', 'low'})


    def test_stale_history_stays_unknown(self):
        versions = [version(report('high'), 10, self.now), version(report('low'), 30, self.now)]
        outcome = assess(history(versions, 30, 10, self.now), self.now)
        self.assertEqual(outcome['status'], 'unknown')

    def test_missing_severity_is_not_improvement(self):
        versions = [version(report('unknown'), 1, self.now), version(report('high'), 30, self.now)]
        self.assertEqual(assess(history(versions, 30, 0, self.now), self.now)['status'], 'unknown')

    def test_latest_change_is_compared_instead_of_oldest_baseline(self):
        versions = [version(report('medium'), 1, self.now), version(report('high'), 15, self.now), version(report('low'), 30, self.now)]
        self.assertEqual(assess(history(versions, 30, 0, self.now), self.now)['status'], 'reduced')

    def test_missing_naive_and_future_times_are_unknown(self):
        versions = [version(report('high'), 1, self.now), version(report('low'), 30, self.now)]
        for value in [None, 'invalid', '2026-11-16T12:00:00', (self.now + timedelta(minutes=10)).isoformat()]:
            with self.subTest(value=value):
                data = history(versions, 30, 0, self.now)
                data['lastSeenAt'] = value
                self.assertEqual(assess(data, self.now)['status'], 'unknown')

    def test_history_endpoint_includes_report_comparison(self):
        import os
        from unittest.mock import AsyncMock, patch
        from fastapi.testclient import TestClient
        from api.main import app

        now = datetime.now(timezone.utc)
        data = history([version(report('medium'), 1, now), version(report('high'), 20, now)], 20, 0, now)
        with patch.dict(os.environ, {'DATABASE_PASSWORD': ''}):
            with TestClient(app) as client:
                app.state.store = AsyncMock()
                app.state.store.history.return_value = data
                response = client.get('/api/incidents/example/history?limit=2')
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload['assessment']['status'], 'reduced')
                self.assertEqual(payload['assessment']['confidence'], 'low')
                self.assertEqual(payload['versions'], data['versions'])
                app.state.store.history.assert_awaited_once_with('example', 2)

if __name__ == '__main__':
    unittest.main()
