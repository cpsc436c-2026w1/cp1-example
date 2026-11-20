"""evals/pickup_place/check.py: the recorded examples give 26 of 30, and each kind of wrong reply is not correct."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("pickup_place_check", ROOT / "evals/pickup_place/check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_recorded_examples():
    result = check.check(check.load_cases(), check.load_replies())
    assert (result["correct"], result["total"]) == (26, 30)


def test_every_place_is_on_the_list():
    places = set((ROOT / "evals/pickup_place/places.txt").read_text().splitlines())
    assert {c["pickup_place"] for c in check.load_cases()} - {None} <= places


def test_wrong_replies():
    assert check.judge("Penn Station", '{"pickup_place": "Penn Station"}') == (True, "")
    assert check.judge(None, '{"pickup_place": null}') == (True, "")
    assert not check.judge("Penn Station", '```json\n{"pickup_place": "Penn Station"}\n```')[0]
    assert not check.judge(None, '{"pickup_place": null, "reason": "x"}')[0]
    assert not check.judge(None, '{"pickup_place": "Penn Station"}')[0]
    assert not check.judge("Penn Station", '{"pickup_place": "penn station"}')[0]
