"""Steps for the pickup place of a rider's message (rule R110) and its eval pickup-place.

The replies come from evals/pickup_place/replies_recorded.jsonl (REPLIES=recorded, the default): recorded
examples written by hand, not a model run. REPLIES=live would ask the model through the course LLM gateway; it
stops at ask_model_live below, which is not written yet.
"""
import importlib.util
import os
from pathlib import Path

from behave import given, then, when
from behave.api.pending_step import StepNotImplementedError

EVAL_DIR = Path(__file__).resolve().parents[2] / "evals" / "pickup_place"
EVALS = {"pickup-place": EVAL_DIR}

_spec = importlib.util.spec_from_file_location("pickup_place_check", EVAL_DIR / "check.py")
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)


def replies_mode() -> str:
    mode = os.environ.get("REPLIES", "recorded")
    assert mode in ("recorded", "live"), f"REPLIES={mode}: use recorded or live"
    return mode


# ---------------------------------------------------------------------------------------------------------------
# LIVE CALL GOES HERE. Not called unless REPLIES=live, and not written yet: a live run spends money on the course
# LLM gateway and needs the instructor's go. It would send the system prompt (the task and the place names of
# places.txt) and the message as the user message, with the output format {"pickup_place": <name or null>}, to
# the model in use (docs/requirements.md, Evals), and return the reply's text unchanged for the checker.
# ---------------------------------------------------------------------------------------------------------------
def ask_model_live(message: str) -> str:
    raise NotImplementedError("REPLIES=live: the call through the course LLM gateway is not written yet")


def recorded_reply(message: str, run: int = 1) -> str:
    cases = {c["message"]: c["case"] for c in checker.load_cases()}
    if message not in cases:                        # a draft example: there is not a recorded reply to show
        raise StepNotImplementedError("this message is not a case of evals/pickup_place/cases.jsonl, so it does not have a recorded reply")
    return next(r["reply"] for r in checker.load_replies() if r["case"] == cases[message] and r["run"] == run)


@given('the rider message "{message}"')
def step_message(context, message):
    context.message = message


@when("the support agent opens the message")
def step_open(context):
    reply = ask_model_live(context.message) if replies_mode() == "live" else recorded_reply(context.message)
    try:
        context.pickup_place = checker.parse_reply(reply)
    except ValueError as error:
        raise AssertionError(f"the reply is {error}: {reply!r}") from None


@then('the pickup place is "{place}"')
def step_place(context, place):
    assert context.pickup_place == place, f'expected pickup place "{place}", the system shows {context.pickup_place!r}'


@then("the system says that the message names no pickup place")
def step_null(context):
    assert context.pickup_place is None, f"expected null, the system shows {context.pickup_place!r}"


@given('the {count:d} cases of the eval "{name}"')
def step_cases(context, count, name):
    assert name in EVALS, f'"{name}" is not an eval with a folder under evals/'
    context.cases = checker.load_cases(EVALS[name] / "cases.jsonl")
    assert len(context.cases) == count, f"the eval has {len(context.cases)} cases, not {count}"


@when("the model that the system uses answers each case {runs:d} times")
def step_answer(context, runs):
    if replies_mode() == "live":
        context.replies = [{"case": c["case"], "run": run, "reply": ask_model_live(c["message"])}
                           for c in context.cases for run in range(1, runs + 1)]
    else:
        context.replies = checker.load_replies()
    for case in context.cases:
        have = sum(1 for r in context.replies if r["case"] == case["case"])
        assert have == runs, f"case {case['case']} has {have} replies, not {runs}"


@then("the pickup place is correct in at least {need:d} of the {total:d} runs")
def step_accuracy(context, need, total):
    result = checker.check(context.cases, context.replies)
    assert result["total"] == total, f"there are {result['total']} runs, not {total}"
    assert result["correct"] >= need, (f"correct in {result['correct']} of {result['total']} runs, "
                                       f"at least {need} needed\n{checker.report(result)}")
