import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response

from api.feeds import Feeds, FeedUnavailable, public_camera
from api.storage import IncidentStore, connection_settings
from api.catalog import RESOURCES
from api.city_cameras import CityCameras, merge_cameras

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=20, headers={'User-Agent': 'Sentinel/0.2'}, follow_redirects=False) as client:
        app.state.feeds = Feeds(client, os.getenv('ONTARIO_511_API_KEY', ''))
        app.state.city_cameras = CityCameras(client)
        app.state.store = IncidentStore(connection_settings()) if os.getenv('DATABASE_PASSWORD') else None
        app.state.storage_status = 'starting' if app.state.store else 'disabled'
        async def cleanup():
            while True:
                await asyncio.sleep(60)
                app.state.feeds.purge_images()
        task = asyncio.create_task(cleanup())
        async def collect():
            while True:
                try:
                    batch = await app.state.feeds.get('event')
                    await app.state.store.record(batch)
                    app.state.storage_status = 'stale' if batch['stale'] else 'ok'
                except FeedUnavailable:
                    app.state.storage_status = 'feed unavailable'
                except psycopg.Error:
                    app.state.storage_status = 'unavailable'
                    logging.getLogger('sentinel').warning('Incident storage unavailable; retrying without connection details.')
                await asyncio.sleep(60)
        collector = asyncio.create_task(collect()) if app.state.store else None
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            if collector:
                collector.cancel()
                with suppress(asyncio.CancelledError):
                    await collector


app = FastAPI(title='Sentinel API', lifespan=lifespan)


@app.get('/api/health')
async def health():
    return {'status': 'ok', 'feedConfigured': bool(os.getenv('ONTARIO_511_API_KEY')), 'storage': app.state.storage_status}


@app.middleware('http')
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response


def in_bounds(item, bbox):
    lon, lat = item['coordinates']
    return bbox is None or bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def bounds(value):
    if value is None:
        return None
    try:
        box = [float(part) for part in value.split(',')]
        if len(box) != 4 or not (-180 <= box[0] < box[2] <= 180 and -90 <= box[1] < box[3] <= 90):
            raise ValueError()
        return box
    except ValueError:
        raise HTTPException(422, 'bbox must be west,south,east,north in geographic degrees') from None


async def feed(name):
    try:
        return await app.state.feeds.get(name)
    except FeedUnavailable as error:
        raise HTTPException(503, str(error), headers={'Retry-After': '60'}) from None


@app.get('/api/incidents')
async def incidents(bbox: str | None = Query(default=None)):
    box = bounds(bbox)
    result = await feed('event')
    return {**result, 'items': [item for item in result['items'] if in_bounds(item, box)]}


@app.get('/api/cameras')
async def cameras(bbox: str | None = Query(default=None)):
    box = bounds(bbox)
    result = await camera_catalog()
    return {**result, 'items': [public_camera(item) for item in result['items'] if in_bounds(item, box)]}


async def camera_catalog():
    city, provincial = await asyncio.gather(app.state.city_cameras.get(), app.state.feeds.get('cameras'), return_exceptions=True)
    available = [result for result in (city, provincial) if isinstance(result, dict)]
    if not available:
        raise HTTPException(503, 'Official camera sources are temporarily unavailable.', headers={'Retry-After': '60'})
    city_items = city['items'] if isinstance(city, dict) else []
    provincial_items = provincial['items'] if isinstance(provincial, dict) else []
    partial = len(available) < 2 or any(result['stale'] for result in available)
    return {
        'items': merge_cameras(city_items, provincial_items),
        'fetchedAt': max(result['fetchedAt'] for result in available), 'stale': partial,
        'message': 'Some camera sources are unavailable or delayed; coverage may be incomplete.' if partial else None,
        'source': 'City of Toronto + Ontario 511',
        'sources': [{'name': name, 'available': isinstance(result, dict), 'fetchedAt': result.get('fetchedAt') if isinstance(result, dict) else None, 'stale': result.get('stale', True) if isinstance(result, dict) else True} for name, result in [('City of Toronto', city), ('Ontario 511', provincial)]],
    }


@app.get('/api/explore/{category}')
async def explore(category: str, bbox: str | None = Query(default=None)):
    if category not in RESOURCES:
        raise HTTPException(404, 'Unknown explore category.')
    box = bounds(bbox)
    result = await feed(category)
    def visible(item):
        if item.get('segments'):
            return box is None or any(box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3] for segment in item['segments'] for point in segment)
        return in_bounds(item, box)
    return {**result, 'items': [item for item in result['items'] if visible(item)]}


@app.get('/api/incidents/{incident_id}/history')
async def incident_history(incident_id: str, limit: int = Query(default=20, ge=1, le=100)):
    if not app.state.store:
        raise HTTPException(503, 'Incident history is not configured.')
    try:
        result = await app.state.store.history(incident_id, limit)
    except psycopg.Error:
        raise HTTPException(503, 'Incident history is temporarily unavailable.') from None
    if result is None:
        raise HTTPException(404, 'No recorded history for this report.')
    return result


@app.get('/api/cameras/{camera_id}/views/{view_id}/snapshot')
async def snapshot(camera_id: str, view_id: str):
    try:
        catalog = None
        if camera_id.startswith('toronto-camera-'):
            catalog = await app.state.city_cameras.get() if view_id == 'street' else await camera_catalog()
        image = await app.state.feeds.snapshot(camera_id, view_id, catalog=catalog)
    except FeedUnavailable as error:
        raise HTTPException(503, str(error), headers={'Retry-After': '10'}) from None
    return Response(image['content'], media_type=image['media_type'], headers={
        'Cache-Control': 'no-store',
        'X-Sentinel-Retrieved-At': image['retrievedAt'],
        'X-Sentinel-Camera-Health': 'frozen' if image['frozen'] else image['health'],
        'X-Content-Type-Options': 'nosniff',
    })
