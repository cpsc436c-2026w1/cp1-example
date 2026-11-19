"""tools/check_trace.py: the example is clean, and one planted error for each rule is found."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REQ, DESIGN = "docs/requirements.md", "docs/design.md"
COUNTS, ASSIGN = "features/js01_trips_per_zone.feature", "features/trip_assignment.feature"


def run(root: Path):
    return subprocess.run([sys.executable, str(ROOT / "tools/check_trace.py"), str(root)], capture_output=True, text=True)


@pytest.fixture
def copy(tmp_path):
    """A copy of the example's docs and features that a test may break."""
    for part in ("docs", "features"):
        shutil.copytree(ROOT / part, tmp_path / part)
    return tmp_path


def change(root: Path, file: str, old: str, new: str):
    path = root / file
    text = path.read_text()
    assert old in text, f"{old!r} is not in {file}: the test is out of date"
    path.write_text(text.replace(old, new, 1))


def test_example_is_clean():
    result = run(ROOT)
    assert result.returncode == 0, result.stdout
    assert "0 problems" in result.stdout
    assert "PROBLEM" not in result.stdout


PLANTED = [
    ("rule 1: a code defined twice", REQ, "- **R020** IF", "- **R010** IF", "R010 is defined twice"),
    ("rule 2: an R line of a focus story without a Rule", COUNTS, "  @R030\n", "", "R030 is not the tag of a Rule"),
    ("rule 2: an RF checked by examples without a Rule", COUNTS, "  @RF020\n", "", "RF020 is not the tag of a Rule"),
    ("rule 3: a tag that is not a defined code", COUNTS, "  @R020\n", "  @R020 @R999\n", "@R999 is not defined"),
    ("rule 3: a story tag that is not a defined story", ASSIGN, "@JS02 @JS03", "@JS02 @JS09", "@JS09 is not defined"),
    ("rule 3: a code in the design that is not defined", DESIGN, "| R070, R080, RF030 |", "| R070, R085, RF030 |",
     "R085 is not defined"),
    ("rule 4: a code on two Rules", COUNTS, "  @R020\n", "  @R020 @R010\n", "@R010 is already the tag of the Rule"),
    ("rule 5: a data set defined twice", DESIGN, "| SIM02 | `quiet-zone`", "| SIM01 | `quiet-zone`", "SIM01 is defined twice"),
    ("rule 6: a data set in a feature that is not defined", COUNTS, 'SIM02 "quiet-zone"', 'SIM09 "quiet-zone"',
     "SIM09 is not defined in docs/design.md"),
    ("rule 6: a source in the requirements that is not defined", REQ, "three zones, from DS01)", "three zones, from DS07)",
     "DS07 is not defined in docs/design.md"),
    ("rule 7: a data set built from a source that is not defined", DESIGN,
     "| SIM03 | `double-accept` | 20 trips of zone 161 from DS01", "| SIM03 | `double-accept` | 20 trips of zone 161 from DS05",
     "SIM03 is built from DS05"),
    ("rule 7: a data set that names no source", DESIGN,
     "| SIM03 | `double-accept` | 20 trips of zone 161 from DS01", "| SIM03 | `double-accept` | 20 trips of zone 161, generated",
     "SIM03 does not name a DS"),
]


@pytest.mark.parametrize("name,file,old,new,message", PLANTED, ids=[p[0] for p in PLANTED])
def test_planted_error_is_found(copy, name, file, old, new, message):
    change(copy, file, old, new)
    result = run(copy)
    assert result.returncode == 1, result.stdout
    assert message in result.stdout, result.stdout


def test_exemptions_are_not_problems(copy):
    """RF050 (read:) and RQ010 do not have a Rule, and R100 (story not in focus) may lose its Rule: not problems."""
    change(copy, ASSIGN, "  @R100\n", "")
    result = run(copy)
    assert result.returncode == 0
    for code in ("R100", "RF050", "RQ010"):
        assert not any(code in line for line in result.stdout.splitlines() if line.startswith("PROBLEM"))
