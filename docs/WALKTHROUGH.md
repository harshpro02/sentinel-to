# Sentinel: two-minute walkthrough

Use the public address only after deployment is verified. Until then use the local preview and explicitly describe it as local. Before presenting, choose a report with stored history and a camera that currently returns an image; source availability can change.

## 0:00-0:20: problem

“Sentinel brings Ontario road reports and nearby official camera snapshots into one place. The useful part is showing what the sources actually reported, when Sentinel observed it, and where evidence is missing.”

## 0:20-1:05: demonstrate

Start over the GTA, select an incident, then show Report history.

“This comes from Ontario 511. The history records the first and last time Sentinel saw the report and versions saved when its content changed. This card compares the latest two versions. A reduced reported impact is not the same as confirmed clearance, so traffic trend remains unknown.”

Open a nearby camera and, if available, its enlarged still image.

“These are official snapshots, not verified live video. A successful download does not prove capture freshness. If an image is unavailable or appears frozen, the interface shows that uncertainty rather than calling the road clear.”

## 1:05-1:40: engineering decision

“The API key stays on the server. A shared cache and request budget bound upstream requests even when several visitors open the map. Geographic filtering happens after the upstream fetch. PostgreSQL stores report versions in a transaction, while the runtime account has fewer permissions than the migration account. A provider or database failure has a separate state, so missing history does not silently become a fake live report.”

If production has been verified, show its HTTPS address and deployment/restore evidence. Otherwise say the container release was tested locally and AWS is pending.

## 1:40-2:00: limitation

“Official coverage is incomplete and source updates may be old. Report changes and still images do not establish vehicle speed or a faster alternative route. Counting and validated Wait or Reroute predictions remain future work. I would rather show unknown than offer confident advice without evidence.”

## Questions to practise

- Why do multiple API workers need a shared cache or dedicated fetcher?
- How do retrieval time and source observation time differ?
- What does a successful restore check prove, and what remains to test on AWS?

Do not claim AWS, S3 image storage, prediction accuracy or public uptime until verified.
