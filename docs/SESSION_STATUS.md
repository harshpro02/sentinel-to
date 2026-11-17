# Sentinel status: November 17, 2026

## Current release

- AWS EC2 release is live at https://sentinel.54.162.93.68.sslip.io. Crossing shares the host at https://exchange.54.162.93.68.sslip.io.
- One t3.small host in us-east-1, encrypted 20 GiB gp3 disk, public HTTP/HTTPS only, private PostgreSQL containers and scoped instance role. Administration uses Systems Manager.
- Released Sentinel tag `a977dcbc1d52` and Crossing tag `22e9f48b4590`. The first attempt exposed a short Java startup grace period; the production override now allows 120 seconds before enforcing startup health.
- Verified public HTTPS, fresh Ontario 511 feed (451 records at verification), incident history, mobile layout and actual 80/20 trade execution. Browser check had no page errors. Missing static assets return 404.
- Both databases were backed up to private S3 storage and restored into isolated databases: 451 incidents/451 versions and 10 orders/2 trades. Production data was not overwritten. Nightly backup is configured.
- Backend tests: 42 passed and three database-dependent tests skipped in this run; frontend six passed and production build succeeded. Crossing 62 unit tests passed. The existing Cesium bundle warning remains.
- Estimated baseline around USD 21/month before credits, taxes, traffic, registry and backup storage. Remaining credits have not been verified. Review Billing regularly; the budget alarm does not stop spending.
- Next: measure loading and API latency, reduce initial bundle cost, handle contradictory provider records and validate future traffic trend features. Vehicle counting, verified live video and traffic predictions are not implemented.

## Historical handoff: November 10, 2026

The sections below preserve the earlier handoff. The current release above supersedes its deployment status and next-work list.

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

1. Saved incident history is now displayed in the details panel (November 15): latest 20 versions, changed fields, observation times and independent failure/retry states. Continue with contradictory provider records below.
2. Resolve contradictory provider records, such as a facility marked Open whose description says closed. Show conflicts explicitly and avoid presenting old status as confirmed availability.
3. Finish visual refinement and reduce initial Cesium loading cost. The illustrated isometric Toronto direction remains a separate small-area prototype, not an implemented renderer.
4. Prepare production serving: containerize frontend/API, complete Docker Compose, configure HTTPS, request limits, health/restart handling, database backup and tested recovery.
5. Deploy to AWS EC2 with an IAM role, scoped permissions, budget review and monitoring. If image storage is introduced, configure S3 and 24-hour retention before enabling it. No AWS resources were created in this session.
6. History now includes a report-impact comparison (November 16), with freshness checks and report-only labels. Validate Wait or Reroute using reliable camera evidence before making traffic predictions. Vehicle counting, traffic baselines and validated traffic trends remain unimplemented; traffic trends stay unknown.
7. Add saved places/corridors and relevant alerts. Verify any additional weather or transit source before integration; transit hub locations do not include departures.
8. Measure API latency, loading time, recovery behaviour and AWS costs. Finish clean-checkout deployment instructions and the portfolio walkthrough using measured results.

The planned core release target remains November 16. Public live video is not confirmed and cannot be promised by that date. Current camera views are official still images; source outages and image resolution remain provider limitations.

## Local services

- Frontend: http://127.0.0.1:5173
- API: http://127.0.0.1:8000
- PostgreSQL: localhost port 5433, in a persistent Docker volume.

Services remain available for local review. Work is stopped after this handoff and GitHub push.
