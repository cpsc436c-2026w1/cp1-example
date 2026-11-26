"""The count by zone over 30 days, read from one compacted file a day (RF040).

Local code for the nightly job `t00-compact-events` and the count query that reads table `trip_events_compacted`.
The job of day D reads the small files of raw/trip-events/dt=D/ and of dt=D+1/hour=00/ (a request of D received
after midnight; R020 takes them up to 10 minutes late), keeps the requests with an event time on D, and writes them
as one file, trip_events_compacted/dt=D/. Here a folder stands in for the bucket and the file is CSV (standard
library only); on AWS the Glue job writes Parquet and Athena runs the count. Neither is deployed at Checkpoint 2
(docs/design.md, Resources; the RF040 example is tagged @todo).
"""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

FIELDS = ["event_id", "trip_id", "rider_id", "pickup_zone_id", "dropoff_zone_id", "quoted_fare", "event_time",
          "received_time"]


def compact_day(raw: Path, table: Path, day: date) -> Path:
    """One run of the job for `day`: one file in table/dt=<day>/."""
    after = day + timedelta(days=1)
    files = sorted((raw / f"dt={day}").glob("hour=*/*.jsonl")) + sorted((raw / f"dt={after}" / "hour=00").glob("*.jsonl"))
    rows = []
    for path in files:
        for line in path.read_text().splitlines():
            if line:
                e = json.loads(line)
                if e.get("event_type") == "trip_requested" and e["event_time"].startswith(str(day)):
                    rows.append({k: e.get(k) for k in FIELDS})
    rows.sort(key=lambda r: (r["event_time"], r["event_id"]))
    out = table / f"dt={day}" / "part-00000.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return out


def count_by_zone(table: Path, first: date, last: date) -> dict[int, int]:
    """Trips requested in each pickup zone from `first` to `last`, both days included, read from the table only."""
    counts: dict[int, int] = {}
    day = first
    while day <= last:
        for path in sorted((table / f"dt={day}").glob("*.csv")):
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    z = int(row["pickup_zone_id"])
                    counts[z] = counts.get(z, 0) + 1
        day += timedelta(days=1)
    return counts
