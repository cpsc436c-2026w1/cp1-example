"""RQ010: what one year of the design costs, in CAD, at the course price sheet's rates (docs/design.md, Cost).

    uv run python scripts/year_cost.py          # prints the table of docs/design.md, Cost

Volumes come from DS01 (measured) and Q050 (one request for each completed trip, assumed); units of work per event
come from the run on AWS (evidence/units.json, scripts/run_units.py: measured); rates from the price sheet,
ca-central-1, 2026-11-18. A row whose units are not measured says so (`assumed`). Standard library only.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAD = 1.45                                     # price sheet: the gateway converts USD to CAD at 1.45
DAYS = 365
TRIPS_MARCH = 6_045_943                        # DS01, Uber trips picked up in Manhattan, March 2024 (measured)
TRIPS_DAY = TRIPS_MARCH / 31
EVENTS_PER_TRIP = 3                            # trip_requested, trip_accepted, trip_completed (docs/design.md, Data)


def rows(units: dict) -> list[tuple]:
    x10 = units["per_replay"]["rq020-x10"]
    x50 = units["per_replay"]["rq020-x50"]
    # Billed ms of one run = fixed + per record, fitted on the 10x and 50x replays (measured).
    per_record = (x50["ms_per_run"] - x10["ms_per_run"]) / (x50["records_per_run"] - x10["records_per_run"])
    fixed = x10["ms_per_run"] - per_record * x10["records_per_run"]
    events_s = TRIPS_DAY * EVENTS_PER_TRIP / 86400
    runs_year = DAYS * 86400                   # 1 shard, a batch at most every 1 s: about one run a second
    ms_run = fixed + per_record * events_s
    requests_year = TRIPS_DAY * DAYS
    events_year = requests_year * EVENTS_PER_TRIP
    log_bytes_run = units["log_bytes"] / max(units["lambda_runs"], 1)
    wru = x10["write_units_per_counted"]
    return [
        # (part, units a year, how many, rate, rate unit, source of the units)
        ("Kinesis stream, 1 shard", "shard-hours", DAYS * 24, 0.0165, "per shard-hour", "1 shard for the whole year"),
        ("Kinesis PUT payload units", "million units", events_year / 1e6, 0.0154, "per million",
         f"{EVENTS_PER_TRIP} events a trip, each under 25 KB"),
        ("Lambda requests", "million runs", runs_year / 1e6, 0.20, "per million",
         f"assumed: one run a second (Lambda polls a shard once a second) at {events_s:.1f} events a second"),
        ("Lambda duration, arm64, 128 MB", "GB-seconds", runs_year * ms_run / 1000 * 0.125, 0.0000133334, "per GB-second",
         f"measured: {fixed:.1f} ms a run + {per_record:.1f} ms a record = {ms_run:.0f} ms"),
        ("DynamoDB writes, counting", "million write units", requests_year * wru / 1e6, 0.6875, "per million",
         f"measured: {wru:g} write units a request (a transaction of 2 items)"),
        ("CloudWatch Logs, counting function", "GB", runs_year * log_bytes_run / 1e9, 0.55, "per GB",
         f"measured: {log_bytes_run:.0f} bytes a run"),
    ]


def rest(requests_year: float, events_year: float) -> list[tuple]:
    """The parts of the design that are not built yet: their units are assumed."""
    return [
        ("Athena, the 30-day count", "TB scanned", 50 * DAYS * 0.05 / 1000, 5.50, "per TB",
         "assumed: 50 queries a day, 50 MB each"),
        ("Firehose to the lake", "GB", events_year * 250 / 1e9, 0.032, "per GB", "assumed: 250 bytes an event"),
        ("S3 storage, raw and compacted", "GB-months", 12 * events_year * 250 / 1e9 / 2, 0.025, "per GB-month",
         "assumed: half a year's events on average"),
        ("S3 PUTs from Firehose", "thousand requests", DAYS * 1440 / 1000, 0.0055, "per thousand", "one file a minute"),
        ("Glue jobs, compaction and curation", "DPU-hours", 2 * DAYS * 2 * 5 / 60, 0.308, "per DPU-hour",
         "assumed: 2 jobs a night, 2 DPUs, 5 minutes"),
        ("DynamoDB writes, trips", "million write units", requests_year * 2 / 1e6, 0.6875, "per million",
         "assumed: 2 writes a trip (assign, complete)"),
        ("API Gateway HTTP API", "million requests", requests_year * 2 / 1e6, 1.11, "per million",
         "assumed: an accept and a rider's read a trip"),
        ("Lambda requests, assign and read functions", "million runs", requests_year * 2 / 1e6, 0.20, "per million",
         "assumed: one run for each API request"),
        ("Lambda duration, assign and read functions", "GB-seconds", requests_year * 2 * 0.05 * 0.125, 0.0000133334,
         "per GB-second", "assumed: 50 ms at 128 MB a run"),
        ("Course LLM gateway, the assistant", "million requests", 200 * DAYS / 1e6, (600 * 0.10 + 20 * 0.20) / CAD,
         "per million", "assumed (Q040): 200 messages a day, 600 input and 20 output tokens each, qwen3.8-27b at 0.10 and 0.20 CAD per million tokens"),
    ]


def money(rate: float) -> str:
    return f"{rate:.10f}".rstrip("0").rstrip(".") if rate < 0.01 else f"{rate:g}"


def main() -> int:
    units = json.loads((ROOT / "evidence" / "units.json").read_text())
    requests_year = TRIPS_DAY * DAYS
    totals = []
    print("| Part | Units a year | Rate (USD) | USD a year | Where the units come from |")
    print("|---|---|---|---|---|")
    for title, part in (("**Counting path, deployed** (units measured on AWS)", rows(units)),
                        ("**The rest of the design, not built yet** (units assumed)",
                         rest(requests_year, requests_year * EVENTS_PER_TRIP))):
        print(f"| {title} | | | | |")
        usd = 0.0
        for name, unit, n, rate, per, src in part:
            usd += n * rate
            print(f"| {name} | {n:,.2f} {unit} | {money(rate)} {per} | {n * rate:,.2f} | {src} |")
        totals.append(usd)
    print(f"\ncounting path: {totals[0]:,.2f} USD = {totals[0] * CAD:,.2f} CAD a year")
    print(f"rest of the design: {totals[1]:,.2f} USD = {totals[1] * CAD:,.2f} CAD a year")
    print(f"whole design: {sum(totals):,.2f} USD = {sum(totals) * CAD:,.2f} CAD a year")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
