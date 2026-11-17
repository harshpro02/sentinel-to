import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.limits import PublicRequestLimit, RequestBudget


class RequestBudgetTests(unittest.TestCase):
    def test_clients_are_independent_and_budget_recovers(self):
        clock = [0]
        budget = RequestBudget(2, clock=lambda: clock[0])
        self.assertEqual(budget.check('a'), 0)
        self.assertEqual(budget.check('a'), 0)
        self.assertEqual(budget.check('a'), 60)
        self.assertEqual(budget.check('b'), 0)
        clock[0] = 60
        self.assertEqual(budget.check('a'), 0)

    def test_memory_cap_does_not_evict_active_clients(self):
        clock = [0]
        budget = RequestBudget(1, max_clients=1, clock=lambda: clock[0])
        self.assertEqual(budget.check('a'), 0)
        self.assertGreater(budget.check('b'), 0)
        self.assertEqual(len(budget.clients), 1)
        clock[0] = 61
        self.assertEqual(budget.check('b'), 0)
        self.assertEqual(len(budget.clients), 1)

    def test_health_is_exempt_and_rejection_is_explicit(self):
        app = FastAPI()
        app.add_middleware(PublicRequestLimit, limit=1)
        @app.get('/api/example')
        def example():
            return {'ok': True}
        @app.get('/api/health')
        def health():
            return {'status': 'ok'}
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/example').status_code, 200)
            response = client.get('/api/example')
            self.assertEqual(response.status_code, 429)
            self.assertGreater(int(response.headers['retry-after']), 0)
            self.assertEqual(client.get('/api/health').status_code, 200)
