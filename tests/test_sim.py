"""The generator: the same seed writes the same files, the committed files are the ones it writes, and the files
hold what docs/design.md, section Data, Simulated data for the demos, says."""
import hashlib
from collections import Counter
from pathlib import Path

from sim import generate as g
from sim.datasets import COMMITTED

COMMITTED_DATA = Path(__file__).resolve().parent.parent / "sim" / "data"


def digest(folder):
    h = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(folder)).encode() + path.read_bytes())
    return h.hexdigest()


def test_same_seed_same_files():
    for sim_id in COMMITTED:
        first = digest(g.generate(sim_id))
        assert digest(g.generate(sim_id)) == first, sim_id


def test_committed_files_are_what_the_generator_writes():
    for sim_id in COMMITTED:
        assert digest(g.generate(sim_id)) == digest(COMMITTED_DATA / sim_id), f"{sim_id}: run uv run python -m sim.generate"


def test_rush_hour_counts_and_faults():
    g.generate("SIM01")
    data = g.load("SIM01")
    assert len(data["events"]) == 2511 and len(data["deliveries"]) == 2515
    assert Counter(f["fault"] for f in data["faults"]) == {"duplicate": 4, "late": 2}
    ids = Counter(d["event_id"] for d in data["deliveries"])
    assert sorted(i for i, n in ids.items() if n == 2) == sorted(f["event_id"] for f in data["faults"] if f["fault"] == "duplicate")
    late = {f["event_id"] for f in data["faults"] if f["fault"] == "late"}
    for d in data["deliveries"]:
        delay = (g.datetime.fromisoformat(d["received_time"][:-1]) - g.datetime.fromisoformat(d["event_time"][:-1])).seconds
        if d["event_id"] in late:
            assert 360 <= delay <= 600
    assert all(d["received_time"] >= d["event_time"] for d in data["deliveries"])


def test_folders_follow_the_time_of_receipt():
    folder = g.generate("SIM01")
    for path in folder.glob("trip-events/dt=*/hour=*/deliveries.jsonl"):
        day, hour = path.parts[-3][3:], path.parts[-2][5:]
        assert all(d["received_time"].startswith(f"{day}T{hour}") for d in g.read_jsonl(path))


def test_quiet_zone_has_no_request_in_its_gap():
    g.generate("SIM02")
    data = g.load("SIM02")
    assert data["faults"] == [dict(fault="quiet", zone=48, start="2026-11-23T09:25:00Z", end="2026-11-23T09:35:00Z",
                                   trips_left_out=60)]
    assert not [e for e in data["events"] if e["event_type"] == "trip_requested" and e["pickup_zone_id"] == 48
                and "2026-11-23T09:25:00Z" <= e["event_time"] < "2026-11-23T09:35:00Z"]


def test_double_accept_pairs():
    g.generate("SIM03")
    data = g.load("SIM03")
    accepts = [d for d in data["deliveries"] if d["event_type"] == "trip_accepted"]
    by_trip = {}
    for a in accepts:
        by_trip.setdefault(a["trip_id"], []).append(a)
    assert len(by_trip) == 20
    for pair in by_trip.values():
        assert len(pair) == 2 and pair[0]["driver_id"] != pair[1]["driver_id"]
        assert pair[0]["received_time"] == pair[1]["received_time"]
    later_first = [t for t, pair in by_trip.items() if pair[0]["event_time"] > pair[1]["event_time"]]
    assert sorted(later_first) == sorted(f["trip_id"] for f in data["faults"])
    assert len(later_first) == 10


def test_the_system_reads_no_truth():
    """What the examples read (load_received) is the same with the truth folder gone."""
    folder = g.generate("SIM01")
    before = g.load_received("SIM01")
    for path in (folder / "_truth").iterdir():
        path.unlink()
    assert g.load_received("SIM01") == before
