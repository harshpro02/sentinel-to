# Sentinel handoff: November 10, 2026

## Completed

- PostgreSQL incident persistence with versioned migrations, first/last observations, changed-report versions and a history API.
- Local database bound to localhost, separate administrator/application credentials, restricted runtime permissions, parameterized queries and generic failure responses.
- Category explorer for all 15 requested 511 categories, with search, on-demand feeds, caching, shared metadata rate limits and explicit source/freshness information.
- GTA-focused map, category icons and hover descriptions, compact result cards, regional navigation and mobile checks. Removed numbered badges, broken heading punctuation and optional Cesium ion branding while preserving map attribution.
- Direct City of Toronto cameras, Downtown shortcut, conservative duplicate location grouping, additional view preservation and source-specific attribution.
- Lazy camera previews, enlarged viewer, zoom, fullscreen and nearby alternatives. Original resolution and unverified capture time remain visible.
- Camera recovery improvements: four concurrent download slots, per-view request sharing, 12-second image download/queue deadline, ten-second failure backoff and useful retry/nearby actions.
- CI configuration includes real isolated PostgreSQL integration tests.

## Validation completed

- 29 backend tests passed, including real PostgreSQL, SQL injection inputs, restricted permissions, provider failures, camera URL/redirect restrictions and independent camera downloads.
- Six frontend tests passed; production build passed.
- Browser checks covered category search, place details, desktop/mobile layout, camera zoom/fullscreen, Escape behaviour and simulated image failure followed by successful retry.
- Configured secrets were checked against source and frontend output without exposing their values. Secrets remain in ignored local configuration. These checks do not establish complete security.

## Next work, in order

1. Add the saved incident timeline to the details panel. Storage and API exist; the timeline is not displayed yet.
2. Resolve contradictory provider records, such as a facility marked Open whose description says closed. Show conflicts explicitly and avoid presenting old status as confirmed availability.
3. Finish visual refinement and reduce initial Cesium loading cost. The illustrated isometric Toronto direction remains a separate small-area prototype, not an implemented renderer.
4. Prepare production serving: containerize frontend/API, complete Docker Compose, configure HTTPS, request limits, health/restart handling, database backup and tested recovery.
5. Deploy to AWS EC2 with an IAM role, scoped permissions, budget review and monitoring. If image storage is introduced, configure S3 and 24-hour retention before enabling it. No AWS resources were created in this session.
6. Build and validate Wait or Reroute using incident history and reliable camera evidence. Vehicle counting, baselines and validated trends remain unimplemented; current trends stay unknown.
7. Add saved places/corridors and relevant alerts. Verify any additional weather or transit source before integration; transit hub locations do not include departures.
8. Measure API latency, loading time, recovery behaviour and AWS costs. Finish clean-checkout deployment instructions and the portfolio walkthrough using measured results.

The planned core release target remains November 16. Public live video is not confirmed and cannot be promised by that date. Current camera views are official still images; source outages and image resolution remain provider limitations.

## Local services

- Frontend: http://127.0.0.1:5173
- API: http://127.0.0.1:8000
- PostgreSQL: localhost port 5433, in a persistent Docker volume.

Services remain available for local review. Work is stopped after this handoff and GitHub push.
