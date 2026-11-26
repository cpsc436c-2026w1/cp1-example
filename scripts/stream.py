"""The Kinesis data stream t00-trip-events (R010, R020, RF010, RF050): the trips service sends each trip event to it.

    uv run python scripts/stream.py up        # create it (1 shard, provisioned), or keep the one that is there
    uv run python scripts/stream.py status    # what is there
    uv run python scripts/stream.py down      # delete it (scripts/teardown.sh does this first: it bills by the hour)

Provisioned with 1 shard, not on demand (docs/reviews/well-architected.md, question 2): one shard takes 1,000 records a second, and the
replay at 50 times SIM01's speed sends about 27 a second; a shard costs 0.0165 USD an hour against 0.048 for an
on-demand stream (price sheet, ca-central-1, 2026-11-18). From the course recipe streaming-ingestion
(main/infra.py, create_stream): a stream with this name that is still being deleted is waited out, then created.
"""
import sys
from datetime import timezone

from common import names, session, tags, usage


def up(kinesis) -> str:
    name = names()["stream"]
    for _ in range(2):
        try:
            kinesis.create_stream(StreamName=name, ShardCount=1, StreamModeDetails={"StreamMode": "PROVISIONED"})
            print(f"created stream {name} (1 shard, provisioned)")
            break
        except kinesis.exceptions.ResourceInUseException:
            try:
                status = kinesis.describe_stream_summary(StreamName=name)["StreamDescriptionSummary"]["StreamStatus"]
            except kinesis.exceptions.ResourceNotFoundException:
                continue                        # the deletion finished between the two calls: create it now
            if status != "DELETING":
                print(f"stream {name} is there ({status}): kept")
                break
            kinesis.get_waiter("stream_not_exists").wait(StreamName=name, WaiterConfig={"Delay": 3, "MaxAttempts": 60})
    kinesis.get_waiter("stream_exists").wait(StreamName=name, WaiterConfig={"Delay": 2, "MaxAttempts": 60})
    kinesis.add_tags_to_stream(StreamName=name, Tags=tags("kinesis"))
    return kinesis.describe_stream_summary(StreamName=name)["StreamDescriptionSummary"]["StreamARN"]


def status(kinesis) -> str:
    try:
        s = kinesis.describe_stream_summary(StreamName=names()["stream"])["StreamDescriptionSummary"]
    except kinesis.exceptions.ResourceNotFoundException:
        return f"stream {names()['stream']}: absent"
    return (f"stream {s['StreamName']}: {s['StreamStatus']}, {s['StreamModeDetails']['StreamMode'].lower()}, "
            f"{s['OpenShardCount']} shard, created {s['StreamCreationTimestamp'].astimezone(timezone.utc):%Y-%m-%dT%H:%M:%SZ}")


def down(kinesis) -> None:
    try:
        kinesis.delete_stream(StreamName=names()["stream"], EnforceConsumerDeletion=True)
    except kinesis.exceptions.ResourceNotFoundException:
        print(f"stream {names()['stream']}: absent")
        return
    kinesis.get_waiter("stream_not_exists").wait(StreamName=names()["stream"], WaiterConfig={"Delay": 3, "MaxAttempts": 60})
    print(f"deleted stream {names()['stream']}")


if __name__ == "__main__":
    command = usage(__doc__, sys.argv)
    k = session().client("kinesis")
    if command == "up":
        print(up(k).split(":stream/")[-1], "ready")
    elif command == "down":
        down(k)
    else:
        print(status(k))
