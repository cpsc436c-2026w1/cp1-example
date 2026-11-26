"""Names, tags and clients shared by the scripts in scripts/.

Every name starts with the team's prefix (PREFIX, default t00), every resource carries the course tags
Project=436c, Team=t00, Owner=<OWNER> (scripts/tags.py, from the course recipe cost-and-teardown, copied unchanged),
and every call goes to ca-central-1 unless AWS_REGION says otherwise. Each `up` is safe to run again: a resource that
is there already is kept and given the settings below.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("PREFIX", "t00")
os.environ.setdefault("TEAM", "t00")
os.environ.setdefault("OWNER", "course")        # a team writes the member who owns the resource

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tags import prefix, tag_values, tags  # noqa: E402,F401

REGION = os.environ.get("AWS_REGION", "ca-central-1")
ROOT = Path(__file__).resolve().parent.parent


def names() -> dict:
    p = prefix()
    return {"stream": f"{p}-trip-events", "function": f"{p}-count-requests", "counts": f"{p}-zone-counts",
            "seen": f"{p}-seen-events", "log_group": f"/aws/lambda/{p}-count-requests",
            "role": f"{p}-count-requests-fn"}


def session():
    import boto3
    return boto3.Session(region_name=REGION)


def usage(doc: str, argv: list[str], commands=("up", "down", "status")) -> str:
    if len(argv) < 2 or argv[1] not in commands:
        sys.exit(doc)
    return argv[1]
