"""The replay test of RQ020: SIM01 at a chosen speed through the deployed counting path, and R010's data latency.

    uv run python sim/replay_test.py --speed 50          # about 1.5 minutes
    uv run python sim/replay_test.py --speed 10          # about 7 minutes
    uv run python sim/replay_test.py --speed 1           # 71 minutes
    uv run python sim/replay_test.py --report evidence/rq020-x10   # the report again, from the files of a run

It empties the two tables, replays SIM01's deliveries received up to 10:11 (the time the SIM01 example reads the
counts; every request and both late ones are in by then) with the course replayer (sim/replay.py, from the recipe
simulated-runs, copied unchanged), waits until every request is counted, and writes to evidence/rq020-x<speed>/:
sent.jsonl and summary.json (the replayer), seen.jsonl (t00-seen-events: when each request entered the stream and
when it was counted), counts.jsonl (t00-zone-counts) and report.json (below).

R010's data latency of a zone and period: from the moment the replay reaches the period's end (its wall time at
this speed) to the moment the stored count holds every request received by then; 0 when it held them before the
end. R020's: from the moment a late request was sent to the moment its period's count was corrected. Each is given
as median, p95 and max (p95 here: the smallest value that 95 of every 100 stay within). The counts are compared with
SIM01's truth (_truth/events.jsonl), not with the system's output.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from rides.counting import parse, period_end, period_start  # noqa: E402
from sim import replay as rp  # noqa: E402

UNTIL = "2026-11-23T10:11:00Z"


def ms(text: str) -> int:
    return int(parse(text).timestamp() * 1000)


def pct(values: list[float], p: float) -> float | None:
    """The smallest value that p of every 100 stay within (nearest rank)."""
    if not values:
        return None
    v = sorted(values)
    return v[max(0, -(-len(v) * p // 100) - 1)]


def spread(values: list[float]) -> dict:
    return {"n": len(values), "median_s": pct(values, 50), "p95_s": pct(values, 95), "max_s": max(values, default=None)}


def report(folder: Path, speed: float) -> dict:
    deliveries = [d for d in rp.load_deliveries("SIM01") if d["received_time"] <= UNTIL]
    run_id = folder.name
    sent = {}
    for line in map(json.loads, (folder / "sent.jsonl").read_text().splitlines()):
        sent.setdefault(rp.unprefixed(line["event_id"], run_id), ms(line["sent_time"]))   # first send of each id
    seen = {rp.unprefixed(s["event_id"], run_id): s for s in map(json.loads, (folder / "seen.jsonl").read_text().splitlines())}
    start_ms, first_r = min(sent.values()), min(ms(d["received_time"]) for d in deliveries)
    wall = lambda sim_ms: start_ms + (sim_ms - first_r) / speed    # noqa: E731  the replay's clock for a sim time
    requests = {}
    for d in deliveries:                                           # first delivery of each request
        if d["event_type"] == "trip_requested":
            requests.setdefault(d["event_id"], d)
    lags = [(seen[i]["counted_ms"] - sent[i]) / 1000 for i in requests if i in seen]
    to_stream = [(seen[i]["entered_ms"] - sent[i]) / 1000 for i in requests if i in seen]
    in_stream = [(seen[i]["counted_ms"] - seen[i]["entered_ms"]) / 1000 for i in requests if i in seen]
    r010, r020 = [], []
    periods = {}
    for d in requests.values():
        periods.setdefault((d["pickup_zone_id"], period_start(d["event_time"])), []).append(d)
    for (_, start), ds in sorted(periods.items()):
        end_ms = ms(period_end(start))
        on_time = [d for d in ds if ms(d["received_time"]) <= end_ms]
        if on_time:
            complete = max(seen[d["event_id"]]["counted_ms"] for d in on_time)
            r010.append(max(0.0, (complete - wall(end_ms)) / 1000))
        r020 += [(seen[d["event_id"]]["counted_ms"] - sent[d["event_id"]]) / 1000 for d in ds if ms(d["received_time"]) > end_ms]
    truth = [json.loads(x) for x in (ROOT / "sim/data/SIM01/_truth/events.jsonl").read_text().splitlines()]
    want = Counter(e["pickup_zone_id"] for e in truth if e["event_type"] == "trip_requested")
    counts = [json.loads(x) for x in (folder / "counts.jsonl").read_text().splitlines()]
    got = Counter()
    for c in counts:
        if "2026-11-23T09:00:00Z" <= c["start"] < "2026-11-23T10:00:00Z":
            got[c["zone"]] += c["trips"]
    summary = json.loads((folder / "summary.json").read_text())
    out = {"run_id": run_id, "speed": speed, "deliveries_sent": summary["sent"], "put_calls": summary["calls"],
           "replay_s": summary["seconds"], "requests": len(requests), "counted": len(seen),
           "r010_data_latency": spread(r010), "r020_data_latency": spread(r020),
           "request_lag": spread(lags), "lag_to_stream": spread(to_stream), "lag_stream_to_count": spread(in_stream),
           "trips_09_to_10": {str(z): got[z] for z in sorted(want)},
           "truth_09_to_10": {str(z): want[z] for z in sorted(want)}, "counts_match_truth": got == want}
    (folder / "report.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def show(r: dict) -> str:
    f = lambda s: (f"median {s['median_s']:.2f} s, p95 {s['p95_s']:.2f} s, max {s['max_s']:.2f} s ({s['n']})"  # noqa: E731
                   if s["n"] else "none")
    return "\n".join([
        f"replay {r['run_id']}: {r['deliveries_sent']} deliveries in {r['put_calls']} PutRecords calls, "
        f"{r['replay_s']:.0f} s at {r['speed']:g} times SIM01's speed; {r['counted']} of {r['requests']} requests counted",
        f"R010 data latency, zone and period ({r['r010_data_latency']['n']}): {f(r['r010_data_latency'])}",
        f"R020 data latency, late requests: {f(r['r020_data_latency'])}",
        f"each request, sent to counted: {f(r['request_lag'])}",
        f"  sent to in the stream: {f(r['lag_to_stream'])}",
        f"  in the stream to counted: {f(r['lag_stream_to_count'])}",
        f"trips 09:00 to 10:00, zones {', '.join(r['trips_09_to_10'])}: {', '.join(map(str, r['trips_09_to_10'].values()))} "
        f"(truth {', '.join(map(str, r['truth_09_to_10'].values()))}): {'match' if r['counts_match_truth'] else 'DIFFER'}"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--speed", type=float, default=50)
    ap.add_argument("--report", type=Path, help="only write the report of a run folder again")
    args = ap.parse_args()
    if args.report:
        print(show(report(args.report, json.loads((args.report / "summary.json").read_text())["speed"])))
        return 0
    from rides.aws_slice import AwsSlice
    aws = AwsSlice()
    aws.clear()
    run_id = f"rq020-x{args.speed:g}"
    folder = ROOT / "evidence" / run_id
    deliveries = [d for d in rp.load_deliveries("SIM01") if d["received_time"] <= UNTIL]
    sender = rp.KinesisSender(aws.kinesis, aws.stream)
    (folder).mkdir(parents=True, exist_ok=True)
    (folder / "command.txt").write_text(f"sim/replay_test.py --speed {args.speed:g}\nstarted "
                                        f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}\ncommit {rp._commit()}\n")
    summary = rp.replay(deliveries, sender, run_id, args.speed, evidence=folder)
    print(f"replayed {summary['sent']} deliveries ({summary['failed']} failed) in {summary['seconds']:.0f} s")
    ids = {rp.prefixed(d, run_id)["event_id"] for d in deliveries if d["event_type"] == "trip_requested"}
    waited = aws.wait_counted(ids, timeout_s=300)
    print(f"every request counted {waited:.1f} s after the last send")
    with open(folder / "seen.jsonl", "w") as f:
        f.writelines(json.dumps(s) + "\n" for s in aws.seen())
    with open(folder / "counts.jsonl", "w") as f:
        f.writelines(json.dumps(c) + "\n" for c in aws.rows())
    r = report(folder, args.speed)
    print(show(r))
    return 0 if r["counts_match_truth"] and r["counted"] == r["requests"] else 1


if __name__ == "__main__":
    sys.exit(main())
