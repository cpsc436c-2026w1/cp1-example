"""The function t00-count-requests with a stand-in for the DynamoDB client, and the local code of the other rules."""
import base64
import json
from datetime import date

import pytest

from rides.assistant import MORE_THAN_ONE, NO_ANSWER, shown
from rides.compact import compact_day, count_by_zone
from rides.count_function import DynamoTables, handler
from rides.curate import Lake


class Cancelled(Exception):
    def __init__(self, code):
        self.response = {"CancellationReasons": [{"Code": code}, {"Code": "None"}]}


class FakeDynamo:
    """Keeps the seen ids and the counts as the transaction would; refuses a seen id with ConditionalCheckFailed."""

    class exceptions:
        TransactionCanceledException = Cancelled

    def __init__(self, fail_on=None):
        self.seen, self.counts, self.calls, self.fail_on = {}, {}, [], fail_on

    def transact_write_items(self, TransactItems, ReturnConsumedCapacity):
        put, update = TransactItems[0]["Put"], TransactItems[1]["Update"]
        event_id = put["Item"]["event_id"]["S"]
        self.calls.append(event_id)
        if event_id == self.fail_on:
            raise Cancelled("ThrottlingError")
        if event_id in self.seen:
            raise Cancelled("ConditionalCheckFailed")
        assert put["ConditionExpression"] == "attribute_not_exists(event_id)"
        key = (int(update["Key"]["zone_id"]["N"]), update["Key"]["period_start"]["S"])
        self.seen[event_id] = put["Item"]
        self.counts[key] = self.counts.get(key, 0) + 1
        return {"ConsumedCapacity": [{"TableName": "t00-seen-events", "CapacityUnits": 2.0},
                                     {"TableName": "t00-zone-counts", "CapacityUnits": 2.0}]}


def record(seq, **event):
    return {"kinesis": {"sequenceNumber": str(seq), "approximateArrivalTimestamp": 1795000000.25,
                        "data": base64.b64encode(json.dumps(event).encode()).decode()}}


def request(event_id, zone=161, t="2026-11-23T09:11:00Z"):
    return dict(event_type="trip_requested", event_id=event_id, trip_id="t-" + event_id, pickup_zone_id=zone, event_time=t)


def test_a_batch_counts_each_request_once_and_skips_other_events():
    db = FakeDynamo()
    tables = DynamoTables(db, "t00-zone-counts", "t00-seen-events", clock=lambda: 1795000001.0)
    batch = [record(1, **request("e1")), record(2, **request("e2")), record(3, **request("e1")),
             record(4, event_type="trip_accepted", event_id="e3", trip_id="t-e1", driver_id="d-1", event_time="2026-11-23T09:11:05Z")]
    assert handler({"Records": batch}, tables=tables) == {"batchItemFailures": []}
    assert db.counts == {(161, "2026-11-23T09:10:00Z"): 2}
    assert db.seen["e1"]["entered_ms"]["N"] == "1795000000250" and db.seen["e1"]["counted_ms"]["N"] == "1795000001000"
    assert db.seen["e1"]["expires_at"]["N"] == str(1795000000 + 24 * 3600)
    assert tables.consumed == 8.0


def test_a_batch_sent_again_after_a_failure_counts_nothing_twice():
    db = FakeDynamo(fail_on="e2")
    tables = DynamoTables(db, "c", "s")
    batch = [record(1, **request("e1")), record(2, **request("e2")), record(3, **request("e3"))]
    assert handler({"Records": batch}, tables=tables) == {"batchItemFailures": [{"itemIdentifier": "2"}]}
    assert db.counts == {(161, "2026-11-23T09:10:00Z"): 1}          # e3 not reached: Lambda retries from e2
    db.fail_on = None
    handler({"Records": batch}, tables=tables)                       # Lambda sends the batch again
    assert db.counts == {(161, "2026-11-23T09:10:00Z"): 3}


def test_a_late_request_goes_to_the_period_of_its_event_time():
    db = FakeDynamo()
    handler({"Records": [record(1, **request("e1", 48, "2026-11-23T09:02:00Z"))]}, tables=DynamoTables(db, "c", "s"))
    assert db.counts == {(48, "2026-11-23T09:00:00Z"): 1}


def test_curate_splits_by_fare():
    lake = Lake()
    rows = [dict(trip_id="a", fare="9.11"), dict(trip_id="b", fare=""), dict(trip_id="c", fare="0.0"), dict(trip_id="d", fare="-4.5")]
    assert lake.load_file("2026-11-22", rows) == (1, 3)
    assert [r["reason"] for r in lake.rejected["2026-11-22"]] == ["no fare", "fare not above 0", "fare not above 0"]
    lake.load_file("2026-11-22", rows)                                # the same file again: no row twice
    assert len(lake.curated["2026-11-22"]) == 1


def test_compaction_keeps_a_request_received_after_midnight_in_its_day(tmp_path):
    raw, table = tmp_path / "raw", tmp_path / "table"
    late = dict(request("e1", 48, "2026-11-22T23:59:59Z"), received_time="2026-11-23T00:00:00Z")
    (raw / "dt=2026-11-23" / "hour=00").mkdir(parents=True)
    (raw / "dt=2026-11-23" / "hour=00" / "deliveries-00.jsonl").write_text(json.dumps(late) + "\n")
    compact_day(raw, table, date(2026, 11, 22))
    assert count_by_zone(table, date(2026, 11, 22), date(2026, 11, 22)) == {48: 1}


@pytest.mark.parametrize("reply, want", [('{"pickup_place": "Penn Station"}', "Penn Station"),
                                         ('{"pickup_place": null}', None),
                                         ('{"pickup_place": "more than one"}', MORE_THAN_ONE),
                                         ('{"pickup_place": "LGA Terminal B"}', NO_ANSWER),
                                         ('Sure! {"pickup_place": "Penn Station"}', NO_ANSWER)])
def test_what_the_page_shows_for_a_reply(reply, want):
    assert shown(reply, ["Penn Station", "Grand Central Terminal"]) == want
