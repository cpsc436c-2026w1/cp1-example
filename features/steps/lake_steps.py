"""Steps for the count over 30 days of small files (rule RF040). Local code only (src/rides/compact.py): a folder
stands in for the bucket, CSV for Parquet and Python for Athena. With TARGET=aws the first step stops: the lake is
not deployed at Checkpoint 2, and the example is tagged @todo."""
import os
import shutil
import statistics
import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path

from behave import given, then, when

from rides.compact import compact_day, count_by_zone
from sim.datasets import DATA_SETS
from sim.generate import OUT

FIRST = DATA_SETS["SIM05"]["first"]
DAYS = DATA_SETS["SIM05"]["days"]


@given("the data set is copied to raw/trip-events/ in the bucket")
def step_copy(context):
    assert context.target == "local", "TARGET=aws: the bucket, the compaction job and Athena are not deployed yet (@todo)"
    context.bucket = Path(tempfile.mkdtemp(prefix="t00-lake-"))
    context.add_cleanup(shutil.rmtree, context.bucket, ignore_errors=True)
    src = OUT / context.data_set_id / "trip-events"
    try:                                         # hard links: the same files, no copy of 200 MB
        shutil.copytree(src, context.bucket / "raw" / "trip-events", copy_function=os.link)
    except OSError:
        shutil.copytree(src, context.bucket / "raw" / "trip-events")


@given("job t00-compact-events has run for each of the {days:d} days")
def step_compact(context, days):
    raw, table = context.bucket / "raw" / "trip-events", context.bucket / "trip_events_compacted"
    for n in range(days):
        compact_day(raw, table, FIRST + timedelta(days=n))
    context.table_dir = table


@when("the count by zone over 30 days runs {runs:d} times in Athena while one small file a minute is added to raw/trip-events/")
def step_count_runs(context, runs):
    """The count runs one after the other; meanwhile a writer adds a small file to raw/ (one a second here, each
    standing for a minute). The count reads only the compacted table, so the new files do not change it."""
    stop, added = threading.Event(), []
    sample = next((OUT / context.data_set_id / "trip-events").glob("dt=*/hour=*/*.jsonl")).read_text()

    def writer():
        while not stop.is_set():
            path = context.bucket / "raw/trip-events/dt=2026-11-23/hour=00" / f"deliveries-{len(added):02d}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(sample)
            added.append(path)
            stop.wait(1.0)

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    context.results, context.run_s = [], []
    last = FIRST + timedelta(days=DAYS - 1)
    for _ in range(runs):
        started = time.monotonic()
        context.results.append(count_by_zone(context.table_dir, FIRST, last))
        context.run_s.append(time.monotonic() - started)
    stop.set()
    thread.join()
    context.files_added = len(added)


@then("table trip_events_compacted has {n:d} files, one for each day")
def step_files(context, n):
    files = sorted(context.table_dir.glob("dt=*/*.csv"))
    days = {p.parent.name for p in files}
    assert len(files) == n and len(days) == n, f"trip_events_compacted has {len(files)} files in {len(days)} days"


@then("every run counts {totals} trips requested for zones {zones}")
def step_run_counts(context, totals, zones):
    want = dict(zip((int(z) for z in zones.replace(" and ", ", ").split(", ")),
                    (int(n) for n in totals.replace(" and ", ", ").split(", "))))
    for k, got in enumerate(context.results, 1):
        assert {z: got.get(z, 0) for z in want} == want, f"run {k} counts {got}, expected {want}"


@then("the median run time is under {limit:d} s")
def step_median(context, limit):
    median = statistics.median(context.run_s)
    assert median < limit, f"median run time {median:.2f} s over {len(context.run_s)} runs, limit {limit} s"
