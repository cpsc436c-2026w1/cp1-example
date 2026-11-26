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
    ("rule 2: an R line with a Scenario link without a Rule", COUNTS, "  @R030\n", "", "R030 is not the tag of a Rule"),
    ("rule 2: an RF with a Scenario link without a Rule", COUNTS, "  @RF020\n", "", "RF020 is not the tag of a Rule"),
    ("rule 2: a Scenario link to a file without the Rule", REQ,
     "not assigned yet. [Scenario](../features/trip_assignment.feature)", "not assigned yet. [Scenario](../features/js01_trips_per_zone.feature)",
     "RF030 links js01_trips_per_zone.feature, but its Rule is at trip_assignment.feature"),
    ("rule 3: a tag that is not a defined code", COUNTS, "  @R020\n", "  @R020 @R999\n", "@R999 is not defined"),
    ("rule 3: a story tag that is not a defined story", ASSIGN, "@JS02 @JS03", "@JS02 @JS09", "@JS09 is not defined"),
    ("rule 3: a heading in the design names an undefined ID in brackets", DESIGN,
     "### Pickup place of a message [R110, R120]", "### Pickup place of a message [R110, R120, R999]", "R999 is not defined in docs/requirements.md"),
    ("rule 3: a SIM bullet names an undefined ID in brackets", DESIGN,
     "- **SIM04 Trips day** [R040]", "- **SIM04 Trips day** [R045]", "R045 is not defined in docs/requirements.md"),
    ("rule 3: a code in the design that is not defined", DESIGN, "| R070, R080, RF030, RF050 |", "| R070, R085, RF030, RF050 |",
     "R085 is not defined"),
    ("rule 4: a code on two Rules", COUNTS, "  @R020\n", "  @R020 @R010\n", "@R010 is already the tag of the Rule"),
    ("rule 5: a data set defined twice", DESIGN, "- **SIM02 Quiet zone**", "- **SIM01 Quiet zone**", "SIM01 is defined twice"),
    ("rule 6: a data set in a feature that is not defined", COUNTS, 'SIM02 "quiet-zone"', 'SIM09 "quiet-zone"',
     "SIM09 is not defined in docs/design.md"),
    ("rule 6: a source in the requirements that is not defined", REQ, "three zones in DS01,", "three zones in DS07,",
     "DS07 is not defined in docs/design.md"),
    ("rule 7: a data set built from a source that is not defined", DESIGN,
     "in SIM01's hour from DS01, at", "in SIM01's hour from DS05, at",
     "SIM03 is built from DS05"),
    ("rule 7: a data set that names no source", DESIGN,
     "in SIM01's hour from DS01, at", "in SIM01's hour, at",
     "SIM03 does not name a DS"),
]


@pytest.mark.parametrize("name,file,old,new,message", PLANTED, ids=[p[0] for p in PLANTED])
def test_planted_error_is_found(copy, name, file, old, new, message):
    change(copy, file, old, new)
    result = run(copy)
    assert result.returncode == 1, result.stdout
    assert message in result.stdout, result.stdout


def test_exemptions_are_not_problems(copy):
    """RF050 (Read:), RQ010 and RQ020 do not have a Rule, and R100 without a Scenario link may lose its Rule: not problems."""
    change(copy, REQ, "(SLO) [Scenario](../features/trip_assignment.feature)\n\n## JS04", "(SLO)\n\n## JS04")
    change(copy, ASSIGN, "  @R100\n", "")
    result = run(copy)
    assert result.returncode == 0, result.stdout
    for code in ("R100", "RF050", "RQ010", "RQ020"):
        assert not any(code in line for line in result.stdout.splitlines() if line.startswith("PROBLEM"))


def test_tags_above_an_outline_stay_with_the_outline(copy):
    """Tags above Scenario Outline: or Examples: belong to that keyword, not to the next Rule."""
    outline = """    @R010
    Scenario Outline: Requests counted per zone, <zone>
      Given a zone <zone>
      Then the count is <n>

      @R010
      Examples:
        | zone | n |
        | Z1   | 1 |

"""
    change(copy, COUNTS, "  @R020\n", outline + "  @R020\n")
    result = run(copy)
    assert "already the tag of the Rule" not in result.stdout, result.stdout
    assert result.returncode == 0, result.stdout


def test_an_id_in_design_prose_is_not_a_use(copy):
    """Only IDs in brackets and in the Resources IDs column count; a token like R2 in a sentence does not."""
    change(copy, DESIGN, "## Resources", "Version R2 of the sketch is in the slides.\n\n## Resources")
    result = run(copy)
    assert result.returncode == 0, result.stdout


def test_a_rule_without_an_example_is_a_problem(copy):
    """Rule 8: the Checkpoint 1 page asks for at least one example under each rule."""
    empty = "  @R999\n  Rule: A rule with no example yet\n\n"
    change(copy, REQ, "- **R010**", "- **R999** THE SYSTEM SHALL keep a placeholder.\n- **R010**")
    change(copy, COUNTS, "  @R020\n", empty + "  @R020\n")
    result = run(copy)
    assert "this Rule has no Example" in result.stdout, result.stdout
    assert result.returncode == 1


def test_a_rule_whose_examples_are_an_outline_is_not_a_problem(copy):
    """An outline under a rule counts as its example."""
    rule = ("  @R999\n  Rule: A rule shown by an outline\n\n    Scenario Outline: zone <zone>\n      Given a zone <zone>\n\n"
            "      Examples:\n        | zone |\n        | Z1   |\n\n")
    change(copy, REQ, "- **R010**", "- **R999** THE SYSTEM SHALL keep a placeholder.\n- **R010**")
    change(copy, COUNTS, "  @R020\n", rule + "  @R020\n")
    result = run(copy)
    assert "has no Example" not in result.stdout, result.stdout


@pytest.mark.parametrize("old,new", [
    ("- **R030**", "* **R030**"), ("- **R030**", "- **`R030`**"), ("- **R030**", "-   **R030**"), ("- **R030**", "- `R030`"),
])
def test_other_requirement_list_formats_define_the_id(copy, old, new):
    change(copy, REQ, old, new)
    result = run(copy)
    assert result.returncode == 0, result.stdout


def test_a_read_line_with_a_rule_is_a_problem(copy):
    change(copy, COUNTS, "  @R020\n", "  @RF050\n  Rule: Tags on every resource\n    Example: a bucket\n      Given x\n\n  @R020\n")
    result = run(copy)
    assert "RF050 ends with Read:, so it must not get a rule" in result.stdout, result.stdout


def test_an_rf_without_link_reply_or_read_is_a_problem(copy):
    change(copy, REQ, "- **RF050**", "- **RF060** Every zone has a name. Reply: we keep a zone table.\n- **RF050**")
    result = run(copy)
    assert "RF060 has no [Scenario](...) link" in result.stdout, result.stdout


def test_a_wrong_folder_gives_a_message_not_a_traceback(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 1 and "Traceback" not in result.stderr
    assert "not found" in result.stdout


def test_docstrings_bom_subfolders_and_heading_case(copy):
    doc = '      """\n      @R666\n      Rule: not a rule\n      """\n'
    change(copy, COUNTS, "      Given ", doc + "      Given ")
    path = copy / COUNTS
    path.write_text(path.read_text(), encoding="utf-8-sig")
    (copy / "features/sub").mkdir()
    (copy / ASSIGN).rename(copy / "features/sub" / Path(ASSIGN).name)
    req = copy / REQ
    req.write_text(req.read_text().replace("features/trip_assignment.feature", "features/sub/trip_assignment.feature"))
    change(copy, DESIGN, "### Our data", "### Our Data")
    result = run(copy)
    assert result.returncode == 0, result.stdout


def test_a_plain_mention_of_a_defined_id_is_not_a_definition(copy):
    """IDs in a notes list or a heading that discusses them do not define them again."""
    path = copy / REQ
    path.write_text(path.read_text() + "\n## Notes\n\n- R010 and R020 share the SLO\n\n### R010 why we count\n")
    result = run(copy)
    assert result.returncode == 0, result.stdout


def test_a_plain_only_definition_gets_a_hint(copy):
    change(copy, REQ, "- **R030**", "- R030")
    result = run(copy)
    assert "R030 starts a line but is not bold" in result.stdout, result.stdout


def test_an_unclosed_docstring_is_reported(copy):
    change(copy, COUNTS, "      Given ", '      """\n      Given ')
    result = run(copy)
    assert "docstring is not closed" in result.stdout, result.stdout
