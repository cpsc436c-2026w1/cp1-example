"""Steps for trip assignment and what the rider sees (rules R070, R080, R090, R100, RF030): one accept, two accepts
sent before either has an answer, a completion, the rider's page. Local code only (src/rides/assign.py): the
functions of JS02 and JS03 are not deployed at Checkpoint 2."""
import threading
import time
from datetime import datetime

from behave import given, then, when

from rides.assign import ASSIGNED, REFUSED, Trips


def accept_together(trips: Trips, accepts: list[tuple[str, str]]) -> dict:
    """Send the accepts from one thread each. Returns {(trip, driver): answer}.

    Every accept reads the trip and then waits at the gate until all of them have read it. So each write is sent
    before any other accept has an answer, and the conditional write decides.
    """
    gate, answers = threading.Barrier(len(accepts)), {}

    def send(trip_id, driver_id):
        answers[(trip_id, driver_id)] = trips.accept(trip_id, driver_id, before_write=gate.wait)

    threads = [threading.Thread(target=send, args=a) for a in accepts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return answers


def trips_of(context) -> Trips:
    """The trips table of the example: every trip of the requests received so far is requested and not assigned."""
    if context.trips is None:
        context.trips = Trips()
        for d in context.deliveries:
            if d["event_type"] == "trip_requested":
                context.trips.request(d["trip_id"])
    return context.trips


@given("this accept is received:")
@when("this accept is received:")
def step_accept_row(context):
    """One accept, one request to our API; the time taken is measured around it."""
    (row,) = list(context.table)
    started = time.monotonic()
    context.answers[(row["trip_id"], row["driver_id"])] = trips_of(context).accept(row["trip_id"], row["driver_id"])
    context.received, context.took_s = row["received_time"], time.monotonic() - started


@when("these accepts are sent together, each before the other has an answer:")
def step_accept_table(context):
    accepts = [(row["trip_id"], row["driver_id"]) for row in context.table]
    context.answers.update(accept_together(trips_of(context), accepts))


@when("the two accepts of every trip are sent together, each before the other has an answer")
def step_accept_data_set(context):
    context.trips, context.answers, context.pairs = Trips(), {}, {}
    for d in context.deliveries:
        if d["event_type"] == "trip_requested":
            context.trips.request(d["trip_id"])
        else:
            context.pairs.setdefault(d["trip_id"], []).append(d["driver_id"])
    for trip_id, drivers in context.pairs.items():
        context.answers.update(accept_together(context.trips, [(trip_id, driver) for driver in drivers]))


def seconds_between(earlier: str, later: str) -> float:
    return (datetime.fromisoformat(later[:-1]) - datetime.fromisoformat(earlier[:-1])).total_seconds()


def check_answer(context, deadline: str, driver_id: str, want: str) -> None:
    """The time allowed is the deadline less the time of receipt; the time taken is measured around the accept."""
    allowed_s = seconds_between(context.received, deadline)
    answers = [a for (_, driver), a in context.answers.items() if driver == driver_id]
    assert answers == [want], f"driver {driver_id}: expected {want}, the system answered {answers}"
    assert context.took_s <= allowed_s, f"driver {driver_id}: answer after {context.took_s:.2f} s, allowed {allowed_s:.0f} s"


@then("by {deadline} driver {driver_id} has the answer that the accept is refused")
def step_refused_by(context, deadline, driver_id):
    check_answer(context, deadline, driver_id, REFUSED)


@then("by {deadline} driver {driver_id} has the answer that the trip is assigned to them")
def step_assigned_by(context, deadline, driver_id):
    check_answer(context, deadline, driver_id, ASSIGNED)


@then("trip {trip_id} is assigned to driver {driver_id}")
def step_assigned(context, trip_id, driver_id):
    actual = context.trips.driver_of(trip_id)
    assert actual == driver_id, f"trip {trip_id}: expected driver {driver_id}, the system has {actual}"


@then("trip {trip_id} is assigned to exactly one of drivers {first} and {second}")
def step_one_of(context, trip_id, first, second):
    told = [driver for driver in (first, second) if context.answers[(trip_id, driver)] == ASSIGNED]
    assert len(told) == 1, f"trip {trip_id}: expected 1 driver told assigned, the system told {len(told)}: {told}"
    assert context.trips.driver_of(trip_id) == told[0], f"trip {trip_id}: the table has {context.trips.driver_of(trip_id)}"


@then("every trip is assigned to exactly one of its two drivers")
def step_every_trip(context):
    for trip_id, drivers in context.pairs.items():
        told = [driver for driver in drivers if context.answers[(trip_id, driver)] == ASSIGNED]
        assert len(told) == 1, f"trip {trip_id}: expected 1 driver told assigned, the system told {len(told)}: {told}"
        assert context.trips.driver_of(trip_id) == told[0], f"trip {trip_id}: the table has {context.trips.driver_of(trip_id)}"


@then("{n:d} accept is refused")
@then("{n:d} accepts are refused")
def step_count_refused(context, n):
    refused = sum(1 for a in context.answers.values() if a == REFUSED)
    assert refused == n, f"expected {n} accepts refused, the system refused {refused}"


@when("this completion is received:")
def step_completion(context):
    """A completion on the stream: the tracking function keeps the trip's fare; the time taken is measured."""
    (row,) = list(context.table)
    started = time.monotonic()
    done = trips_of(context).complete(row["trip_id"], row["driver_id"], float(row["fare"]))
    assert done, f"trip {row['trip_id']} is not assigned to {row['driver_id']}: the completion was not kept"
    context.received, context.took_s = row["received_time"], time.monotonic() - started


@when("the rider of trip {trip_id} asks who is coming at {time}")
def step_rider_asks(context, trip_id, time):
    context.view = trips_of(context).rider_view(trip_id)


@then("the rider is shown driver {driver_id}")
def step_rider_driver(context, driver_id):
    assert context.view == {"driver": driver_id}, f"expected driver {driver_id}, the rider is shown {context.view}"


@then("by {deadline} the rider of trip {trip_id} is shown the fare {fare:g}")
def step_rider_fare(context, deadline, trip_id, fare):
    started = time.monotonic()
    view = trips_of(context).rider_view(trip_id)
    took = context.took_s + time.monotonic() - started
    allowed_s = seconds_between(context.received, deadline)
    assert view == {"fare": fare}, f"trip {trip_id}: expected the fare {fare}, the rider is shown {view}"
    assert took <= allowed_s, f"trip {trip_id}: the fare after {took:.2f} s, allowed {allowed_s:.0f} s"
