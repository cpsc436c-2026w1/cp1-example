"""Trips requested in each pickup zone for each 5-minute period (R010, R020, R030, RF010, RF020).

The rule of the function `t00-count-requests`: for each request on the stream, add 1 to the count of its zone and of
the period of its event time (a late request corrects the count of its own period, R020), once for each `event_id`
(RF010). The request's id and the count are written in one step: on AWS one DynamoDB transaction on the tables
`t00-seen-events` and `t00-zone-counts` (src/rides/count_function.py); here `MemoryTables` stands in for the two
tables, so the examples run without AWS. A zone and period without a request get no count: they are shown as
`no data` (RF020). Standard library only: Lambda runs this file as it is.
"""
import os
import threading
from datetime import datetime, timedelta, timezone

PERIOD = timedelta(minutes=5)
NO_DATA = "no data"


def parse(time: str) -> datetime:
    return datetime.fromisoformat(time.replace("Z", "+00:00"))


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def period_start(event_time: str) -> str:
    """Start of the 5-minute period that holds the time: 09:13:40 is in the period between 09:10 and 09:15."""
    t = parse(event_time)
    return iso(t.replace(minute=t.minute - t.minute % 5, second=0, microsecond=0))


def period_end(start: str) -> str:
    return iso(parse(start) + PERIOD)


def dedupe_is_on() -> bool:
    """DEDUPE=off in the environment turns the duplicate check off (the studio's prediction step)."""
    return os.environ.get("DEDUPE", "on").lower() != "off"


class MemoryTables:
    """Stands in for t00-zone-counts (a count for each zone and period start) and t00-seen-events (each counted
    event_id). The lock makes "keep the id if it is new, and add 1" one step, as the transaction does on AWS."""

    def __init__(self):
        self.counts: dict[tuple[int, str], int] = {}
        self.seen: dict[str, dict] = {}
        self._lock = threading.Lock()

    def count_once(self, event_id: str, zone: int, start: str, info: dict) -> bool:
        """Count the request unless its id was counted before. True when it was counted now."""
        with self._lock:
            if event_id in self.seen:
                return False
            self.seen[event_id] = dict(info, zone=zone, period_start=start)
            self.counts[(zone, start)] = self.counts.get((zone, start), 0) + 1
            return True

    def add(self, zone: int, start: str) -> None:
        """The count without the duplicate check (DEDUPE=off)."""
        with self._lock:
            self.counts[(zone, start)] = self.counts.get((zone, start), 0) + 1

    def count(self, zone: int, start: str):
        return self.counts.get((zone, start), NO_DATA)

    def rows(self) -> list[dict]:
        return [dict(zone=z, start=s, end=period_end(s), trips=n) for (z, s), n in sorted(self.counts.items())]


def count_request(tables, event: dict, dedupe: bool | None = None, **info) -> str:
    """One delivery from the stream. Returns counted, repeat (its id was counted before) or skipped (not a request)."""
    if event.get("event_type") != "trip_requested":
        return "skipped"
    dedupe = dedupe_is_on() if dedupe is None else dedupe
    zone, start = int(event["pickup_zone_id"]), period_start(event["event_time"])
    if not dedupe:
        tables.add(zone, start)
        return "counted"
    return "counted" if tables.count_once(event["event_id"], zone, start, info) else "repeat"


class LocalSlice:
    """The counting path without AWS: the stream hands each delivery to the rule, in the order received."""

    target = "local"

    def __init__(self):
        self.tables = MemoryTables()

    def send(self, deliveries: list[dict], wait: bool = True) -> None:
        for d in deliveries:
            count_request(self.tables, d, received_time=d.get("received_time"))

    def count(self, zone: int, start: str):
        return self.tables.count(zone, start)

    def rows(self) -> list[dict]:
        return self.tables.rows()


def received_by(deliveries: list[dict], read_at: str | None) -> list[dict]:
    """The deliveries received up to read_at, in the order received."""
    out = [d for d in deliveries if read_at is None or parse(d["received_time"]) <= parse(read_at)]
    return sorted(out, key=lambda d: parse(d["received_time"]))


def count_requests(deliveries: list[dict], read_at: str | None = None, dedupe: bool | None = None) -> dict:
    """Counts by (pickup zone, period start) from the deliveries received up to read_at."""
    tables = MemoryTables()
    for d in received_by(deliveries, read_at):
        count_request(tables, d, dedupe=dedupe)
    return dict(tables.counts)


def show(counts: dict, zone: int, start: str):
    """What a reader sees for one zone and period: the count, or `no data`."""
    return counts.get((zone, start), NO_DATA)
