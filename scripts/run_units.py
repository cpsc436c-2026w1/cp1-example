"""The measured units of a run on AWS, and their cost at the course price sheet's rates (docs/design.md, Cost).

    uv run python scripts/run_units.py --start 2026-11-26T05:50:00Z --end 2026-11-26T08:30:00Z --stream-hours 2.6
    uv run python scripts/run_units.py --recost --stream-hours 2.7    # after the teardown: the stream's real hours,
                                                                      # the units already in evidence/units.json

It reads CloudWatch, which only reads (GetMetricData, FilterLogEvents): records and bytes into the stream, the
function's runs and billed milliseconds (its REPORT log lines), the write and read units of both tables, and the log
bytes received. For each replay of evidence/rq020-x*/ it also counts, from the function's log lines in that replay's
window, its runs, billed milliseconds, records, counted requests and write units (`per_replay`).
Run it before scripts/teardown.sh --yes deletes the log group. The stream's hours are its life, from `stream.py up`
to the teardown (given). It writes evidence/units.json and prints the cost in USD and in CAD
(1.45 CAD a USD, the rate of the price sheet). The free tier is left out, as the price sheet says.
"""
import argparse
import json
import re
from datetime import datetime

from common import ROOT, names, session

RATES = {   # price sheet, ca-central-1, 2026-11-18 (USD)
    "shard_hour": 0.0165, "put_unit_million": 0.0154, "lambda_request_million": 0.20,
    "lambda_gb_s_arm": 0.0000133334, "wru_million": 0.6875, "rru_million": 0.1375, "log_gb": 0.55,
}
CAD = 1.45


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def metric_sum(cw, namespace: str, metric: str, dims: dict, start, end) -> float:
    resp = cw.get_metric_data(StartTime=start, EndTime=end, MetricDataQueries=[{
        "Id": "m", "ReturnData": True, "MetricStat": {"Stat": "Sum", "Period": 3600, "Metric": {
            "Namespace": namespace, "MetricName": metric,
            "Dimensions": [{"Name": k, "Value": v} for k, v in dims.items()]}}}])
    return sum(resp["MetricDataResults"][0]["Values"])


def ms(text: str) -> int:
    return int(utc(text).timestamp() * 1000)


def per_replay(logs, group: str) -> dict:
    """Runs, billed ms, records, counted requests and write units of the function during each replay."""
    windows = []
    for folder in sorted(p for p in (ROOT / "evidence").glob("rq020-x*") if (p / "sent.jsonl").exists()):
        times = sorted(json.loads(x)["sent_time"] for x in (folder / "sent.jsonl").read_text().splitlines())
        windows.append([folder.name, ms(times[0]) - 1000, ms(times[-1]) + 20000])
    windows.sort(key=lambda w: w[1])
    for here, after in zip(windows, windows[1:]):
        here[2] = min(here[2], after[1] - 500)                   # stop where the next replay begins
    out = {}
    for name, a, b in windows:
        r = dict(runs=0, billed_ms=0, records=0, counted=0, repeat=0, write_units=0.0)
        for page in logs.get_paginator("filter_log_events").paginate(logGroupName=group, startTime=a, endTime=b):
            for e in page["events"]:
                m = e["message"]
                if m.startswith("REPORT"):
                    r["runs"] += 1
                    r["billed_ms"] += int(re.search(r"Billed Duration: (\d+) ms", m).group(1))
                elif m.startswith("{"):
                    d = json.loads(m)
                    for k in ("records", "counted", "repeat"):
                        r[k] += d.get(k, 0)
                    r["write_units"] += d.get("write_units", 0)
        r["ms_per_run"] = round(r["billed_ms"] / max(r["runs"], 1), 1)
        r["records_per_run"] = round(r["records"] / max(r["runs"], 1), 2)
        r["write_units_per_counted"] = round(r["write_units"] / max(r["counted"], 1), 2)
        out[name] = r
    return out


def costs(units: dict) -> dict:
    wru, rru = sum(units["write_units"].values()), sum(units["read_units"].values())
    return {   # records under 25 KB: one PUT payload unit each
        "Kinesis shard-hours": units["stream_hours"] * RATES["shard_hour"],
        "Kinesis PUT payload units": units["records_in"] / 1e6 * RATES["put_unit_million"],
        "Lambda requests": units["lambda_runs"] / 1e6 * RATES["lambda_request_million"],
        "Lambda duration (arm64)": units["lambda_gb_s"] * RATES["lambda_gb_s_arm"],
        "DynamoDB write units": wru / 1e6 * RATES["wru_million"],
        "DynamoDB read units": rru / 1e6 * RATES["rru_million"],
        "CloudWatch Logs ingestion": units["log_bytes"] / 1e9 * RATES["log_gb"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--stream-hours", type=float, required=True)
    ap.add_argument("--recost", action="store_true", help="no AWS call: the units of evidence/units.json")
    args = ap.parse_args()
    path = ROOT / "evidence" / "units.json"
    if args.recost:
        units = json.loads(path.read_text())
        units["stream_hours"] = args.stream_hours
    else:
        units = measure(args.start, args.end, args.stream_hours)
    cost = costs(units)
    units["cost_usd"] = {k: round(v, 6) for k, v in cost.items()}
    units["total_usd"] = round(sum(cost.values()), 4)
    units["total_cad"] = round(sum(cost.values()) * CAD, 4)
    path.write_text(json.dumps(units, indent=2) + "\n")
    print(json.dumps({k: v for k, v in units.items() if k not in ("cost_usd", "per_replay")}, indent=2))
    for k, v in cost.items():
        print(f"{k:28} {v:10.6f} USD")
    print(f"{'total':28} {units['total_usd']:10.4f} USD = {units['total_cad']:.4f} CAD")
    return 0


def measure(start_text: str, end_text: str, stream_hours: float) -> dict:
    s, n = session(), names()
    cw, logs = s.client("cloudwatch"), s.client("logs")
    start, end = utc(start_text), utc(end_text)
    runs, billed_ms, memory_mb = 0, 0, 128
    for page in logs.get_paginator("filter_log_events").paginate(
            logGroupName=n["log_group"], filterPattern="REPORT", startTime=int(start.timestamp() * 1000),
            endTime=int(end.timestamp() * 1000)):
        for e in page["events"]:
            runs += 1
            billed_ms += int(re.search(r"Billed Duration: (\d+) ms", e["message"]).group(1))
            memory_mb = int(re.search(r"Memory Size: (\d+) MB", e["message"]).group(1))
    return {
        "window": [start_text, end_text],
        "stream_hours": stream_hours,
        "records_in": metric_sum(cw, "AWS/Kinesis", "IncomingRecords", {"StreamName": n["stream"]}, start, end),
        "bytes_in": metric_sum(cw, "AWS/Kinesis", "IncomingBytes", {"StreamName": n["stream"]}, start, end),
        "lambda_runs": runs, "lambda_billed_ms": billed_ms, "lambda_memory_mb": memory_mb,
        "lambda_gb_s": billed_ms / 1000 * memory_mb / 1024,
        "write_units": {t: metric_sum(cw, "AWS/DynamoDB", "ConsumedWriteCapacityUnits", {"TableName": t}, start, end)
                        for t in (n["counts"], n["seen"])},
        "read_units": {t: metric_sum(cw, "AWS/DynamoDB", "ConsumedReadCapacityUnits", {"TableName": t}, start, end)
                       for t in (n["counts"], n["seen"])},
        "log_bytes": metric_sum(cw, "AWS/Logs", "IncomingBytes", {"LogGroupName": n["log_group"]}, start, end),
        "per_replay": per_replay(logs, n["log_group"]),
    }


if __name__ == "__main__":
    raise SystemExit(main())
