#!/usr/bin/env python3
"""Checker of the eval pickup-place (R110): compares each reply with the case's reference value. No model call.

    python3 evals/pickup_place/check.py [replies.jsonl]     # default: replies_recorded.jsonl beside this file

A run is correct when its reply is a JSON object with exactly one field, pickup_place, and that value equals the
case's reference value: a name from places.txt, or null. Anything else is not correct: text around the JSON (a code
fence too), an extra field, another place. Prints one line for each case, then the total. Standard library only.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_cases(path: Path = HERE / "cases.jsonl") -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_replies(path: Path = HERE / "replies_recorded.jsonl") -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def parse_reply(reply: str):
    """The reply's pickup_place, or raises ValueError with what is wrong with the reply."""
    try:
        value = json.loads(reply)
    except json.JSONDecodeError:
        raise ValueError("not JSON") from None
    if not isinstance(value, dict) or set(value) != {"pickup_place"}:
        raise ValueError("not exactly one field pickup_place")
    return value["pickup_place"]


def judge(reference, reply: str) -> tuple[bool, str]:
    """(correct, why not) for one run."""
    try:
        got = parse_reply(reply)
    except ValueError as error:
        return False, str(error)
    if got != reference:
        return False, f"pickup_place is {json.dumps(got)}"
    return True, ""


def check(cases: list[dict], replies: list[dict]) -> dict:
    """Per case: its runs and the wrong ones; in all: correct runs and all runs."""
    per_case = []
    for case in cases:
        runs = [r for r in replies if r["case"] == case["case"]]
        wrong = []
        for run in runs:
            ok, why = judge(case["pickup_place"], run["reply"])
            if not ok:
                wrong.append((run["run"], why))
        per_case.append({"case": case["case"], "reference": case["pickup_place"], "runs": len(runs), "wrong": wrong})
    total = sum(c["runs"] for c in per_case)
    correct = total - sum(len(c["wrong"]) for c in per_case)
    return {"cases": per_case, "correct": correct, "total": total}


def report(result: dict) -> str:
    lines = [f"{'case':>4}  {'reference':24}  correct  wrong runs"]
    for c in result["cases"]:
        wrong = "; ".join(f"run {run}: {why}" for run, why in c["wrong"])
        lines.append(f"{c['case']:>4}  {json.dumps(c['reference']):24}  {c['runs'] - len(c['wrong'])} of {c['runs']}   {wrong}")
    accuracy = result["correct"] / result["total"] if result["total"] else 0
    lines.append(f"pickup place correct in {result['correct']} of {result['total']} runs (accuracy {accuracy:.2f})")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    replies_path = Path(argv[1]) if len(argv) > 1 else HERE / "replies_recorded.jsonl"
    replies = load_replies(replies_path)
    kinds = sorted({r.get("kind", "") for r in replies})
    print(f"replies: {replies_path.name}, {len(replies)} lines ({', '.join(kinds)})")
    if any(k.startswith("recorded") for k in kinds):
        print("checker only, recorded replies: this run checks the checker, not the model; R110 needs a live run")
    print(report(check(load_cases(), replies)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
