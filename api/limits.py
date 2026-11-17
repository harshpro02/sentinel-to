import math
import time
from collections import deque

from starlette.responses import JSONResponse


class RequestBudget:
    def __init__(self, limit, window=60, max_clients=2048, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.max_clients = max_clients
        self.clock = clock
        self.clients = {}

    def check(self, client):
        now = self.clock()
        cutoff = now - self.window
        if client not in self.clients:
            if len(self.clients) >= self.max_clients:
                self.clients = {key: values for key, values in self.clients.items() if values and values[-1] > cutoff}
            if len(self.clients) >= self.max_clients:
                return 60
            self.clients[client] = deque()
        timestamps = self.clients[client]
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
        if len(timestamps) >= self.limit:
            return max(1, math.ceil(timestamps[0] + self.window - now))
        timestamps.append(now)
        return 0


class PublicRequestLimit:
    def __init__(self, app, limit=120):
        self.app = app
        self.budget = RequestBudget(limit)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'].startswith('/api/') and scope['path'] != '/api/health':
            retry = self.budget.check((scope.get('client') or ('unknown', 0))[0])
            if retry:
                response = JSONResponse({'detail': 'Too many requests. Try again shortly.'}, status_code=429, headers={'Retry-After': str(retry), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
