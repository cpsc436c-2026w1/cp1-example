"""The deployed counting path, as the examples and the replay test use it: stream t00-trip-events, function
t00-count-requests, tables t00-zone-counts and t00-seen-events (scripts/stream.py, scripts/counting.py).

    TARGET=aws uv run behave features/js01_trips_per_zone.feature --tags="not @todo"   # JS01's counting examples on AWS

`AwsSlice` has the methods of `LocalSlice` (src/rides/counting.py): send the deliveries to the stream in the order
received, read a count, read the rows of the dashboard. A send waits until the function has counted every request
it sent: each counted event_id is an item of t00-seen-events (no test hook in the function). It needs boto3, so it
runs under `uv run`, not under `uvx behave@1.3.3` (the local examples do not import it).
"""
import json
import os
import time

from rides.counting import NO_DATA, period_end

PUT_LIMIT = 500                       # PutRecords takes at most 500 records a call


class AwsSlice:
    target = "aws"

    def __init__(self, session=None):
        import boto3
        s = session or boto3.Session(region_name=os.environ.get("AWS_REGION", "ca-central-1"))
        p = os.environ.get("PREFIX", "t00")
        self.stream, self.counts_table, self.seen_table = f"{p}-trip-events", f"{p}-zone-counts", f"{p}-seen-events"
        self.kinesis, self.ddb = s.client("kinesis"), s.client("dynamodb")
        self.put_calls, self.records_put = 0, 0

    # -- writing
    def put(self, deliveries: list[dict]) -> None:
        """Each delivery as one record, its event fields only (received_time is set by the stream), keyed by trip."""
        for i in range(0, len(deliveries), PUT_LIMIT):
            records = [{"Data": json.dumps({k: v for k, v in d.items() if k != "received_time"}).encode(),
                        "PartitionKey": str(d.get("trip_id") or d["event_id"])} for d in deliveries[i:i + PUT_LIMIT]]
            for attempt in range(5):
                self.put_calls += 1
                resp = self.kinesis.put_records(StreamName=self.stream, Records=records)
                failed = [r for r, out in zip(records, resp["Records"]) if out.get("ErrorCode")]
                self.records_put += len(records) - len(failed)
                if not failed:
                    break
                records = failed
                time.sleep(0.1 * 2 ** attempt)
            else:
                raise RuntimeError(f"{len(records)} records refused after 5 calls")

    def send(self, deliveries: list[dict], wait: bool = True, timeout_s: float = 120) -> None:
        self.put(deliveries)
        if wait:
            self.wait_counted({d["event_id"] for d in deliveries if d.get("event_type") == "trip_requested"}, timeout_s)

    def wait_counted(self, event_ids: set[str], timeout_s: float = 120) -> float:
        """Wait until every id is in t00-seen-events; returns the seconds waited."""
        start, left = time.monotonic(), set(event_ids)
        while left:
            for chunk in [sorted(left)[i:i + 100] for i in range(0, len(left), 100)]:
                resp = self.ddb.batch_get_item(RequestItems={self.seen_table: {
                    "Keys": [{"event_id": {"S": i}} for i in chunk], "ProjectionExpression": "event_id"}})
                left -= {item["event_id"]["S"] for item in resp["Responses"].get(self.seen_table, [])}
            if left and time.monotonic() - start > timeout_s:
                raise TimeoutError(f"{len(left)} of {len(event_ids)} requests not counted after {timeout_s:.0f} s")
            if left:
                time.sleep(0.5)
        return time.monotonic() - start

    def clear(self) -> None:
        for table, keys in ((self.counts_table, ("zone_id", "period_start")), (self.seen_table, ("event_id",))):
            for page in self.ddb.get_paginator("scan").paginate(TableName=table, ProjectionExpression=", ".join(keys)):
                for i in range(0, len(page["Items"]), 25):
                    batch = [{"DeleteRequest": {"Key": item}} for item in page["Items"][i:i + 25]]
                    while batch:
                        batch = self.ddb.batch_write_item(RequestItems={table: batch}).get(
                            "UnprocessedItems", {}).get(table, [])

    # -- reading, as the read function will
    def count(self, zone: int, start: str):
        item = self.ddb.get_item(TableName=self.counts_table, ConsistentRead=True,
                                 Key={"zone_id": {"N": str(zone)}, "period_start": {"S": start}}).get("Item")
        return int(item["trips"]["N"]) if item else NO_DATA

    def rows(self) -> list[dict]:
        out = []
        for page in self.ddb.get_paginator("scan").paginate(TableName=self.counts_table, ConsistentRead=True):
            out += [dict(zone=int(i["zone_id"]["N"]), start=i["period_start"]["S"],
                         end=i.get("period_end", {}).get("S") or period_end(i["period_start"]["S"]),
                         trips=int(i["trips"]["N"])) for i in page["Items"]]
        return sorted(out, key=lambda r: (r["zone"], r["start"]))

    def seen(self) -> list[dict]:
        out = []
        for page in self.ddb.get_paginator("scan").paginate(TableName=self.seen_table):
            out += [{k: (int(v["N"]) if "N" in v else v["S"]) for k, v in i.items()} for i in page["Items"]]
        return sorted(out, key=lambda r: r["event_id"])
