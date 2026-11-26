"""The counting path of JS01 on AWS (R010, R020, R030, RF010, RF020, RF050): two tables, the function and its mapping.

    uv run python scripts/counting.py up        # tables, log group, function, event source mapping (stream first:
                                                #   scripts/stream.py up)
    uv run python scripts/counting.py status    # what is there
    uv run python scripts/counting.py clear     # empty both tables between runs (the examples and the replay test)
    uv run python scripts/counting.py down      # delete what `up` made (scripts/teardown.sh runs the same deletes)

What `up` creates, each with the course tags (scripts/common.py):

    DynamoDB table t00-zone-counts     key zone_id (number), period_start (text); attribute trips; on demand
    DynamoDB table t00-seen-events     key event_id; expires 24 hours after the record entered the stream (Q030)
    log group /aws/lambda/t00-count-requests, kept 7 days, made before the function
    Lambda function t00-count-requests  src/rides/counting.py and count_function.py; Python 3.12, arm64, 128 MB,
                                        30 s; at most 1 run at a time (reserved concurrency 1; the lease allows 10)
    event source mapping t00-trip-events -> t00-count-requests

The function's role is t00-count-requests-fn (LAMBDA_ROLE_ARN to use another): it may read this stream, write
these two tables and its own log group, nothing else. In a team's lease the role is made the same way by the
team; here the course staff made it, so no script here creates an IAM role.

From the course recipe streaming-ingestion (main/infra.py): create_table, create_log_group, create_function and
kinesis_mapping, with the names and keys of the rides case. The mapping has no failure destination: a record that
still fails after 3 retries is given up and its sequence number is in the log (docs/reviews/well-architected.md, question 1).
"""
import io
import os
import sys
import time
import zipfile

from common import ROOT, names, session, tags, usage

LOG_DAYS = 7


def create_table(ddb, name: str, keys: list[tuple[str, str, str]]) -> None:
    """On demand: no charge while idle except storage. A table that is still being deleted is waited out."""
    for _ in range(2):
        try:
            ddb.create_table(TableName=name, BillingMode="PAY_PER_REQUEST",
                             KeySchema=[{"AttributeName": k, "KeyType": role} for k, _, role in keys],
                             AttributeDefinitions=[{"AttributeName": k, "AttributeType": t} for k, t, _ in keys],
                             Tags=tags("dynamodb"))
            print(f"created table {name}")
            break
        except ddb.exceptions.ResourceInUseException:
            try:
                state = ddb.describe_table(TableName=name)["Table"]["TableStatus"]
            except ddb.exceptions.ResourceNotFoundException:
                continue
            if state != "DELETING":
                print(f"table {name} is there ({state}): kept")
                break
            ddb.get_waiter("table_not_exists").wait(TableName=name)
    ddb.get_waiter("table_exists").wait(TableName=name)


def package() -> bytes:
    """The deployment package: the rides package with the rule and the handler, nothing else."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ("__init__.py", "counting.py", "count_function.py"):
            info = zipfile.ZipInfo(f"rides/{f}", date_time=(2026, 1, 1, 0, 0, 0))   # same bytes on every run
            info.external_attr = 0o644 << 16
            z.writestr(info, (ROOT / "src" / "rides" / f).read_bytes(), zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def up(s) -> None:
    n = names()
    ddb, lam, logs, kinesis = s.client("dynamodb"), s.client("lambda"), s.client("logs"), s.client("kinesis")
    account = s.client("sts").get_caller_identity()["Account"]
    stream_arn = kinesis.describe_stream_summary(StreamName=n["stream"])["StreamDescriptionSummary"]["StreamARN"]
    create_table(ddb, n["counts"], [("zone_id", "N", "HASH"), ("period_start", "S", "RANGE")])
    create_table(ddb, n["seen"], [("event_id", "S", "HASH")])
    ttl = ddb.describe_time_to_live(TableName=n["seen"])["TimeToLiveDescription"]
    if ttl.get("TimeToLiveStatus") not in ("ENABLED", "ENABLING"):
        ddb.update_time_to_live(TableName=n["seen"], TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"})
    try:
        logs.create_log_group(logGroupName=n["log_group"], tags=tags("logs"))
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    logs.put_retention_policy(logGroupName=n["log_group"], retentionInDays=LOG_DAYS)
    role = os.environ.get("LAMBDA_ROLE_ARN") or f"arn:aws:iam::{account}:role/{n['role']}"
    env = {"Variables": {"COUNTS_TABLE": n["counts"], "SEEN_TABLE": n["seen"], "DEDUPE": "on"}}
    try:
        lam.create_function(FunctionName=n["function"], Runtime="python3.12", Architectures=["arm64"], Role=role,
                            Handler="rides.count_function.handler", Code={"ZipFile": package()}, Timeout=30,
                            MemorySize=128, Environment=env, Tags=tags("lambda"))
        print(f"created function {n['function']}")
    except lam.exceptions.ResourceConflictException:
        lam.get_waiter("function_updated_v2").wait(FunctionName=n["function"])
        lam.update_function_code(FunctionName=n["function"], ZipFile=package())
        lam.get_waiter("function_updated_v2").wait(FunctionName=n["function"])
        lam.update_function_configuration(FunctionName=n["function"], Environment=env, Role=role)
        print(f"function {n['function']} is there: code and settings updated")
    lam.get_waiter("function_active_v2").wait(FunctionName=n["function"])
    reserve_one(lam, n["function"])
    settings = dict(BatchSize=100, MaximumBatchingWindowInSeconds=1, ParallelizationFactor=1,
                    FunctionResponseTypes=["ReportBatchItemFailures"], BisectBatchOnFunctionError=True,
                    MaximumRetryAttempts=3, MaximumRecordAgeInSeconds=3600)
    found = [m for m in lam.list_event_source_mappings(FunctionName=n["function"], EventSourceArn=stream_arn)[
        "EventSourceMappings"] if m["State"] != "Deleting"]
    if found:
        uuid = found[0]["UUID"]
        wait_mapping(lam, uuid, ("Enabled", "Disabled"))
        lam.update_event_source_mapping(UUID=uuid, FunctionName=n["function"], **settings)
        print(f"mapping {n['stream']} -> {n['function']} is there: settings updated")
    else:
        uuid = lam.create_event_source_mapping(FunctionName=n["function"], EventSourceArn=stream_arn,
                                               StartingPosition="TRIM_HORIZON", Tags=tags("lambda"), **settings)["UUID"]
        print(f"created mapping {n['stream']} -> {n['function']}")
    wait_mapping(lam, uuid, ("Enabled",))
    print("counting path ready")


def reserve_one(lam, function: str) -> None:
    """At most one run at a time, when the account can spare it: Lambda keeps 100 units unreserved (Lambda API
    Reference, PutFunctionConcurrency), so an account with a total of 10 cannot reserve any. From the course recipe
    limits-and-alarms (main/limits.py, ensure_concurrency). Without it, one shard and a parallelization factor of 1
    still mean one run at a time for this function."""
    current = lam.get_function_concurrency(FunctionName=function).get("ReservedConcurrentExecutions", 0)
    unreserved = lam.get_account_settings()["AccountLimit"]["UnreservedConcurrentExecutions"] + current
    if unreserved - 1 < 100:
        print(f"reserved concurrency not set: {unreserved} unreserved in the account, Lambda keeps 100")
        return
    lam.put_function_concurrency(FunctionName=function, ReservedConcurrentExecutions=1)
    print(f"reserved concurrency 1 on {function}")


def wait_mapping(lam, uuid: str, states: tuple, timeout_s: int = 240) -> None:
    end = time.time() + timeout_s
    while time.time() < end:
        if lam.get_event_source_mapping(UUID=uuid)["State"] in states:
            return
        time.sleep(3)
    raise TimeoutError(f"mapping {uuid} not {' or '.join(states)} after {timeout_s} s")


def clear(s) -> None:
    """Delete every item of both tables: each example and each replay starts from empty tables."""
    ddb = s.client("dynamodb")
    for table, keys in ((names()["counts"], ("zone_id", "period_start")), (names()["seen"], ("event_id",))):
        deleted = 0
        for page in ddb.get_paginator("scan").paginate(TableName=table, ProjectionExpression=", ".join(keys)):
            items = page["Items"]
            for i in range(0, len(items), 25):
                batch = [{"DeleteRequest": {"Key": item}} for item in items[i:i + 25]]
                while batch:
                    left = ddb.batch_write_item(RequestItems={table: batch}).get("UnprocessedItems", {})
                    batch = left.get(table, [])
            deleted += len(items)
        print(f"{table}: {deleted} items deleted")


def status(s) -> None:
    n = names()
    ddb, lam, logs = s.client("dynamodb"), s.client("lambda"), s.client("logs")
    for table in (n["counts"], n["seen"]):
        try:
            t = ddb.describe_table(TableName=table)["Table"]
            print(f"table {table}: {t['TableStatus']}, {t.get('ItemCount', 0)} items (updated every 6 hours)")
        except ddb.exceptions.ResourceNotFoundException:
            print(f"table {table}: absent")
    try:
        f = lam.get_function(FunctionName=n["function"])["Configuration"]
        print(f"function {n['function']}: {f['State']}, {f['Runtime']}, {f['Architectures'][0]}, {f['MemorySize']} MB")
        for m in lam.list_event_source_mappings(FunctionName=n["function"])["EventSourceMappings"]:
            print(f"mapping {m['UUID']}: {m['State']}, batch {m['BatchSize']}, last result {m.get('LastProcessingResult')}")
    except lam.exceptions.ResourceNotFoundException:
        print(f"function {n['function']}: absent")
    found = logs.describe_log_groups(logGroupNamePrefix=n["log_group"])["logGroups"]
    print(f"log group {n['log_group']}: " + (f"{found[0].get('storedBytes', 0)} bytes, kept "
                                               f"{found[0].get('retentionInDays')} days" if found else "absent"))


def down(s) -> None:
    n = names()
    ddb, lam, logs = s.client("dynamodb"), s.client("lambda"), s.client("logs")
    try:
        for m in lam.list_event_source_mappings(FunctionName=n["function"])["EventSourceMappings"]:
            lam.delete_event_source_mapping(UUID=m["UUID"])
            print(f"deleted mapping {m['UUID']}")
        lam.delete_function(FunctionName=n["function"])
        print(f"deleted function {n['function']}")
    except lam.exceptions.ResourceNotFoundException:
        print(f"function {n['function']}: absent")
    for table in (n["counts"], n["seen"]):
        try:
            ddb.delete_table(TableName=table)
            ddb.get_waiter("table_not_exists").wait(TableName=table)
            print(f"deleted table {table}")
        except ddb.exceptions.ResourceNotFoundException:
            print(f"table {table}: absent")
    try:
        logs.delete_log_group(logGroupName=n["log_group"])
        print(f"deleted log group {n['log_group']}")
    except logs.exceptions.ResourceNotFoundException:
        print(f"log group {n['log_group']}: absent")


if __name__ == "__main__":
    command = usage(__doc__, sys.argv, ("up", "down", "status", "clear"))
    {"up": up, "down": down, "status": status, "clear": clear}[command](session())
