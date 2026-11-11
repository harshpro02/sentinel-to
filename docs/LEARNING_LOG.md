# Learning log

## November 9, 2026 :  Explore frontend and Toronto skyline

Built a React/Vite Explore screen with demonstration incidents, road search, layer filtering, incident details, keyboard access, responsive layout and localhost hot reload. Replaced the initial MapLibre implementation with CesiumJS at Harsh's request. Added a downtown subset of the City's 2025 3D Massing geometry and a return-to-skyline control. No AWS resources were provisioned.

Concepts explained: React components are reusable UI pieces; state remembers selections; Vite runs the local server and builds deployable files; hot reload updates the preview after saves; Cesium renders geographic 3D scenes; building footprints plus heights become simplified 3D buildings; Web Mercator stores coordinates in metres and must be converted to longitude/latitude.

Implementation corrections: the Cesium component initially omitted a React import, causing a black screen; added the import and checked the browser. The source archive's filename included WGS84 but its projection file specified Web Mercator; converted the geometry rather than treating metres as degrees. No user misconception was established.

Source code contains no comments by user request. Explanations belong here and in chat.

The user clarified that the miniature skyline reference describes the presentation, not permission to invent or reposition buildings. Preserve municipal footprints and source heights; do not claim roof, façade or landmark accuracy from average-height extrusions. Replaced thousands of per-building entities with batched static geometry, preserving polygon holes and multipolygon parts. This reduces per-object overhead; frame rate still needs measurement on the user's hardware.

Validation: three filtering tests passed. A headless browser check passed desktop/mobile rendering, building-load completion, search, incident details, layer toggles, empty-state reset and return-to-skyline. No page JavaScript errors or horizontal mobile overflow were observed. The production build includes a substantial Cesium bundle; optimize download and measure rendering before release.

Interview question: Why must a stale or offline camera produce unknown conditions?

Model answer: An unchanged image cannot establish present traffic conditions. I separate source availability from road status and expose timestamps so missing evidence never silently becomes a clearing or safe-road claim.

## November 9, 2026 :  Ontario map direction

At Harsh's request, removed the skyline renderer and bundled building geometry, keeping the street map as the main view. Expanded the interface to Sentinel Ontario with southern/eastern/northern/province navigation and fictional examples in Ottawa, London, Sudbury and Thunder Bay as well as Toronto. City names are searchable. The preview still uses demo data; province-wide official ingestion and AWS deployment remain upcoming work.

Concepts: a camera preset stores a centre, viewing angle and distance for repeatable map navigation; regional map navigation does not restrict the incident list. Removing the skyline avoids downloading its approximately 5 MB geometry file and preparing thousands of buildings. No measured frame-rate improvement is claimed.

Validation: four search/filter tests and the production build passed. The browser check passed Ontario desktop/mobile rendering, city search, incident details, regional navigation, full-province reset, layer filters and empty-state reset. No building-geometry requests, page errors or horizontal mobile overflow were observed.

Naming correction: the product is Sentinel, with no TO, ON or Ontario suffix. Ontario remains the coverage area. Updated header, accessible home label, page metadata, package name and current documentation.

Default view correction: centre the map on the GTA at a closer camera distance, with a GTA return button. Keep all Ontario accessible from the regional selector. A camera distance controls the visible map area; a smaller distance zooms closer without restricting the geographic coverage of the application.

## November 9, 2026 :  Official reports and camera evidence

Connected Ontario 511 events and cameras through FastAPI. Added region queries, source timestamps, stale/error states, report and camera lists, nearby camera links, still-image viewing and manual refresh. The application no longer imports demo records. Kept traffic trend unknown rather than inferring road clearance from images.

Concepts explained: FastAPI serves browser data requests; a shared cache reuses feed results within the source refresh interval; the API key belongs only on the server; camera Enabled and HTTP success do not prove image freshness. A bounding box filters by west/south/east/north coordinates. An image hash compares content without identifying vehicles.

Images stay in a bounded memory cache, with 60-second reuse and idle-byte deletion after fifteen minutes plus the cleanup interval. Identical observations ten minutes apart produce a potential-frozen warning. Capture time remains unverified. AWS infrastructure, PostgreSQL history, vehicle counts and verified video remain upcoming work.

Verified live feed responses and a JPEG snapshot. The browser check passed actual report display, source times, snapshot rendering, camera warnings, mobile fit, absence of the API key in browser request URLs and a no-demo failure state. Added backend regression tests for shared requests, stale data, missing keys, bounds, unofficial image URLs, disabled views and content validation. Added CI for backend tests and frontend build/tests.

Interview question: How do you avoid exhausting an upstream rate limit when many users open the app?

Model answer: Cache the full upstream response on the server and share one in-flight fetch using a lock. Apply user-specific geographic filtering after retrieval. A single cache owner bounds upstream calls independently of browser count; scaling to several workers requires a shared cache or dedicated fetcher.

## November 9: Isometric reference and deployment planning

Inspected Isometric Toronto's public page, reference image, credits and method. Its illustrated image tiles use a deep-zoom presentation, rather than merely tilting Sentinel's existing street map. Recorded the visual direction and a small-area prototype boundary; no new illustrated renderer or third-party tile layer has been added to the app.

Read the relevant local Claude memory and chat records. Preserve short explanations, interview ownership and no em dashes in public writing. Career/resume research stays outside the public project. The desired recent resume redesign was not found in the available local transcripts, so clarification is pending instead of inventing a prior decision.
# November 10, 2026: PostgreSQL incident history

Built local PostgreSQL storage with versioned SQL migrations and a dedicated runtime role. A background collector shares the 511 cache, stores first/last observations, and saves changed report versions atomically. Added a bounded history endpoint, generic database errors, API response headers, and suppressed HTTP client request logs to avoid logging upstream query credentials.

Concepts: persistence survives process restarts; a transaction commits a whole batch or rolls it back; parameterized SQL sends data separately from SQL instructions; least privilege gives the running app only the permissions it needs. No source-code comments were added.

Validation: 17 backend tests passed, including real isolated PostgreSQL tests for repeat migrations, stale/duplicate handling, history persistence, SQL injection inputs and denied schema changes. Four frontend tests and the production build passed. Local smoke check recorded 462 official reports and served history through Vite. Current configured secrets were not found in tracked files, Git patches or frontend output. This scan does not establish that all possible vulnerabilities are absent. Frontend still has the existing large Cesium bundle warning.

Limitations: observed report changes do not prove road clearance; no historical data before collection began; history UI, AWS, HTTPS, public request limits and backup/recovery automation remain to implement. Local container data lives in a persistent Docker volume, not Git. AWS resources were not provisioned.

Interview question: Why use different database accounts for migrations and the API? Model answer: migrations need permission to change the schema, while normal requests only need to read and write report data. Restricting the runtime account limits damage if a request path is compromised.

## November 10: Map readability pass

Reduced the header and sidebar footprint, centered the map in the remaining desktop space, brightened street imagery, removed the dimming overlay and tightened the GTA starting view. Added screen-space marker clustering with report counts and click-to-zoom. Selected reports remain visible independently; source data and API handling are unchanged.

Concept: clustering groups nearby screen positions at the current zoom, not administrative areas or incident severity. Counts change as users zoom or toggle layers. The list remains available for individual report selection.

Validation: inspected the desktop screenshot; browser checks exercised a cluster-area click, report selection, back navigation, GTA reset and a 390-pixel mobile viewport without JavaScript errors or horizontal overflow. Four existing frontend tests and the production build passed. The existing Cesium bundle-size warning remains. Illustrated isometric rendering is still a separate prototype.

## November 10: Explore categories instead of a report wall

Replaced report/camera tabs with a category explorer. Six common choices appear first; All categories reveals all 15 from the user's reference. Category-name search leads into on-demand feeds, and loaded results can be searched by location, road or amenities. Cards lead with the official impact or place name and a clear action. Numbered clusters were replaced by category icons with descriptive hover labels. Nearby groups zoom in when clicked.

Connected 13 additional allowlisted 511 feeds, including construction projects, v3 road conditions, transit hubs, rest areas, service centres, carpool lots, ferries and commercial travel facilities. Shared a sliding-window metadata request budget across feeds and used longer caches for static places. Road-condition polylines are decoded into map segments; source updates older than six hours or No Report are explicitly unknown. Found old source updates during live verification and added the warning rather than treating successful retrieval as current evidence.

Validation: 21 backend tests passed, including normalization, geometry decoding, source freshness, rate limits, SQL injection inputs and real PostgreSQL persistence. Six frontend tests passed. Live smoke checks returned records from all 13 added feeds. GTA examples included 31 transit hubs, 12 rest-area records, 6 service centres and 69 condition segments. Browser checks verified category search, all 15 options, rest-area details, back navigation and mobile width without JavaScript errors or horizontal overflow. External map imagery can take time to sharpen; the existing Cesium bundle-size warning remains.

Concepts: on-demand fetching avoids downloading every layer at once; one shared request budget protects provider access; retrieval freshness and the age of a source observation are separate. Neither a facility listing nor a provider status proves real-time availability. No verified live video or full transit schedules were added.
