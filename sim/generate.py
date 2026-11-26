"""Write the simulated data sets to sim/data/<id>/.

    uv run python -m sim.generate              # SIM01 to SIM04 (committed), checks every line against src/rides/events.py
    uv run python -m sim.generate SIM05        # one data set; SIM05 is 42,797 files, written on demand

The seed is fixed, so every run writes the same files, byte for byte. Each data set has:

    sim/data/<id>/trip-events/dt=<day>/hour=<hour>/deliveries.jsonl   what the system receives, in the order received
                                                                       (SIM05: deliveries-<minute>.jsonl, one a minute)
    sim/data/<id>/trip-exports/dt=<day>/trips.csv                      SIM04: the nightly export, one CSV file
    sim/data/<id>/_truth/events.jsonl    each event once, as it happened: expected answers are computed from it
    sim/data/<id>/_truth/faults.jsonl    each injected fault; never sent to the system

The folders under trip-events/ are the folders of raw/trip-events/ in the team's bucket: day and hour of receipt.
The folder trip-exports/dt=<day>/ is where the export puts the file of that day's trips.
`generate()` uses the standard library only, so the examples can write SIM05 under `uvx behave@1.3.3`; the command
above also validates every line with Pydantic (src/rides/events.py), and sim/check.py checks the files against the
numbers of the bullets (sim/expected.toml).
"""
import csv
import gzip
import io
import json
import random
import shutil
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from sim.datasets import COMMITTED, DATA_SETS, SEED, SEED_ROWS, SEED_START, SIM_START

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sim" / "data"
EXPORT_FIELDS = ["trip_id", "driver_id", "dropoff_zone_id", "trip_miles", "trip_time_s", "fare", "driver_pay",
                 "event_time"]


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


def by_minute(d: dict) -> str:
    """SIM05: one small file for each minute of receipt, as the stream's copy to the lake writes them."""
    r = d["received_time"]
    return f"trip-events/dt={r:%Y-%m-%d}/hour={r:%H}/deliveries-{r:%M}.jsonl"


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


def utc_moved(text: str, fmt: str, shift: timedelta) -> datetime:
    """A DS01 time (New York local, as in the source) moved by `shift` and read as UTC, clock time kept."""
    return (datetime.strptime(text, fmt) + shift).replace(tzinfo=timezone.utc)


def trips_day(sim_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """SIM04: the completed trips of one day, as the rows of the nightly export, and 3 rows added with a bad fare.

    The truth holds the day's trips as they happened (one trip_completed each); each added row is a fault
    `bad-fare` that carries the row and the reason the system must give (R050)."""
    cfg, rng = DATA_SETS[sim_id], random.Random(SEED)
    shift = datetime.combine(cfg["day"], time()) - datetime.combine(cfg["seed_day"], time())
    events = []
    with gzip.open(ROOT / cfg["seed_rows"], "rt", newline="") as f:
        for n, row in enumerate(csv.DictReader(f), 1):
            requested = utc_moved(row["request_datetime"], "%Y-%m-%d %H:%M:%S", shift)
            accepted = requested + timedelta(seconds=rng.randint(3, 15))                  # as in trip_events
            events.append(dict(event_type="trip_completed", trip_id=f"t-{n:05d}",
                               driver_id=f"d-{rng.randint(1, 200):04d}", dropoff_zone_id=int(row["dropoff_zone_id"]),
                               trip_miles=float(row["trip_miles"]), trip_time_s=int(row["trip_time_s"]),
                               fare=float(row["fare"]), driver_pay=float(row["driver_pay"]),
                               event_time=accepted + timedelta(seconds=300 + int(row["trip_time_s"]))))
    events.sort(key=lambda e: (e["event_time"], e["trip_id"]))
    for n, event in enumerate(events, 1):
        event["event_id"] = f"ev-{n:06d}"
    rows = [{k: e[k] for k in EXPORT_FIELDS} for e in events]
    faults, day_start = [], datetime.combine(cfg["day"], time(), tzinfo=timezone.utc)
    for k, fare in enumerate(cfg["bad_fares"], len(events) + 1):   # a missing, a zero and a negative fare
        like = rng.choice(events)                                   # the other fields of a real trip: ours
        row = dict(trip_id=f"t-{k:05d}", driver_id=f"d-{rng.randint(1, 200):04d}",
                   dropoff_zone_id=like["dropoff_zone_id"], trip_miles=like["trip_miles"],
                   trip_time_s=like["trip_time_s"], fare=fare, driver_pay=like["driver_pay"],
                   event_time=day_start + timedelta(seconds=rng.randint(6 * 3600, 22 * 3600)))
        rows.append(row)
        faults.append(dict(fault="bad-fare", trip_id=row["trip_id"],
                           reason="no fare" if fare is None else "fare not above 0", row=row))
    rows.sort(key=lambda r: (r["event_time"], r["trip_id"]))
    received = datetime.fromisoformat(cfg["arrives"].replace("Z", "+00:00"))
    return events, [deliver(r, received) for r in rows], faults


def thirty_days(sim_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """SIM05: the requests of 30 days, from the count of DS01 requests in each minute and zone (seed file).

    From DS01: the minute and the pickup zone of each request. Made up (ours): its second in the minute, rider,
    dropoff zone and quoted fare. Only trip_requested events: RF040 counts requests. No injected faults."""
    cfg, rng = DATA_SETS[sim_id], random.Random(SEED)
    shift = datetime.combine(cfg["first"], time()) - datetime.combine(cfg["seed_first"], time())
    events = []
    with gzip.open(ROOT / cfg["seed_rows"], "rt", newline="") as f:
        for row in csv.DictReader(f):
            minute = utc_moved(row["minute"], "%Y-%m-%d %H:%M", shift)
            for second in sorted(rng.randint(0, 59) for _ in range(int(row["requests"]))):
                events.append(dict(event_type="trip_requested", rider_id=f"p-{rng.randint(1, 99999):05d}",
                                   pickup_zone_id=int(row["pickup_zone_id"]), dropoff_zone_id=rng.randint(1, 263),
                                   quoted_fare=round(rng.uniform(8, 60), 2),
                                   event_time=minute + timedelta(seconds=second)))
    events.sort(key=lambda e: (e["event_time"], e["pickup_zone_id"]))
    for n, event in enumerate(events, 1):
        event["event_id"], event["trip_id"] = f"ev-{n:06d}", f"t-{n:06d}"
    return events, [deliver(e, e["event_time"] + timedelta(seconds=1)) for e in events], []


MAKERS = {"event stream": (stream, hourly), "two concurrent writers": (double_accept, hourly),
          "daily file": (trips_day, None), "minute files": (thirty_days, by_minute)}


def dumps(line: dict) -> str:
    return json.dumps(line, default=iso)


def write(sim_id: str, events: list[dict], deliveries: list[dict], faults: list[dict]) -> Path:
    folder = OUT / sim_id
    shutil.rmtree(folder, ignore_errors=True)
    files: dict[Path, str] = {}
    layout = MAKERS[DATA_SETS[sim_id]["kind"]][1]
    if layout is None:                                              # SIM04: one CSV file, the export of the day
        buf = io.StringIO()
        out = csv.DictWriter(buf, EXPORT_FIELDS, lineterminator="\n")
        out.writeheader()
        for d in deliveries:
            out.writerow({**{k: d[k] for k in EXPORT_FIELDS}, "fare": "" if d["fare"] is None else d["fare"],
                          "event_time": iso(d["event_time"])})
        files[folder / "trip-exports" / f"dt={DATA_SETS[sim_id]['day']:%Y-%m-%d}" / "trips.csv"] = buf.getvalue()
    else:
        by_file: dict[str, list[str]] = {}
        for d in deliveries:                                        # folder = day and hour of receipt, as in raw/
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
    """What the system receives: the delivery files outside _truth/, in the order received (SIM04: the rows of its
    file). The examples read only this."""
    folder = OUT / sim_id
    if DATA_SETS[sim_id]["kind"] == "daily file":
        (path,) = folder.glob("trip-exports/dt=*/trips.csv")
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    return [d for path in sorted(folder.glob("trip-events/dt=*/hour=*/*.jsonl")) for d in read_jsonl(path)]


def is_written(sim_id: str) -> bool:
    """The faults file is written last: a data set without it was not written to the end."""
    return (OUT / sim_id / "_truth" / "faults.jsonl").exists()


def load(sim_id: str) -> dict:
    """A written data set: what the system receives, the events as they happened, the injected faults."""
    folder = OUT / sim_id
    return dict(deliveries=load_received(sim_id), events=read_jsonl(folder / "_truth" / "events.jsonl"),
                faults=read_jsonl(folder / "_truth" / "faults.jsonl"))


def validate(sim_id: str) -> int:
    """Every truth event and delivery against its Pydantic model (src/rides/events.py). Returns the lines checked."""
    sys.path.insert(0, str(ROOT / "src"))
    from rides.events import ExportRow, validate as validate_event   # here: generate() runs without pydantic
    data, n = load(sim_id), 0
    for event in data["events"]:
        validate_event(event)
        n += 1
    for d in data["deliveries"]:
        if DATA_SETS[sim_id]["kind"] == "daily file":
            ExportRow.model_validate({**d, "fare": d["fare"] or None})
        else:
            validate_event({k: v for k, v in d.items() if k != "received_time"})
        n += 1
    return n


if __name__ == "__main__":
    for sim_id in sys.argv[1:] or COMMITTED:
        cfg = DATA_SETS[sim_id]
        folder = generate(sim_id)
        data = load(sim_id)
        kinds = sorted({f["fault"] for f in data["faults"]}) or ["none"]
        files = sum(1 for p in folder.rglob("*") if p.is_file() and "_truth" not in p.parts)
        print(f'{sim_id} {cfg["name"]}: {len(data["events"])} events, {len(data["deliveries"])} deliveries in '
              f'{files} file{"s" * (files != 1)}, {len(data["faults"])} fault records ({", ".join(kinds)}), '
              f'{validate(sim_id)} lines valid -> {folder.relative_to(ROOT)}/')
