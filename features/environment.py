"""Setup that behave runs around the examples.

    uvx behave@1.3.3                                                              # every example, local code
    TARGET=aws uv run behave features/js01_trips_per_zone.feature --tags="not @todo"   # JS01's counting path on AWS

TARGET=local (the default) runs each example against the local code in src/rides/, standard library only, so
`uvx behave@1.3.3` (behave and nothing else) runs every example. TARGET=aws sends JS01's counting examples to the
deployed slice (scripts/stream.py up, scripts/counting.py up) and needs boto3 (`uv run`).
The examples read what the system receives, sim/data/<id>/ outside _truth/: their expected answers are written in
the examples, computed from _truth/ before the system ran (sim/expected.toml, sim/check.py).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from rides.counting import LocalSlice        # noqa: E402


def target() -> str:
    t = os.environ.get("TARGET", "local")
    assert t in ("local", "aws"), f"TARGET={t}: use local or aws"
    return t


def before_all(context):
    context.target = target()
    context.received = {}                     # data sets read so far, by id: what the system receives
    if context.target == "aws":
        from rides.aws_slice import AwsSlice  # boto3: only for TARGET=aws
        context.aws = AwsSlice()


def before_scenario(context, scenario):
    context.deliveries = []                   # every example starts without data: "only these trip requests"
    context.trips, context.answers = None, {}  # and without trips or answers
    if context.target == "aws":
        context.aws.clear()                   # and with empty tables
        context.slice = context.aws
    else:
        context.slice = LocalSlice()
