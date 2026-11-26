"""The function t00-count-requests: Lambda calls it with each batch of records of the stream t00-trip-events.

From the course recipe streaming-ingestion (cpsc436c-2026w1/recipes, streaming-ingestion/main/consumer.py): the batch
loop, a failed record reported by its sequence number (ReportBatchItemFailures) so Lambda retries from it, and one
log line of counts for each batch, not one for each record. Changed for the rides case: each request is counted by
the rule of src/rides/counting.py, and its event_id and its count are written in one DynamoDB transaction
(docs/reviews/well-architected.md, question 1): a batch that Lambda sends again after a failure cannot count a request twice, and a
request is never marked seen without being counted.

The seen-events item also keeps the times the replay test reads (RQ020, sim/latency.py): when the record entered the
stream (Kinesis approximateArrivalTimestamp) and when the transaction finished, in epoch milliseconds, and it
expires 24 hours after the record entered the stream (Q030; DynamoDB time to live on `expires_at`).
Lambda's Python runtime has boto3; this package holds rides/counting.py and this file only (scripts/counting.py).
"""
import base64
import json
import os
import time

from rides.counting import count_request, dedupe_is_on, period_end

KEEP_S = 24 * 3600                                   # an id is kept 24 hours (RF010, Q030)


class DynamoTables:
    """t00-zone-counts (key zone_id, period_start) and t00-seen-events (key event_id) behind the calls the rule makes."""

    def __init__(self, client=None, counts=None, seen=None, clock=time.time):
        if client is None:
            import boto3                             # in Lambda's runtime; not needed by the local examples
            client = boto3.client("dynamodb")
        self.client, self.clock = client, clock
        self.counts_table = counts or os.environ.get("COUNTS_TABLE", "t00-zone-counts")
        self.seen_table = seen or os.environ.get("SEEN_TABLE", "t00-seen-events")
        self.consumed = 0.0                          # write units, as DynamoDB reports them (ReturnConsumedCapacity)

    def _count_update(self, zone: int, start: str) -> dict:
        return {"TableName": self.counts_table,
                "Key": {"zone_id": {"N": str(zone)}, "period_start": {"S": start}},
                "UpdateExpression": "ADD trips :one SET period_end = :end, updated_ms = :now",
                "ExpressionAttributeValues": {":one": {"N": "1"}, ":end": {"S": period_end(start)},
                                              ":now": {"N": str(int(self.clock() * 1000))}}}

    def count_once(self, event_id: str, zone: int, start: str, info: dict) -> bool:
        now_ms = int(self.clock() * 1000)
        entered_ms = int(info.get("entered_ms") or now_ms)
        seen = {"event_id": {"S": event_id}, "zone_id": {"N": str(zone)}, "period_start": {"S": start},
                "event_time": {"S": info.get("event_time", "")}, "entered_ms": {"N": str(entered_ms)},
                "counted_ms": {"N": str(now_ms)}, "expires_at": {"N": str(entered_ms // 1000 + KEEP_S)}}
        try:
            resp = self.client.transact_write_items(
                TransactItems=[{"Put": {"TableName": self.seen_table, "Item": seen,
                                        "ConditionExpression": "attribute_not_exists(event_id)"}},
                               {"Update": self._count_update(zone, start)}],
                ReturnConsumedCapacity="TOTAL")
            self.consumed += sum(c.get("CapacityUnits", 0) for c in resp.get("ConsumedCapacity", []))
            return True
        except self.client.exceptions.TransactionCanceledException as err:
            reasons = err.response.get("CancellationReasons", [])
            if reasons and reasons[0].get("Code") == "ConditionalCheckFailed":
                return False                         # counted before: a second delivery of the same event
            raise

    def add(self, zone: int, start: str) -> None:
        resp = self.client.update_item(**self._count_update(zone, start), ReturnConsumedCapacity="TOTAL")
        self.consumed += resp.get("ConsumedCapacity", {}).get("CapacityUnits", 0)


_tables = None


def handler(event, context=None, tables=None):
    """Lambda entry point for the Kinesis event source mapping."""
    global _tables
    if tables is None:
        _tables = _tables or DynamoTables()
        tables = _tables
    tables.consumed = 0.0
    counts = {"counted": 0, "repeat": 0, "skipped": 0}
    dedupe = dedupe_is_on()
    for record in event["Records"]:
        k = record["kinesis"]
        try:
            delivery = json.loads(base64.b64decode(k["data"]))
            entered_ms = int(float(k["approximateArrivalTimestamp"]) * 1000)
            counts[count_request(tables, delivery, dedupe=dedupe, entered_ms=entered_ms,
                                 event_time=delivery.get("event_time", ""))] += 1
        except Exception as err:   # a bad record or a refused write: report it, and stop this batch here
            print(json.dumps({"failed": k["sequenceNumber"], "error": repr(err), **counts}))
            return {"batchItemFailures": [{"itemIdentifier": k["sequenceNumber"]}]}
    print(json.dumps({**counts, "records": len(event["Records"]), "write_units": tables.consumed}))
    return {"batchItemFailures": []}
