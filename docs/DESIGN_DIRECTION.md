# Sentinel visual direction

Latest reference, November 9: [Isometric Toronto](https://iso.sloptoronto.ca/) and the author's [method](https://iso.sloptoronto.ca/how). This supersedes the earlier preference for a plain street map as the final visual treatment. The working GTA map remains available while the new presentation is evaluated.

## What to carry into Sentinel

- A city canvas that occupies most of the screen, with recognizable blocks and restrained controls.
- A consistent isometric angle: parallel edges keep their scale instead of distant buildings shrinking like a perspective photograph.
- Muted building colours, green parks, quiet water and crisp edges. Keep incident colours distinct from the base illustration.
- Compact search and layer controls; details open on selection.
- Continuous zoom and responsive panning, with regional context and a reliable GTA reset.

## What the reference actually does

The author's method describes geographically aligned city renders transformed into a large illustration, served as tiled images through a deep-zoom viewer. Four separately rendered/drawn angles support rotation. The site credits OpenSeadragon, city/open geographic data and an image-model illustration pipeline. This is a different rendering pipeline from Sentinel's current Cesium street map.

The illustration and any animated traffic must remain distinct from official camera evidence and reported incidents. Sentinel's coordinates, source times and camera warnings remain grounded in the real feeds. Do not animate invented traffic as a live measurement.

## Implementation boundary

First prove a small Toronto area using reusable or independently produced, correctly registered map assets. Establish the geographic-to-image coordinate transform before placing real reports over it. Check source reuse conditions, geographic registration, readable markers, mobile loading and pan/zoom performance before expanding to the GTA. Ontario-wide views need coverage/fallback behaviour rather than stretching Toronto artwork to other places.

No external artwork or tile collection has been copied into the product. Source code and underlying artwork/data/model terms are separate questions. The current change is a researched design direction, not a completed illustrated renderer.

## Delivery order

Target the first working AWS preview around November 12 to 13 and the core portfolio release by November 16. Finish the container/serving path, HTTPS, server-only configuration, health/restart behaviour and cost review before exposing the preview. Keep the illustration experiment bounded so a visual redesign does not indefinitely delay a usable deployment. These are planning targets, not completed deployments.
