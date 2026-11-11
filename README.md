# Sentinel

An Ontario road awareness map built from official Ontario 511 reports and camera information. Opens over the GTA, with province-wide regional navigation, searchable reports, source timestamps and nearby official camera snapshots.

**Wait or Reroute, in progress:** traffic trends currently remain unknown. Official reports and nearby images supply evidence; snapshots alone do not establish speed, clearance or a faster alternative route. Vehicle counting and validated trend analysis remain planned.

**Status:** in progress.

## Local development

Requires Python 3.10+ and Node.js 22.12+ (developed with Node 24). Create an Ontario 511 developer key through the [official developer resources](https://511on.ca/developers/resources).

From the repository root, set up the backend:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api\requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set `ONTARIO_511_API_KEY` in `.env`. Preserve an existing `.env` when repeating setup. Never put this key in a `VITE_` variable or frontend code.

For incident history, start Docker Desktop and set two different, randomly generated passwords in `.env`: `POSTGRES_PASSWORD` for database administration and `DATABASE_PASSWORD` for the application. Do not use the placeholder values or share the file. Leave the other database settings at their example defaults for local development.

```powershell
docker compose up -d --wait db
.\.venv\Scripts\python.exe -m api.migrate
```

The database listens on `127.0.0.1:5433`, not the LAN. Migrations run separately using the administrator account; the API uses a restricted application role that cannot create or drop tables. The Docker volume preserves reports across container and API restarts. `docker compose down` stops the database without deleting its volume. Do not add `-v` unless you intend to delete the stored history.

With `DATABASE_PASSWORD` configured, one background collector shares the existing 511 cache and records fresh province-wide events every 60 seconds. It records first/last observations and a version when report content changes. Stale responses are skipped and duplicate batches are ignored. An absent report does not establish clearance. No camera images or user location histories are stored in PostgreSQL.

Without database configuration the existing live feed still works; history returns 503. A database outage does not prevent the live-feed routes from responding. `/api/health` reports storage status separately. Keep one API process while this collector and rate limiter are process-local. Stop the older `fetcher/log_events.py` logger if running so it does not make redundant upstream requests.

Start the backend in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir api
```

Start the frontend in another terminal:

```powershell
cd web
npm ci
npm run dev -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173. Keep the server running to see frontend changes automatically.

The Vite development server proxies `/api` to FastAPI on port 8000. Search matches road names, report details and camera providers. The region selector changes the feed query bounds as well as the map view. Road reports and cameras have separate lists; the Cameras list enables camera markers. An incident lists up to four cameras within 5 km, without claiming they face the incident's direction.

Real feed failures show an error or clearly marked stale results; the running app never silently substitutes demo incidents. The old `demo.js` data remains solely for the existing filtering tests and is not imported by the live application.

## Checks

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s api -t . -v
```

To include real PostgreSQL tests with the local database running:

```powershell
$env:RUN_DATABASE_TESTS = '1'
.\.venv\Scripts\python.exe -m unittest discover -s api -t . -v
Remove-Item Env:RUN_DATABASE_TESTS
```

These integration tests create and delete a separate randomly named test database. They verify idempotent migrations, persistence, duplicate/stale handling, SQL injection inputs and runtime permissions. CI runs them against PostgreSQL too.

From `web/`:

```powershell
npm test
npm run build
```

The production output is `web/dist/`, including Cesium's required static assets. The initial Cesium bundle is substantial; download and frame-rate optimization remain release work. Production serving, HTTPS and AWS deployment are not implemented yet.

## Feed and camera behaviour

| Endpoint | Behaviour |
| --- | --- |
| `/api/health` | App health and whether a feed key is configured; never returns the key |
| `/api/incidents?bbox=west,south,east,north` | Official events, source report times, retrieval time and stale status |
| `/api/incidents/{id}/history?limit=20` | Latest observed report versions, bounded to 100 per request; 404 for unrecorded IDs, 503 when storage is unavailable |
| `/api/cameras?bbox=west,south,east,north` | Official camera metadata and view availability; no upstream image URLs or API keys |
| `/api/cameras/{id}/views/{view}/snapshot` | Size-limited JPEG/PNG from an allowlisted official image endpoint, retrieved time and limited health evidence |

The backend shares one cached events response for 60 seconds and camera metadata for 300 seconds. Failed feed attempts back off for 60 seconds. Use one API worker while this in-memory cache owns rate limiting; multiple workers/instances need a shared fetcher or cache. Ontario 511 limits developer calls to 10 per 60 seconds.

Camera images are requested only when a view is selected or manually refreshed. The backend caches a successful view for 60 seconds, caps the cache at 64 images, and purges idle image bytes after 15 minutes with a cleanup loop running every minute. Images are not saved to disk or S3 by this implementation. Browser object URLs are revoked when the view changes.

Capture time is unverified, even when HTTP succeeds or the API says Enabled. The provider can return an offline notice as a JPEG. Repeated hashes identify unchanged images; the same image observed at least ten minutes apart is labelled potentially frozen. Fresh-looking, blank, frozen and unavailable views never establish that a road is clear.

## Map coverage and attribution

The street map uses OpenStreetMap imagery with attribution visible in the viewer. No skyline geometry, Cesium ion token or paid building service is used. Ontario 511 supplies province-wide road reports, but this does not imply every municipal street is monitored. Regional bounding boxes are approximate navigation/filter extents, not administrative boundaries.

Ontario 511 data is provided as available and may differ from actual road conditions. Source attribution links to [Ontario 511](https://511on.ca/). See its [Developer Access Agreement](https://511on.ca/developers/resources) and [Open Government Licence - Ontario](https://www.ontario.ca/page/open-government-licence-ontario). Publicly accessible source images remain subject to their provider's applicable terms; Sentinel does not claim endorsement or control of camera availability. No verified video stream is integrated.

## Planned AWS deployment

The local Compose file currently starts PostgreSQL only. The API and frontend still run on the host. AWS, HTTPS, backups, public request limits and full production container serving remain release work. Supply only runtime credentials to the deployed API, keep the administrator credentials for migration jobs, and never expose the database port publicly. HTTP client request logs are disabled at INFO/DEBUG levels because upstream URLs contain the feed key. Do not enable verbose HTTP tracing with real credentials.

```text
Official feeds → Python fetcher → PostgreSQL + S3 images (24-hour retention)
                                     ↓
                              FastAPI → React/Cesium
Docker Compose on EC2; S3 access through an EC2 IAM role
```

See [delivery plan](docs/DELIVERY_PLAN.md) and [learning log](docs/LEARNING_LOG.md).

It uses official public feeds only. Planned counting excludes identifying or tracking people and vehicles. It is a public awareness tool, not an emergency service, and should be used before travelling.
