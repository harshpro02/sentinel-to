"""Log Ontario 511 incidents once a minute to data/events.jsonl."""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

URL = "https://511on.ca/api/v2/get/event"
POLL_SECONDS = 60
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "events.jsonl"


def fetch_incidents(client: httpx.Client, key: str) -> list[dict]:
    response = client.get(URL, params={"format": "json", "key": key})
    response.raise_for_status()
    return [e for e in response.json() if e.get("EventType") == "accidentsAndIncidents"]


def save(incidents: list[dict]) -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    record = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "incidents": incidents,
    }
    with OUTPUT.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="poll one time, then exit")
    args = parser.parse_args()

    load_dotenv()
    key = os.environ["ONTARIO_511_API_KEY"]

    with httpx.Client(timeout=30, headers={"User-Agent": "sentinel-to"}) as client:
        while True:
            try:
                incidents = fetch_incidents(client, key)
                save(incidents)
                print(f"logged {len(incidents)} incidents", flush=True)
            except (httpx.HTTPError, ValueError) as error:
                # The URL contains the key, so print only the error type.
                print(f"poll failed: {type(error).__name__}", flush=True)

            if args.once:
                break
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
