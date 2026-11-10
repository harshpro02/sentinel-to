# Seven-day release plan

Working window: November 9–16, 2026, Toronto time. This replaces the earlier November 12 target. Target a working, explainable AWS release; do not claim the full feature list is already implemented.

| Day | Deliverable |
| --- | --- |
| Nov 9–10 | Ontario map UI, regional navigation, local preview and keyboard/mobile checks; skyline removed at user's request |
| Nov 10–11 | FastAPI and province-wide official 511 ingestion, freshness and failure states |
| Nov 11–12 | PostgreSQL persistence, migrations, source timestamps, incident details and timeline |
| Nov 12–13 | Official camera discovery and health states; only authorized video sources, otherwise explicitly labelled images |
| Nov 13–14 | Saved places/corridors and relevant alerts; verify additional weather/transit sources before integrating |
| Nov 14–15 | Docker Compose, EC2, IAM-role access, S3 retention, logging, HTTPS and cost review |
| Nov 15–16 | Failure/recovery checks, measured performance, clean-checkout instructions, public demo and portfolio walkthrough |

Video access is not guaranteed by this timeline. Do not fabricate a stream, use synthetic footage as evidence, or label images live video.

Keep the original Wait or Reroute feature explainable: default to unknown without adequate evidence. Vehicle counts alone cannot establish that an incident cleared or that an alternative route is faster. Validate any trend claim against official incident histories.

Ontario-wide scope supersedes Toronto-only scope. Ontario 511 is the province-wide source; city-specific sources require separate coverage labels. A province-wide map does not imply complete reporting on every municipal road. Camera availability and source permissions must be verified per provider.

Additional layers follow after the core release if source access or validation takes longer. Prioritize complete user journeys and verified evidence. Provision AWS only within the documented budget and report resource costs before leaving them running.

# Portfolio evidence

Record measured ingestion delay, API latency under a stated load, camera failure handling, deployment/recovery steps and actual cost. Document tradeoffs and limitations. Use only measured results in resume bullets; do not invent users, speedups, savings or accuracy.
