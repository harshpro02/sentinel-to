# Data sources

Checked on Nov 6, 2026.

## City of Toronto traffic cameras

**Status:** working, no key needed.

- **Camera list:** [ArcGIS layer 3](https://gis.toronto.ca/arcgis/rest/services/cot_geospatial2/FeatureServer/3) returned 336 cameras, all with an `IMAGEURL`.
- **Useful fields:** `REC_ID`, `MAINROAD`, `CROSSROAD`, `LATITUDE`, `LONGITUDE`, `IMAGEURL`.
- **Image URL format:** `https://opendata.toronto.ca/transportation/tmc/rescucameraimages/CameraImages/loc8001.jpg`
- **Sample images:** 2 of 2 returned `200 image/jpeg`, at about 100 to 120 KB each.
- **Image contents:** the sample was a small snapshot, with the location and time printed on it.
- **Freshness:** the 2 samples were about 2 minutes old when fetched. `Cache-Control` is `max-age=60`.
- **Comparison images:** `REFURL1` to `REFURL4` point to comparison images by direction. Their purpose is still to be confirmed.

### Still to check

- Measure the real refresh interval over several fetches.
- Confirm the licence and whether frames can be rehosted on a public page.
- Test YOLO accuracy on these small images.

## Ontario 511

**Status:** working with an API key stored in `.env`.

- **Endpoints:** `/api/v2/get/event` and `/api/v2/get/cameras`, using `format=json` and a `key` query parameter.
- **Rate limit:** 10 calls per 60 seconds.
- **Useful event fields:** `ID`, `RoadwayName`, `DirectionOfTravel`, `Description`, `Reported`, `LastUpdated`, `LanesAffected`, `Latitude`, `Longitude`, `EventType`, `IsFullClosure`.
- **Useful camera fields:** `Id`, `Source`, `Roadway`, `Location`, `Latitude`, `Longitude`, `Views`.

### Snapshot: Friday Nov 6, about 4 pm

These counts use a rough Toronto bounding box, which also catches some nearby areas.

| Measure | Result |
|---|---|
| Events in the box | 80 (79 roadwork, 1 incident) |
| Incidents across Ontario | 2 |
| Events within 1 km of a city camera | 41 of 80 |
| Events within 1 km of a 511 camera | 80 of 80 |
| 511 cameras in the box | 192 (114 COMPASS, 74 City of Toronto, 4 RWIS) |

The one incident was a disabled vehicle on Highway 401 at Kennedy Road, with a COMPASS camera about 0.1 km away.

### Camera images

- `Views[].Url` returns a JPEG, for example `https://511on.ca/map/Cctv/710`.
- No video field appears in the API response. The fields only give image links.
- **COMPASS sample:** 1920x1080, about 5 minutes old when fetched.
- **RWIS sample:** 800x450, about 17 minutes old when fetched.
- `Last-Modified` showed the fetch time on the RWIS sample, so it can't be trusted for image age. Use image changes and the time printed on the image instead.

### Decision

Use COMPASS highway cameras for Wait or Reroute, because 511 incidents are mostly on highways. Keep city cameras as a separate street layer.

### Still to check

- Log events over several days, because incidents were rare in this one snapshot.
- Repeat the COMPASS refresh test at other times of day. On Nov 6, 5 cameras all changed over 10 minutes, usually every 172 to 179 seconds, with gaps of 206 and 275 seconds also seen.
- Remove duplicates between the 74 City of Toronto cameras in 511 and the city layer.
- Confirm the terms for caching, displaying and rehosting 511 data and images.
- Decide whether to downscale images before storing them, because COMPASS images are much sharper.
