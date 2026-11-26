"""Steps for the counts of trips requested (rules R010, R020, R030, RF010, RF020).

The `When` steps hand the deliveries received by the given time to the counting path, in the order received:
`context.slice` is the local code (src/rides/counting.py, LocalSlice) or, with TARGET=aws, the deployed stream,
function and tables (src/rides/aws_slice.py). The `Then` steps read the stored counts back from it.
"""
import time

from behave import then, when

from rides.counting import NO_DATA, dedupe_is_on, received_by

DAY = "2026-11-23T"


def start_of(hhmm: str) -> str:
    return f"{DAY}{hhmm}:00Z"


def label(zone, start: str) -> str:
    """zone 161, between 09:10 and 09:15"""
    hour, minute = int(start[11:13]), int(start[14:16]) + 5
    end = f"{hour + minute // 60:02d}:{minute % 60:02d}"
    return f"zone {zone}, between {start[11:16]} and {end}"


def switch_note(context) -> str:
    return "" if dedupe_is_on() or context.target == "aws" else " (DEDUPE=off: the duplicate check is off)"


def deliver(context, read_at: str, wait: bool = True) -> None:
    """The deliveries received up to read_at go to the counting path; the ones after it are not received yet."""
    context.slice.send(received_by(context.deliveries, read_at), wait=wait)
    context.sent_at = time.monotonic()


@when("the counts are read at {time}")
@when("the time is {time}")
def step_read(context, time):
    deliver(context, time)


@when("the period between {start} and {end} ends")
def step_period_ends(context, start, end):
    deliver(context, start_of(end), wait=False)          # the Then waits, and measures how long


@when("the dashboard is opened at {time}")
def step_dashboard(context, time):
    deliver(context, time)
    context.dashboard = context.slice.rows()


@then("within {seconds:d} s zone {zone:d} has {expected:d} trip requested between {start} and {end}")
@then("within {seconds:d} s zone {zone:d} has {expected:d} trips requested between {start} and {end}")
def step_count_within(context, seconds, zone, expected, start, end):
    """The count must be stored, with the expected value, within the time the example gives after the period's end."""
    actual = context.slice.count(zone, start_of(start))
    while actual != expected and time.monotonic() - context.sent_at < seconds:
        time.sleep(0.25)
        actual = context.slice.count(zone, start_of(start))
    took = time.monotonic() - context.sent_at
    assert actual == expected, (f"{label(zone, start_of(start))}: expected {expected} trips requested within "
                                f"{seconds} s, the system has {actual} after {took:.1f} s")


@then("zone {zone:d} shows {expected:d} trip requested between {start} and {end}")
@then("zone {zone:d} shows {expected:d} trips requested between {start} and {end}")
@then("zone {zone:d} has {expected:d} trip requested between {start} and {end}")
@then("zone {zone:d} has {expected:d} trips requested between {start} and {end}")
def step_count(context, zone, expected, start, end):
    actual = context.slice.count(zone, start_of(start))
    assert actual == expected, (f"{label(zone, start_of(start))}: expected {expected} trips requested, "
                                f"the system counted {actual}{switch_note(context)}")


@then("zone {zone:d} shows no data between {start} and {end}")
def step_no_data(context, zone, start, end):
    actual = context.slice.count(zone, start_of(start))
    assert actual == NO_DATA, f"{label(zone, start_of(start))}: expected no data, the system shows {actual}"


@then("zones {zones} show {totals} trips requested between {start} and {end}")
def step_totals(context, zones, totals, start, end):
    """zones 48, 161 and 230 show 304, 191 and 342 trips requested between 09:00 and 10:00: the sum of the zone's
    stored counts over the periods that start in that time."""
    zone_list = [int(z) for z in zones.replace(" and ", ", ").split(", ")]
    total_list = [int(n) for n in totals.replace(" and ", ", ").split(", ")]
    assert len(zone_list) == len(total_list), f"{len(zone_list)} zones and {len(total_list)} totals"
    first, last = start_of(start), start_of(end)
    rows = context.slice.rows()
    for zone, want in zip(zone_list, total_list):
        got = sum(r["trips"] for r in rows if r["zone"] == zone and first <= r["start"] < last)
        assert got == want, (f"zone {zone}, between {start} and {end}: expected {want} trips requested, "
                             f"the system counted {got}{switch_note(context)}")


@then("the dashboard has a row with zone {zone:d}, start {start}, end {end} and {expected:d} trip requested")
@then("the dashboard has a row with zone {zone:d}, start {start}, end {end} and {expected:d} trips requested")
def step_dashboard_row(context, zone, start, end, expected):
    want = dict(zone=zone, start=start_of(start), end=start_of(end), trips=expected)
    assert want in context.dashboard, f"expected the row {want}, the dashboard has {context.dashboard}"
