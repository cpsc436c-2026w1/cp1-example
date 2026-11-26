"""sim/check.py: each committed data set passes, and one planted error makes its check fail.

Adapted from the B5T2 tutorial's tests/test_check.py. The data sets are written into a temporary folder
(tests/conftest.py); the bullet check reads docs/design.md, or a copy with one number changed."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sim import generate as g

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def data(tmp_path):
    for sim_id in ("SIM01", "SIM02", "SIM04"):
        shutil.copytree(g.generate(sim_id), tmp_path / sim_id)
    return tmp_path


def run(data: Path, sim_id: str, design: Path = ROOT / "docs" / "design.md") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "sim" / "check.py"), sim_id, "--data", str(data),
                           "--design", str(design)], capture_output=True, text=True)


def failing(result) -> set[str]:
    return {line.split()[1].rstrip(":") for line in result.stdout.splitlines() if line.startswith("PROBLEM")}


def rewrite(path: Path, change):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text("".join(json.dumps(r) + "\n" for r in change(rows)))


def first_file(data: Path, sim_id="SIM01") -> Path:
    return sorted((data / sim_id / "trip-events").glob("dt=*/hour=*/deliveries.jsonl"))[0]


@pytest.mark.parametrize("sim_id", ["SIM01", "SIM02", "SIM04"])
def test_written_data_sets_pass(data, sim_id):
    result = run(data, sim_id)
    assert result.returncode == 0, result.stdout
    assert f"OK: {sim_id} matches its bullet" in result.stdout


def test_a_number_changed_in_the_bullet_fails_bullet(data, tmp_path):
    design = tmp_path / "design.md"
    design.write_text((ROOT / "docs" / "design.md").read_text().replace("2,511 events", "2,512 events"))
    result = run(data, "SIM01", design)
    assert failing(result) == {"bullet"}, result.stdout
    assert '"2,511 events" is not in the bullet of SIM01' in result.stdout


def test_one_more_request_fails_bullet_and_truth(data):
    def extra(rows):
        return rows + [dict(rows[0], event_id="ev-999999")]
    rewrite(first_file(data), extra)
    result = run(data, "SIM01")
    assert {"bullet", "truth", "lines"} <= failing(result), result.stdout


def test_a_field_with_a_typo_fails_validate(data):
    def typo(rows):
        rows[0]["pickup_zone"] = rows[0].pop("pickup_zone_id", 0)
        return rows
    rewrite(first_file(data), typo)
    assert "validate" in failing(run(data, "SIM01"))


def test_a_duplicate_without_its_record_fails_duplicate(data):
    faults = data / "SIM01" / "_truth" / "faults.jsonl"
    rewrite(faults, lambda rows: [r for r in rows if r["fault"] != "duplicate"][:] + [r for r in rows if r["fault"] == "duplicate"][1:])
    assert {"duplicate", "lines"} <= failing(run(data, "SIM01"))


def test_a_request_inside_the_quiet_window_fails_quiet(data):
    def noisy(rows):
        r = next(r for r in rows if r["event_type"] == "trip_requested" and r["pickup_zone_id"] == 161)
        r["pickup_zone_id"], r["event_time"] = 48, "2026-11-23T09:26:00Z"
        return rows
    path = sorted((data / "SIM02" / "trip-events").glob("dt=*/hour=09/deliveries.jsonl"))[0]
    rewrite(path, noisy)
    assert "quiet" in failing(run(data, "SIM02"))


def test_a_good_fare_made_zero_fails_bad_fare(data):
    path = next((data / "SIM04" / "trip-exports").glob("dt=*/trips.csv"))
    lines = path.read_text().splitlines()
    cells = lines[1].split(",")
    cells[5] = "0.0"
    path.write_text("\n".join([lines[0], ",".join(cells)] + lines[2:]) + "\n")
    assert {"bad-fare", "changed", "bullet"} <= failing(run(data, "SIM04"))
