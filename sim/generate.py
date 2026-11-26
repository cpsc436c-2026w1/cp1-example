"""Write the simulated data sets to sim/data/<id>/.

    uv run python -m sim.generate              # SIM01 to SIM03 (committed)

The seed is fixed, so every run writes the same files, byte for byte. Each data set has:

    sim/data/<id>/trip-events/dt=<day>/hour=<hour>/deliveries.jsonl   what the system receives, in the order received
    sim/data/<id>/_truth/events.jsonl    each event once, as it happened: expected answers are computed from it
    sim/data/<id>/_truth/faults.jsonl    each injected fault; never sent to the system

The folders under trip-events/ are the folders of raw/trip-events/ in the team's bucket: day and hour of receipt.
"""
import csv
import json
import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sim.datasets import COMMITTED, DATA_SETS, SEED, SEED_ROWS, SEED_START, SIM_START

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sim" / "data"


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_seed_rows() -> list[dict]:
    """The DS01 sample, with each request time moved to the simulated hour (minute and second kept)."""
    rows = []
    with open(ROOT / SEED_ROWS, newline="") as f:
        for n, row in enumerate(csv.DictReader(f), 1):
            requested = datetime.strptime(row["request_datetime"], "%Y-%m-%d %H:%M:%S")
            rows.append(dict(trip_id=f"t-{n:04d}", requested=SIM_START + (requested - SEED_START),
                             pickup_zone_id=int(row["pickup_zone_id"]), dropoff_zone_id=int(row["dropoff_zone_id"]),
                             trip_miles=float(row["trip_miles"]), trip_time_s=int(row["trip_time_s"]),
                             fare=float(row["fare"]), driver_pay=float(row["driver_pay"])))
    return rows


def trip_events(rows: list[dict], rng: random.Random) -> list[dict]:
    """Three events for each trip. Fields are those of docs/design.md, section Data, Event format."""
    events = []
    for row in rows:
        driver = f"d-{rng.randint(1, 200):04d}"                    # DS01 does not have drivers: ours
        accepted = row["requested"] + timedelta(seconds=rng.randint(3, 15))
        completed = accepted + timedelta(seconds=300 + row["trip_time_s"])   # 5 minutes to the pickup: ours
        events.append(dict(event_type="trip_requested", trip_id=row["trip_id"],
                           rider_id=f"p-{rng.randint(1, 99999):05d}", pickup_zone_id=row["pickup_zone_id"],
                           dropoff_zone_id=row["dropoff_zone_id"], quoted_fare=row["fare"],
                           event_time=row["requested"]))
        events.append(dict(event_type="trip_accepted", trip_id=row["trip_id"], driver_id=driver,
                           event_time=accepted))
        events.append(dict(event_type="trip_completed", trip_id=row["trip_id"], driver_id=driver,
                           dropoff_zone_id=row["dropoff_zone_id"], trip_miles=row["trip_miles"],
                           trip_time_s=row["trip_time_s"], fare=row["fare"], driver_pay=row["driver_pay"],
                           event_time=completed))
    events.sort(key=lambda e: (e["event_time"], e["trip_id"]))
    for n, event in enumerate(events, 1):
        event["event_id"] = f"ev-{n:06d}"
    return events


def deliver(event: dict, received: datetime) -> dict:
    return {**event, "received_time": received}


def hourly(d: dict) -> str:
    """The file of a delivery: the day and hour it was received, as in raw/trip-events/."""
    return f"trip-events/dt={d['received_time']:%Y-%m-%d}/hour={d['received_time']:%H}/deliveries.jsonl"


def stream(sim_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """SIM01 and SIM02: (events, deliveries, faults)."""
    cfg, rng = DATA_SETS[sim_id], random.Random(SEED)
    events, faults = trip_events(read_seed_rows(), rng), []
    if "quiet_zone" in cfg:                                         # leave out a zone's trips for a while
        day = SIM_START.strftime("%Y-%m-%dT")
        start, end = day + cfg["quiet_from"] + ":00Z", day + cfg["quiet_to"] + ":00Z"
        gone = {e["trip_id"] for e in events if e["event_type"] == "trip_requested"
                and e["pickup_zone_id"] == cfg["quiet_zone"] and start <= iso(e["event_time"]) < end}
        events = [e for e in events if e["trip_id"] not in gone]
        faults.append(dict(fault="quiet", zone=cfg["quiet_zone"], start=start, end=end, trips_left_out=len(gone)))
    deliveries = [deliver(e, e["event_time"] + timedelta(seconds=1)) for e in events]
    requests = [d for d in deliveries if d["event_type"] == "trip_requested"]
    picked = rng.sample(requests, cfg.get("duplicates", 0) + cfg.get("late", 0))
    for d in picked[:cfg.get("duplicates", 0)]:                     # the same event a second time
        deliveries.append(deliver(d, d["received_time"] + timedelta(seconds=rng.randint(2, 30))))
        faults.append(dict(fault="duplicate", event_id=d["event_id"]))
    for d in picked[cfg.get("duplicates", 0):]:                     # received minutes after it happened
        low, high = cfg["late_minutes"]
        d["received_time"] = d["event_time"] + timedelta(seconds=rng.randint(low * 60, high * 60))
        faults.append(dict(fault="late", event_id=d["event_id"]))
    deliveries.sort(key=lambda d: (d["received_time"], d["event_id"]))
    return events, deliveries, faults


def double_accept(sim_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """SIM03: each trip is requested once and accepted by two drivers; both accepts carry one received_time."""
    cfg, rng = DATA_SETS[sim_id], random.Random(SEED)
    rows = [r for r in read_seed_rows() if r["pickup_zone_id"] == cfg["zone"]][:cfg["trips"]]
    events, deliveries, faults, n = [], [], [], 0
    for i, row in enumerate(rows):
        first_driver, second_driver = (f"d-{k:04d}" for k in rng.sample(range(1, 201), 2))
        first = row["requested"] + timedelta(seconds=rng.randint(3, 15))
        second = first + timedelta(seconds=rng.randint(1, 2))
        request = dict(event_type="trip_requested", trip_id=row["trip_id"], rider_id=f"p-{rng.randint(1, 99999):05d}",
                       pickup_zone_id=row["pickup_zone_id"], dropoff_zone_id=row["dropoff_zone_id"],
                       quoted_fare=row["fare"], event_time=row["requested"])
        accepts = [dict(event_type="trip_accepted", trip_id=row["trip_id"], driver_id=first_driver, event_time=first),
                   dict(event_type="trip_accepted", trip_id=row["trip_id"], driver_id=second_driver, event_time=second)]
        if i < cfg["later_first"]:                                  # the accept made later is first in the file
            accepts.reverse()
        for event in [request] + accepts:
            n += 1
            event["event_id"] = f"ev-{n:06d}"
        if i < cfg["later_first"]:
            faults.append(dict(fault="later-first", trip_id=row["trip_id"], event_id=accepts[0]["event_id"]))
        events += [request] + accepts
        deliveries.append(deliver(request, request["event_time"] + timedelta(seconds=1)))
        deliveries += [deliver(a, second + timedelta(seconds=1)) for a in accepts]
    return events, deliveries, faults


MAKERS = {"event stream": (stream, hourly), "two concurrent writers": (double_accept, hourly)}


def dumps(line: dict) -> str:
    return json.dumps(line, default=iso)


def write(sim_id: str, events: list[dict], deliveries: list[dict], faults: list[dict]) -> Path:
    folder = OUT / sim_id
    shutil.rmtree(folder, ignore_errors=True)
    files: dict[Path, str] = {}
    layout = MAKERS[DATA_SETS[sim_id]["kind"]][1]
    by_file: dict[str, list[str]] = {}
    for d in deliveries:                                            # folder = day and hour of receipt, as in raw/
        by_file.setdefault(layout(d), []).append(dumps(d))
    files.update({folder / rel: "\n".join(lines) + "\n" for rel, lines in by_file.items()})
    files[folder / "_truth" / "events.jsonl"] = "".join(dumps(e) + "\n" for e in events)
    files[folder / "_truth" / "faults.jsonl"] = "".join(dumps(f) + "\n" for f in faults)
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return folder


def generate(sim_id: str) -> Path:
    """Write one data set and return its folder. Standard library only."""
    make = MAKERS[DATA_SETS[sim_id]["kind"]][0]
    return write(sim_id, *make(sim_id))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def load_received(sim_id: str) -> list[dict]:
    """What the system receives: the delivery files outside _truth/, in the order received. The examples read only
    this."""
    folder = OUT / sim_id
    return [d for path in sorted(folder.glob("trip-events/dt=*/hour=*/*.jsonl")) for d in read_jsonl(path)]


def is_written(sim_id: str) -> bool:
    """The faults file is written last: a data set without it was not written to the end."""
    return (OUT / sim_id / "_truth" / "faults.jsonl").exists()


def load(sim_id: str) -> dict:
    """A written data set: what the system receives, the events as they happened, the injected faults."""
    folder = OUT / sim_id
    return dict(deliveries=load_received(sim_id), events=read_jsonl(folder / "_truth" / "events.jsonl"),
                faults=read_jsonl(folder / "_truth" / "faults.jsonl"))


if __name__ == "__main__":
    for sim_id in sys.argv[1:] or COMMITTED:
        cfg = DATA_SETS[sim_id]
        folder = generate(sim_id)
        data = load(sim_id)
        kinds = sorted({f["fault"] for f in data["faults"]})
        files = sum(1 for p in folder.rglob("*") if p.is_file() and "_truth" not in p.parts)
        print(f'{sim_id} {cfg["name"]}: {len(data["events"])} events, {len(data["deliveries"])} deliveries in '
              f'{files} file{"s" * (files != 1)}, {len(data["faults"])} fault records ({", ".join(kinds)}) '
              f'-> {folder.relative_to(ROOT)}/')
