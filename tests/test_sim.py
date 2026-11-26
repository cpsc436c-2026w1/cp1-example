"""The generator: the same seed writes the same files, the committed files are the ones it writes, and the files
hold what docs/design.md, section Data, Simulated data for the demos, says (sim/check.py checks every number)."""
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


def test_folders_follow_the_time_of_receipt():
    folder = g.generate("SIM01")
    for path in folder.glob("trip-events/dt=*/hour=*/deliveries.jsonl"):
        day, hour = path.parts[-3][3:], path.parts[-2][5:]
        assert all(d["received_time"].startswith(f"{day}T{hour}") for d in g.read_jsonl(path))


def test_trips_day_file_and_its_bad_fares():
    g.generate("SIM04")
    data = g.load("SIM04")
    assert len(data["events"]) == 19074 and len(data["deliveries"]) == 19077
    bad = {f["trip_id"]: f["reason"] for f in data["faults"]}
    assert sorted(bad.values()) == ["fare not above 0", "fare not above 0", "no fare"]
    rows = {r["trip_id"]: r for r in data["deliveries"]}
    assert [rows[t]["fare"] for t in sorted(bad)] == ["", "0.0", "-4.5"]


def test_the_system_reads_no_truth():
    """What the examples read (load_received) is the same with the truth folder gone."""
    folder = g.generate("SIM01")
    before = g.load_received("SIM01")
    for path in (folder / "_truth").iterdir():
        path.unlink()
    assert g.load_received("SIM01") == before
