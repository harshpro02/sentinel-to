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

**Status:** blocked until we have an API key.

- `GET https://511on.ca/api/v2/get/event?format=json` returned `400 Invalid Key` without a key.
- `GET https://511on.ca/api/v2/get/cameras?format=json` also returned `400` without a key.
- **Rate limit:** 10 calls per 60 seconds.

### Still to check

- Inspect the real event fields.
- Find out how many Toronto incidents are close to a city camera. Wait or Reroute depends on this.
- Compare 511 cameras with city cameras and remove duplicates.
- Confirm the terms for caching and displaying the data.
