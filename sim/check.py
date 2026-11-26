"""Check one simulated data set: against the simulation standards, and against the numbers of its bullet.

    uv run python sim/check.py SIM01            # one data set
    uv run python sim/check.py                  # every data set that is written under sim/data/

Adapted from the B5T2 tutorial's checker (cpsc436c-2026w1/b5-t2-behave-sim, sim/check.py). What changed here:
the bullet check (sim/expected.toml), a CSV source for the nightly export (SIM04), the fault kinds of this
repository (`duplicate` where B5T2 writes `twice`; `quiet`, `later-first` and `bad-fare` are checked too), and one
file a minute (SIM05, `deliveries-<minute>.jsonl`). It needs duckdb and pydantic (in pyproject.toml).

What it checks:

    bullet     each `says` of sim/expected.toml is in the data set's bullet in docs/design.md, each number of its
               `expect` is in its `says`, and its `sql` on the files returns `expect`
    validate   every delivery line is a model of src/rides/events.py plus `received_time`; every truth line is a
               model; a CSV row is an ExportRow; times are UTC
    folders    every delivery is in the dt=/hour= folder (and minute file) of its received_time
    truth      each event_id once in _truth/events.jsonl; every delivered event is in it (a CSV row by trip_id)
    duplicate  the event is delivered one more time for each `duplicate` record
    never      the event is in the truth and is not delivered
    late       the event's delay (event_time to first delivery) is longer than every event not marked late
    changed    a delivery of the event differs from the truth in the record's `field`; no other delivery differs
    quiet      no request of the record's zone has an event time in its window
    later-first  the accept the record names is first in the file and is the later of its trip's two accepts
    bad-fare   the CSV has the record's row as it is, and its fare is missing, 0 or negative; every other fare is above 0
    lines      delivery lines = truth events - never + duplicate (+ bad-fare rows)

Exit code 0 when there is no problem, 1 otherwise. The last line is a digest of the data set's files: run the
generator twice, and the digest is the same both times when the generator is deterministic.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
import tomllib
import typing
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import duckdb
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parent.parent
SHOW = 5                                   # problems shown for each check; the count is always given
KINDS = ("duplicate", "never", "late", "changed", "quiet", "later-first", "bad-fare")


def load_models(path: Path) -> tuple[dict[str, type[BaseModel]], type[BaseModel] | None]:
    """The models whose `event_type` is a Literal of one value, by that value; and ExportRow, the CSV row."""
    spec = importlib.util.spec_from_file_location("events_under_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    models = {}
    for obj in vars(module).values():
        if isinstance(obj, type) and issubclass(obj, BaseModel) and "event_type" in obj.model_fields:
            values = typing.get_args(obj.model_fields["event_type"].annotation)
            if len(values) == 1:
                models[values[0]] = obj
    return models, getattr(module, "ExportRow", None)


def utc(value) -> datetime | None:
    """A UTC time written as 2026-11-23T09:00:00Z (or +00:00), else None."""
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.utcoffset() is not None and t.utcoffset().total_seconds() == 0 else None


def read_jsonl(path: Path, problems: list) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            problems.append(f"{rel(path)}:{n}: not JSON ({e.msg})")
    return rows


class Report:
    def __init__(self):
        self.problems = 0

    def check(self, name: str, problems: list[str], ok_text: str):
        if problems:
            self.problems += len(problems)
            print(f"PROBLEM {name}: {len(problems)}")
            for p in problems[:SHOW]:
                print(f"  {p}")
            if len(problems) > SHOW:
                print(f"  ... and {len(problems) - SHOW} more")
        else:
            print(f"ok   {name}: {ok_text}")


def digest(folder: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(folder)).encode() + b"\0" + path.read_bytes())
    return h.hexdigest()[:16]


def pl(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def dur(seconds: float) -> str:
    if seconds < 600:
        return f"{seconds:.0f} s"
    return f"{seconds / 60:.0f} min" if seconds < 3 * 3600 else f"{seconds / 3600:.0f} h"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def bullets(design: Path) -> dict[str, str]:
    """{SIM id: its bullet in docs/design.md, Data, Simulated data, as one line with single spaces}."""
    out, last, in_part = {}, None, False
    for line in design.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("### "):
            in_part = "simulated data" in line.lower()
            last = None
            continue
        if not in_part:
            continue
        if m := re.match(r"\s*[-*+]\s+\**`?(SIM\d+)\b", line):
            last = m.group(1)
            out[last] = line
        elif last and line.startswith("  "):
            out[last] += " " + line
        else:
            last = None
    return {k: re.sub(r"\s+", " ", v.replace("*", "")) for k, v in out.items()}


def numbers(value) -> list[str]:
    return re.findall(r"\d+", str(value).replace(",", ""))


def check_bullet(sim_id: str, db, expected: list[dict], bullet: str | None) -> list[str]:
    if bullet is None:
        return [f"docs/design.md: no bullet for {sim_id} under Data, Simulated data for the demos"]
    problems = []
    for row in expected:
        says = re.sub(r"\s+", " ", row["says"])
        if says not in bullet:
            problems.append(f'expected.toml: "{says}" is not in the bullet of {sim_id}')
        for number in numbers(row["expect"]):
            if number != "0" and not re.search(rf"(?<![\d.]){number}(?![\d.])", says.replace(",", "")):
                problems.append(f'expected.toml: {row["expect"]} is the expected value, but "{says}" does not say {number}')
        try:
            got = db.execute(row["sql"]).fetchone()[0]
        except duckdb.Error as e:
            problems.append(f'expected.toml: "{says}": the query failed: {str(e).splitlines()[0]}')
            continue
        if str(got) != str(row["expect"]):
            problems.append(f'"{says}": the files give {got}, the bullet says {row["expect"]}')
    return problems


def check_one(sim_id: str, data: Path, models, export_model, expected: list[dict], bullet: str | None) -> int:
    folder = data / sim_id
    if not (folder / "_truth" / "events.jsonl").exists():
        print(f"FAILED: {rel(folder)}/_truth/events.jsonl not found: run uv run python -m sim.generate {sim_id}")
        return 1
    print(f"{sim_id}: {rel(folder)}/ (models: {', '.join(sorted(models))}{', ExportRow' if export_model else ''})")
    report = Report()
    sources = sorted(p.name for p in folder.iterdir() if p.is_dir() and not p.name.startswith("_"))
    jsonl = {s: sorted((folder / s).glob("dt=*/hour=*/deliveries*.jsonl")) for s in sources}
    csvs = {s: sorted((folder / s).glob("dt=*/*.csv")) for s in sources}
    known = {p for s in sources for p in jsonl[s] + csvs[s]}
    stray = [rel(p) for s in sources for p in (folder / s).rglob("*") if p.is_file() and p not in known]
    parse_problems, deliveries, rows = [], [], []   # (path, line number, record)
    for s in sources:
        for path in jsonl[s]:
            deliveries += [(path, n, r) for n, r in enumerate(read_jsonl(path, parse_problems), 1)]
        for path in csvs[s]:
            with open(path, newline="") as f:
                rows += [(path, n, r) for n, r in enumerate(csv.DictReader(f), 2)]
    truth = read_jsonl(folder / "_truth" / "events.jsonl", parse_problems)
    faults_path = folder / "_truth" / "faults.jsonl"
    faults = read_jsonl(faults_path, parse_problems) if faults_path.exists() else []
    report.check("JSON", parse_problems, "every line is one JSON object")

    # Folders: a JSON Lines delivery is in the folder (and minute file) of its received_time.
    folder_problems = [f"{rel(folder)}/: no source folder with dt=<day>/ files"] if not (deliveries or rows) else []
    folder_problems += [f"{p}: not dt=<day>/hour=<hour>/deliveries*.jsonl or dt=<day>/<file>.csv" for p in stray]
    for path, n, row in deliveries:
        t = utc(row.get("received_time"))
        day, hour = path.parts[-3].removeprefix("dt="), path.parts[-2].removeprefix("hour=")
        minute = path.stem.removeprefix("deliveries").removeprefix("-")
        if t is not None and ((f"{t:%Y-%m-%d}", f"{t:%H}") != (day, hour) or (minute and minute != f"{t:%M}")):
            folder_problems.append(f"{rel(path)}:{n}: received_time {row['received_time']} is not in this file's folder")
    n_files = sum(len(jsonl[s]) + len(csvs[s]) for s in sources)
    report.check("folders", folder_problems, f"{pl(len(sources), 'source')} ({', '.join(sources)}), "
                 f"{pl(n_files, 'file')}, every line in the folder of its received_time")

    def validate(row: dict, where: str, delivered: bool) -> str | None:
        event = dict(row)
        if delivered:
            if "received_time" not in event:
                return f"{where}: no received_time"
            if utc(event.pop("received_time")) is None:
                return f"{where}: received_time {row['received_time']!r} is not a UTC time like 2026-11-23T09:00:00Z"
        model = models.get(event.get("event_type"))
        if model is None:
            return f"{where}: event_type {event.get('event_type')!r} has no model"
        try:
            model.model_validate(event)
        except ValidationError as e:
            err = e.errors()[0]
            return f"{where}: {'.'.join(map(str, err['loc'])) or 'line'}: {err['msg']}"
        if utc(event.get("event_time")) is None:
            return f"{where}: event_time {event.get('event_time')!r} is not a UTC time like 2026-11-23T09:00:00Z"
        return None

    invalid = [p for path, n, r in deliveries if (p := validate(r, f"{rel(path)}:{n}", True))]
    invalid += [p for n, r in enumerate(truth, 1) if (p := validate(r, f"_truth/events.jsonl:{n}", False))]
    for path, n, r in rows:
        try:
            export_model.model_validate({**r, "fare": r["fare"] or None})
        except (ValidationError, AttributeError) as e:
            invalid.append(f"{rel(path)}:{n}: {e.errors()[0]['msg'] if isinstance(e, ValidationError) else 'no ExportRow model'}")
    report.check("validate", invalid, f"{len(deliveries) + len(rows)} delivery lines and {len(truth)} truth events "
                 "match their models")

    # Truth: each event once; every delivery in it (a CSV row by its trip_id); every fault names a real event.
    truth_ids = Counter(e.get("event_id") for e in truth)
    by_id = {e.get("event_id"): e for e in truth}
    by_trip = {e.get("trip_id"): e for e in truth}
    kinds = Counter(f.get("fault") for f in faults)
    added = {f.get("trip_id"): f for f in faults if f.get("fault") == "bad-fare"}
    truth_problems = [f"_truth/events.jsonl: {i} is there {n} times" for i, n in truth_ids.items() if n > 1]
    truth_problems += sorted({f"{rel(p)}:{n}: {r.get('event_id')} is not in _truth/events.jsonl"
                              for p, n, r in deliveries if r.get("event_id") not in by_id})
    truth_problems += [f"{rel(p)}:{n}: trip {r['trip_id']} is not in _truth/events.jsonl nor a bad-fare record"
                       for p, n, r in rows if r["trip_id"] not in by_trip and r["trip_id"] not in added]
    for n, f in enumerate(faults, 1):
        if f.get("fault") in ("duplicate", "never", "late", "changed", "later-first") and f.get("event_id") not in by_id:
            truth_problems.append(f"_truth/faults.jsonl:{n}: {f.get('fault')} names {f.get('event_id')!r}, not in the truth")
    report.check("truth", truth_problems, f"each of {len(truth)} event_ids once, every delivery is in it")

    db = duckdb.connect()
    db.execute("SET TimeZone = 'UTC'")             # times in the files are UTC; so are the answers
    nd = "format='newline_delimited', union_by_name=true, hive_partitioning=false"
    db.execute(f"CREATE VIEW truth AS SELECT * FROM read_json('{folder}/_truth/events.jsonl', {nd})")
    if faults:
        db.execute(f"CREATE VIEW faults AS SELECT * FROM read_json('{faults_path}', {nd})")
    else:
        db.execute("CREATE VIEW faults AS SELECT NULL::VARCHAR AS fault, NULL::VARCHAR AS event_id WHERE false")
    if deliveries:
        db.execute(f"CREATE VIEW deliveries AS SELECT * EXCLUDE (filename), filename AS file FROM read_json("
                   f"'{folder}/[!_]*/dt=*/hour=*/deliveries*.jsonl', {nd}, filename=true)")
    if rows:
        db.execute(f"CREATE VIEW rows AS SELECT * FROM read_csv('{folder}/[!_]*/dt=*/*.csv', header=true)")
    report.check("bullet", check_bullet(sim_id, db, expected, bullet),
                 f"{pl(len(expected), 'number')} of the bullet, each given by the files")

    # duplicate and never: deliveries of each event = (0 if never else 1) + its duplicate records.
    got = Counter(r.get("event_id") for _, _, r in deliveries)
    if deliveries:
        want = Counter({i: 1 for i in by_id})
        for f in faults:
            if f.get("fault") == "duplicate":
                want[f["event_id"]] += 1
            elif f.get("fault") == "never":
                want[f["event_id"]] = 0
        wrong = [f"{i}: delivered {got[i]} times, the faults say {want[i]}" for i in by_id if got[i] != want[i]]
    else:
        wrong = []
    report.check("duplicate", wrong, f"{pl(kinds['duplicate'], 'record')}, each event delivered once more"
                 if kinds["duplicate"] else "none")
    report.check("never", [], f"{pl(kinds['never'], 'event')} in the truth and not delivered" if kinds["never"] else "none")

    # late: the delay of each late event is longer than every other event's.
    delays: dict[str, float] = {}
    for _, _, r in deliveries:
        e = by_id.get(r.get("event_id"))
        t, s = utc(r.get("received_time")), utc((e or {}).get("event_time"))
        if t and s:
            delays[r["event_id"]] = min(delays.get(r["event_id"], 1e18), (t - s).total_seconds())
    late_ids = {f.get("event_id") for f in faults if f.get("fault") == "late"} & delays.keys()
    early = [f"{i}: received {dur(-v)} before its event_time" for i, v in sorted(delays.items()) if v < 0]
    report.check("received after event", early, "every delivery has received_time >= event_time")
    if late_ids:
        slowest = max((v for i, v in delays.items() if i not in late_ids), default=0)
        low, high = dur(min(delays[i] for i in late_ids)), dur(max(delays[i] for i in late_ids))
        report.check("late", [f"{i}: first delivered {dur(delays[i])} after event_time, not later than an on-time "
                              f"event ({dur(slowest)})" for i in sorted(late_ids) if delays[i] <= slowest],
                     f"{pl(kinds['late'], 'event')} first delivered {low if low == high else low + ' to ' + high} "
                     f"after event_time; every other event within {dur(slowest)}")
    else:
        report.check("late", [], "none")

    # changed: a delivery differs from the truth only in the fields of a changed record.
    changed = defaultdict(set)
    for f in faults:
        if f.get("fault") == "changed":
            changed[f.get("event_id")].add(f.get("field"))
    change_problems = []
    for path, n, r in deliveries:
        e = by_id.get(r.get("event_id"))
        if e is not None:
            diff = {k for k in set(r) | set(e) if k != "received_time" and r.get(k) != e.get(k)}
            if diff - changed.get(r.get("event_id"), set()):
                change_problems.append(f"{rel(path)}:{n}: {r['event_id']} differs from the truth in "
                                       f"{', '.join(sorted(diff))} without a changed record")
    for path, n, r in rows:
        e = by_trip.get(r["trip_id"])
        if e is not None:
            diff = [k for k in r if str(e.get(k)) != r[k]]
            if diff:
                change_problems.append(f"{rel(path)}:{n}: trip {r['trip_id']} differs from the truth in {', '.join(diff)}")
    report.check("changed", change_problems, f"{pl(kinds['changed'], 'record')}" if kinds["changed"]
                 else "none: every delivery equals its truth event")

    # quiet: no request of the zone in the window.
    quiet = [f for f in faults if f.get("fault") == "quiet"]
    quiet_problems = [f"{r['event_id']}: a request of zone {f['zone']} at {r['event_time']}, inside the quiet window"
                      for f in quiet for _, _, r in deliveries if r.get("event_type") == "trip_requested"
                      and r.get("pickup_zone_id") == f["zone"] and f["start"] <= r["event_time"] < f["end"]]
    report.check("quiet", quiet_problems, f"zone {quiet[0]['zone']} has no request from {quiet[0]['start'][11:16]} "
                 f"to {quiet[0]['end'][11:16]}" if quiet else "none")

    # later-first: the named accept comes first in the file and is the later one.
    accepts = defaultdict(list)
    for _, _, r in deliveries:
        if r.get("event_type") == "trip_accepted":
            accepts[r["trip_id"]].append(r)
    lf = [f for f in faults if f.get("fault") == "later-first"]
    lf_problems = []
    for f in lf:
        pair = accepts.get(f["trip_id"], [])
        if len(pair) != 2 or pair[0]["event_id"] != f["event_id"] or pair[0]["event_time"] <= pair[1]["event_time"]:
            lf_problems.append(f"{f['trip_id']}: {f['event_id']} is not the later accept, first in the file")
    named = {f["trip_id"] for f in lf}
    lf_problems += [f"{t}: the later accept is first in the file, without a later-first record"
                    for t, pair in accepts.items() if len(pair) == 2 and pair[0]["event_time"] > pair[1]["event_time"]
                    and t not in named]
    report.check("later-first", lf_problems, f"{pl(len(lf), 'trip')} with the later accept first" if lf else "none")

    # bad-fare: the added rows are in the file as recorded; every other fare is above 0.
    bad_problems = []
    in_file = {r["trip_id"]: (p, n, r) for p, n, r in rows}
    for t, f in added.items():
        if t not in in_file:
            bad_problems.append(f"{t}: a bad-fare record, not in the file")
            continue
        p, n, r = in_file[t]
        fare = f["row"]["fare"]
        want_fare = "" if fare is None else str(fare)
        if r["fare"] != want_fare or (fare is not None and fare > 0):
            bad_problems.append(f"{rel(p)}:{n}: fare {r['fare']!r}, the record says {fare!r} (missing, 0 or negative)")
    bad_problems += [f"{rel(p)}:{n}: fare {r['fare']!r} is not above 0, without a bad-fare record"
                     for p, n, r in rows if r["trip_id"] not in added and not (r["fare"] and float(r["fare"]) > 0)]
    report.check("bad-fare", bad_problems, f"{pl(len(added), 'row')} with a missing, 0 or negative fare, every other "
                 "fare above 0" if added else "none")

    lines = len(deliveries) + len(rows)
    lines_want = len(truth) - kinds["never"] + kinds["duplicate"] + kinds["bad-fare"]
    report.check("lines", [f"{lines} delivery lines, truth - never + duplicate + bad-fare = {lines_want}"]
                 if lines != lines_want else [],
                 f"{lines} = {len(truth)} truth - {kinds['never']} never + {kinds['duplicate']} duplicate"
                 + (f" + {kinds['bad-fare']} bad-fare" if kinds["bad-fare"] else ""))
    other = {k: n for k, n in kinds.items() if k not in KINDS}
    print(f"--   other fault kinds, not checked here: {', '.join(f'{k} {n}' for k, n in sorted(other.items())) or 'none'}")
    print(f"FAILED: {sim_id} has {report.problems} problems" if report.problems
          else f"OK: {sim_id} matches its bullet and the simulation standards (0 problems)")
    print(f"digest {digest(folder)}")
    return 1 if report.problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sim_ids", nargs="*", help="SIM01 ...; none: every data set written under sim/data/")
    ap.add_argument("--data", type=Path, default=ROOT / "sim" / "data", help="the folder that holds <SIM>/")
    ap.add_argument("--design", type=Path, default=ROOT / "docs" / "design.md")
    ap.add_argument("--expected", type=Path, default=ROOT / "sim" / "expected.toml")
    args = ap.parse_args()
    models, export_model = load_models(ROOT / "src" / "rides" / "events.py")
    expected = tomllib.loads(args.expected.read_text())
    found = bullets(args.design)
    sim_ids = args.sim_ids or sorted(p.name for p in args.data.iterdir() if p.is_dir() and p.name.startswith("SIM"))
    failed = 0
    for i, sim_id in enumerate(sim_ids):
        if i:
            print()
        failed += check_one(sim_id, args.data, models, export_model, expected.get(sim_id, []), found.get(sim_id))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
