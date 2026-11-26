"""Steps for yesterday's completed trips (rules R040, R050): a file arrives, the job loads it into two tables.
Local code only (src/rides/curate.py): the job and the lake are not deployed at Checkpoint 2."""
import time
from datetime import datetime, timedelta

from behave import given, then, when

from rides.curate import Lake


def seconds_between(earlier: str, later: str) -> float:
    return (datetime.fromisoformat(later[:-1]) - datetime.fromisoformat(earlier[:-1])).total_seconds()


@given("a file of completed trips with these rows:")
def step_file_rows(context):
    context.deliveries = [dict(zip(context.table.headings, row.cells)) for row in context.table]


def load(context, day: str, arrives: str) -> None:
    context.lake, context.day, context.arrived = Lake(), day, arrives
    started = time.monotonic()
    context.lake.load_file(day, context.deliveries)
    context.took_s = time.monotonic() - started


@when("the file for {day} arrives at {time}")
def step_file_for_day(context, day, time):
    load(context, day, time)


@when("the file arrives at {time}")
def step_file_arrives(context, time):
    """The nightly export of the day before the morning it arrives."""
    load(context, (datetime.fromisoformat(time[:10]) - timedelta(days=1)).strftime("%Y-%m-%d"), time)


@then("by {deadline} table trips_curated has {n:d} rows for {day}")
@then("by {deadline} table trips_curated has {n:d} row for {day}, trip {trip_id}")
def step_curated(context, deadline, n, day, trip_id=None):
    rows = context.lake.curated.get(day, [])
    assert len(rows) == n, f"trips_curated has {len(rows)} rows for {day}, expected {n}"
    if trip_id:
        assert [r["trip_id"] for r in rows] == [trip_id], f"trips_curated has {[r['trip_id'] for r in rows]}"
    allowed_s = seconds_between(context.arrived, deadline)
    assert context.took_s <= allowed_s, f"loaded after {context.took_s:.1f} s, allowed {allowed_s:.0f} s"


@then('table trips_rejected has trip {trip_id} with reason "{reason}"')
def step_rejected(context, trip_id, reason):
    rows = [r for r in context.lake.rejected.get(context.day, []) if r["trip_id"] == trip_id]
    assert [r["reason"] for r in rows] == [reason], f"trips_rejected has {trip_id} with {[r['reason'] for r in rows]}"
