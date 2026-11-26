# Studio demo: the rides example, file by file

About one minute a step. Steps 1 to 8 are Checkpoint 1: **text that a team writes by Tuesday**, and the two checks
of that text (tag `cp1`; output pasted from runs on 2026-11-20). Steps 9 to 16 are Checkpoint 2: **the same text,
running**, with JS01's counting path deployed on AWS (tag `cp2`; output pasted from runs on 2026-11-26).

Before the studio: `uv` installed; `uv sync` once in this folder.

## Checkpoint 1: what a team writes for Tuesday

Steps 1 to 8 show the files at tag `cp1` (`git checkout cp1`; `git checkout cp2` comes back): the README, the
docs and the feature files have changed since.

| # | Show | Say |
|---|---|---|
| 1 | `README.md`, the table | the upper rows are Tuesday's hand-in, the lower rows are Checkpoint 2 |
| 2 | `docs/requirements.md`, JS01 | a story is a heading; under it lines R010 … in five forms: WHEN (R010), IF … THEN (R020), no keyword (R030), WHILE (R090 under JS03), WHERE with WHEN (R110 under JS04). An ID is defined once in the file; a number after `|` is the requirement's target; `[Scenario]` at the end of a line links the feature file that has its rule |
| 3 | `docs/requirements.md`, Stakeholder input | the feedback IDs with their wording, then `Reply [R080]:` and how the team addresses it, with the R lines that meet it in brackets (`Reply:` when no R line meets it); the line ends with `[Scenario]` and the feature file (RF010 to RF040) or with `Read at Checkpoint 2:` and what staff will read then (RF050, RQ010, RQ020); RQ010 and RQ020 each have a `Reply:` that says what the team will do and what it is based on (`We will calculate … based on …`, `We will write the test …`); then the Evals entry for R110: cases, what counts as correct, runs, the count that passes, the model in use |
| 4 | `docs/design.md`, Data, Our data | four sentences: DS01 and DS02, the subset with its rows and size, and what the events are built from. Run the count below |
| 5 | `docs/design.md`, Data, Simulated data for the demos | SIM01 to SIM05, one bullet each in words: the IDs it shows in brackets after its name, then what it holds and its injected faults with exact counts |
| 6 | `docs/design.md`, Data, Event format | one line for each kind of event; the fields are the columns of an example's table. Field types and valid values come at Checkpoint 2 |
| 7 | `features/js01_trips_per_zone.feature`, rule `@RF010` | story tag on the feature, ID tag on the rule; one example with a 3-row table, one with `Given the simulated data set SIM01 "rush-hour"`. Then `trip_assignment.feature`: two story tags, a rule with two ID tags (`@R080 @RF030`). Then the `@eval` gate in `js04_pickup_place.feature` |
| 8 | the two checks below | the traceability table, then the dry run on the Tuesday state |

Step 4, one number of Our data checked (reads the file's footer over HTTPS):

```
$ echo "SELECT count(*) AS trips FROM 'https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-03.parquet';" | uvx --from duckdb-cli duckdb
| trips:BIGINT |
|---|
| 21280788 |
```

Step 8, traceability:

```
$ python3 tools/check_trace.py
ID     Defined                Used
JS01   requirements.md:5      js01_trips_per_zone.feature:2, js01_yesterdays_trips.feature:2
R010   requirements.md:12     js01_trips_per_zone.feature:10, design.md (4 lines)
R020   requirements.md:13     js01_trips_per_zone.feature:23, design.md (4 lines)
R030   requirements.md:14     js01_trips_per_zone.feature:48, design.md (4 lines)
R040   requirements.md:15     js01_yesterdays_trips.feature:9, design.md (6 lines)
R050   requirements.md:16     js01_yesterdays_trips.feature:17, design.md (6 lines)
JS02   requirements.md:18     trip_assignment.feature:2
R070   requirements.md:23     trip_assignment.feature:9, design.md (5 lines)
R080   requirements.md:24     trip_assignment.feature:21, design.md (5 lines)
JS03   requirements.md:26     trip_assignment.feature:2
R090   requirements.md:30     trip_assignment.feature:56, design.md (6 lines)
R100   requirements.md:31     trip_assignment.feature:69, design.md (6 lines)
JS04   requirements.md:33     js04_pickup_place.feature:2
R110   requirements.md:39     js04_pickup_place.feature:11, design.md (4 lines)
R120   requirements.md:40     js04_pickup_place.feature:30, design.md (4 lines)
RF010  requirements.md:46     js01_trips_per_zone.feature:58, design.md (5 lines)
RF020  requirements.md:47     js01_trips_per_zone.feature:79, design.md (6 lines)
RF030  requirements.md:48     trip_assignment.feature:21, design.md (4 lines)
RF040  requirements.md:49     js01_trips_per_zone.feature:100, design.md (7 lines)
RF050  requirements.md:50     design.md (19 lines)
RQ010  requirements.md:51     read, not run
RQ020  requirements.md:52     read, not run
DS01   design.md:100          requirements.md:7, requirements.md:51, requirements.md:71, SIM01, SIM02, SIM03, SIM04, SIM05
DS02   design.md:104          not used
SIM01  design.md:111          js01_trips_per_zone.feature:70, requirements.md:52
SIM02  design.md:114          js01_trips_per_zone.feature:93
SIM03  design.md:116          trip_assignment.feature:48
SIM04  design.md:119          js01_yesterdays_trips.feature:12
SIM05  design.md:122          js01_trips_per_zone.feature:104

29 IDs, 0 problems
$ echo $?
0
```

RF050, RQ010 and RQ020 are read, not run, so they do not have a rule. To see a problem, change
`SIM02` to `SIM09` in the feature file and run it again:
`PROBLEM js01_trips_per_zone.feature:93: SIM09 is not defined in docs/design.md, section Data`, exit code 1.

Step 8, the dry run on what a team hands in (tag `cp1`: step code only for the pickup-place feature, `features/steps/pickup_steps.py`, as a demonstration):

```
$ git checkout -q cp1
$ uvx behave@1.3.3 --dry-run --no-snippets        # last lines
0 features passed, 0 failed, 3 error, 0 skipped, 1 untested
0 rules passed, 0 failed, 12 error, 0 skipped, 2 untested
0 scenarios passed, 0 failed, 18 error, 0 skipped, 4 untested
0 steps passed, 0 failed, 0 skipped, 73 undefined, 11 untested
$ grep -c "^ *Example:" features/*.feature        # 22 in all
features/js01_yesterdays_trips.feature:2
features/js01_trips_per_zone.feature:10
features/js04_pickup_place.feature:4
features/trip_assignment.feature:6
$ git checkout -q main
```

"error" and "undefined" are what a team's Tuesday looks like: every feature was read, and its steps do not have code yet. In this example the steps of the pickup-place feature do have code (`features/steps/pickup_steps.py`, a demonstration), so its 4
examples are "untested" (the dry run does not run R120's example, whose `Then` does not have code). The count of
scenarios (18 error and 4 untested, 22) equals the number of `Example:` lines.

## Checkpoint 2: the same text, running

Tag `cp2`. Every rule has step code and every example runs; JS01's counting path ran on AWS on 2026-11-26 (account
of the course staff, ca-central-1, the team prefix `t00`) and was deleted after the run. The numbers on the circled
steps are those of the Checkpoint 2 page.

| # | Show | Say |
|---|---|---|
| 9 | ① `docs/design.md`, Simulated data for the demos, beside `sim/datasets.py` and `sim/expected.toml`; run the generator, then `sim/check.py` | each bullet became settings, and each number of the bullet a query on the files; the checker fails when a number in the bullet and the files differ. `sim/data/SIM01/` is what the system receives, `_truth/` beside it the events as they happened and the faults. SIM05 (42,797 files) is written on demand and not committed |
| 10 | ② `uvx behave@1.3.3`, then the two tag runs | every example runs on the local code, with behave alone (no AWS, no Pydantic). One example is tagged `@todo`: RF040's, whose lake is not deployed; it runs on the local stand-in |
| 11 | ② `@RF010` with `DEDUPE=off`, after a prediction | as at Checkpoint 1: the example knew its answer before the system ran |
| 12 | ③ `docs/design.md`, Resources; `scripts/stream.py up`, `scripts/counting.py up`; the first batch | the first six rows are deployed, each from a script that is safe to run again, with the course tags; the first batch of 4 records (one twice) took 28 s, observed once, after the deploy; a second run of both scripts keeps or updates each resource |
| 13 | ③ the JS01 counting examples against the deployed slice | the same examples, `TARGET=aws`: the `Given` rows go to the Kinesis stream, the function counts them in DynamoDB, the `Then` reads the table |
| 14 | ④ `docs/requirements.md`, RQ010 and RQ020; `docs/design.md`, Cost and Experiments; the replay test | RQ020: R010's data latency stays about 1 s at p95 at 1, 10 and 50 times SIM01's speed: the function reads the shard about once a second, whatever the rate. RQ010: one year in CAD, from DS01's volume and the units the run measured |
| 15 | ⑤ `docs/reviews/well-architected.md` | four questions of the Data Analytics Lens; questions 1 and 2 changed the design (a transaction and batch item failures; a provisioned shard), and `docs/design.md` shows both |
| 16 | ⑥ the checks, the decisions, the teardown | `check_trace.py` lists the two decisions; `teardown.sh --yes` deletes the stream first, then asks each service again |

Step 9:

```
$ uv run python -m sim.generate
SIM01 rush-hour: 2511 events, 2515 deliveries in 3 files, 6 fault records (duplicate, late), 5026 lines valid -> sim/data/SIM01/
SIM02 quiet-zone: 2331 events, 2331 deliveries in 3 files, 1 fault records (quiet), 4662 lines valid -> sim/data/SIM02/
SIM03 double-accept: 60 events, 60 deliveries in 1 file, 10 fault records (later-first), 120 lines valid -> sim/data/SIM03/
SIM04 trips-day: 19074 events, 19077 deliveries in 1 file, 3 fault records (bad-fare), 38151 lines valid -> sim/data/SIM04/
$ uv run python sim/check.py SIM01
SIM01: sim/data/SIM01/ (models: trip_accepted, trip_completed, trip_requested, ExportRow)
ok   JSON: every line is one JSON object
ok   folders: 1 source (trip-events), 3 files, every line in the folder of its received_time
ok   validate: 2515 delivery lines and 2511 truth events match their models
ok   truth: each of 2511 event_ids once, every delivery is in it
ok   bullet: 6 numbers of the bullet, each given by the files
ok   duplicate: 4 records, each event delivered once more
ok   never: none
ok   received after event: every delivery has received_time >= event_time
ok   late: 2 events first delivered 391 s to 405 s after event_time; every other event within 1 s
ok   changed: none: every delivery equals its truth event
ok   quiet: none
ok   later-first: none
ok   bad-fare: none
ok   lines: 2515 = 2511 truth - 0 never + 4 duplicate
--   other fault kinds, not checked here: none
OK: SIM01 matches its bullet and the simulation standards (0 problems)
digest 0f2e3a9c5894127e
$ uv run python sim/check.py                       # every data set: the last two lines of each
OK: SIM01 matches its bullet and the simulation standards (0 problems)
digest 0f2e3a9c5894127e
OK: SIM02 matches its bullet and the simulation standards (0 problems)
digest c643744177fdae18
OK: SIM03 matches its bullet and the simulation standards (0 problems)
digest f1d42a916abdcee2
OK: SIM04 matches its bullet and the simulation standards (0 problems)
digest e07316a76c4bc103
OK: SIM05 matches its bullet and the simulation standards (0 problems)
digest fbe867552c4a5020
```

The number 191 changed to 192 in SIM01's bullet (a copy of `docs/design.md`), then put back:

```
$ uv run python sim/check.py SIM01 --design /tmp/design-planted.md      # from the problem on
PROBLEM bullet: 1
  expected.toml: "304, 191 and 342 trips" is not in the bullet of SIM01
FAILED: SIM01 has 1 problems
```

Step 10 (last lines of each; a fresh clone takes about 40 s the first time, to write SIM05):

```
$ uvx behave@1.3.3
4 features passed, 0 failed, 0 skipped
14 rules passed, 0 failed, 0 skipped
22 scenarios passed, 0 failed, 0 skipped
84 steps passed, 0 failed, 0 skipped
Took 0min 0.000s
$ uvx behave@1.3.3 --tags="not @todo"
4 features passed, 0 failed, 0 skipped
13 rules passed, 0 failed, 1 skipped
21 scenarios passed, 0 failed, 1 skipped
77 steps passed, 0 failed, 7 skipped
Took 0min 0.000s
$ uvx behave@1.3.3 --tags=@todo
1 feature passed, 0 failed, 3 skipped
1 rule passed, 0 failed, 13 skipped
1 scenario passed, 0 failed, 21 skipped
7 steps passed, 0 failed, 77 skipped
Took 0min 0.000s
$ uvx behave@1.3.3 --dry-run --tags="not @todo"; echo $?
0 features passed, 0 failed, 0 skipped, 4 untested
0 rules passed, 0 failed, 1 skipped, 13 untested
0 scenarios passed, 0 failed, 1 skipped, 21 untested
0 steps passed, 0 failed, 7 skipped, 77 untested
Took 0min 0.000s
0
```

Step 11:

```
$ DEDUPE=off uvx behave@1.3.3 --tags=@RF010        # the two failures
      ASSERT FAILED: zone 161, between 09:10 and 09:15: expected 2 trips requested, the system counted 3 (DEDUPE=off: the duplicate check is off)
      ASSERT FAILED: zone 48, between 09:00 and 10:00: expected 304 trips requested, the system counted 307 (DEDUPE=off: the duplicate check is off)
```

Step 12 (`evidence/deploy.txt`, `evidence/first-batch.txt`, `evidence/rerun-up.txt`, `evidence/teardown-dry-run.txt`):

```
$ uv run python scripts/stream.py up && uv run python scripts/counting.py up
created stream t00-trip-events (1 shard, provisioned)
t00-trip-events ready
created table t00-zone-counts
created table t00-seen-events
created function t00-count-requests
created mapping t00-trip-events -> t00-count-requests
counting path ready
# the first batch, sent by a few lines of Python with src/rides/aws_slice.py: R010's 3 rows and one of them again
first batch: 4 records (one sent twice), all counted 28.3 s after the put
$ uv run python scripts/stream.py up && uv run python scripts/counting.py up       # again, on the deployed slice
stream t00-trip-events is there (ACTIVE): kept
t00-trip-events ready
table t00-zone-counts is there (ACTIVE): kept
table t00-seen-events is there (ACTIVE): kept
function t00-count-requests is there: code and settings updated
reserved concurrency 1 on t00-count-requests
mapping t00-trip-events -> t00-count-requests is there: settings updated
counting path ready
$ bash scripts/teardown.sh --dry-run               # with the slice deployed
would delete  Kinesis stream t00-trip-events (hourly)
would delete  event source mapping fd4c6e2f-7fb5-4bea-b6a8-1e093199fbf7 (t00-trip-events -> t00-count-requests)
would delete  Lambda function t00-count-requests
would delete  DynamoDB table t00-zone-counts
would delete  DynamoDB table t00-seen-events
would delete  log group /aws/lambda/t00-count-requests
dry run: nothing deleted (bash scripts/teardown.sh --yes deletes)
```

Step 13:

```
$ TARGET=aws uv run behave features/js01_trips_per_zone.feature --tags="not @todo"     # last lines
1 feature passed, 0 failed, 0 skipped
5 rules passed, 0 failed, 1 skipped
9 scenarios passed, 0 failed, 1 skipped
32 steps passed, 0 failed, 7 skipped
Took 0min 0.000s
exit 0
```

Step 14, the replay test (each run empties the tables, replays SIM01's deliveries received up to 10:11, waits until
every request is counted, and compares the counts with the truth):

```
$ uv run python sim/replay_test.py --speed 50
replayed 2332 deliveries (0 failed) in 85 s
every request counted 0.2 s after the last send
replay rq020-x50: 2332 deliveries in 1774 PutRecords calls, 85 s at 50 times SIM01's speed; 837 of 837 requests counted
R010 data latency, zone and period (36): median 0.60 s, p95 0.70 s, max 0.70 s (36)
R020 data latency, late requests: median 0.52 s, p95 1.04 s, max 1.04 s (2)
each request, sent to counted: median 0.70 s, p95 1.00 s, max 1.10 s (837)
  sent to in the stream: median 0.01 s, p95 0.01 s, max 0.04 s (837)
  in the stream to counted: median 0.70 s, p95 1.00 s, max 1.10 s (837)
trips 09:00 to 10:00, zones 48, 161, 230: 304, 191, 342 (truth 304, 191, 342): match
$ uv run python sim/replay_test.py --speed 10
replayed 2332 deliveries (0 failed) in 423 s
every request counted 0.2 s after the last send
replay rq020-x10: 2332 deliveries in 1774 PutRecords calls, 423 s at 10 times SIM01's speed; 837 of 837 requests counted
R010 data latency, zone and period (36): median 0.00 s, p95 0.98 s, max 1.01 s (36)
R020 data latency, late requests: median 0.39 s, p95 0.55 s, max 0.55 s (2)
each request, sent to counted: median 0.66 s, p95 1.09 s, max 1.94 s (837)
  sent to in the stream: median 0.01 s, p95 0.01 s, max 0.04 s (837)
  in the stream to counted: median 0.66 s, p95 1.09 s, max 1.90 s (837)
trips 09:00 to 10:00, zones 48, 161, 230: 304, 191, 342 (truth 304, 191, 342): match
$ uv run python sim/replay_test.py --speed 1
replayed 2332 deliveries (0 failed) in 4225 s
every request counted 0.2 s after the last send
replay rq020-x1: 2332 deliveries in 1774 PutRecords calls, 4225 s at 1 times SIM01's speed; 837 of 837 requests counted
R010 data latency, zone and period (36): median 0.00 s, p95 0.91 s, max 1.94 s (36)
R020 data latency, late requests: median 0.85 s, p95 1.05 s, max 1.05 s (2)
each request, sent to counted: median 0.94 s, p95 1.96 s, max 2.04 s (837)
  sent to in the stream: median 0.01 s, p95 0.01 s, max 0.04 s (837)
  in the stream to counted: median 0.94 s, p95 1.95 s, max 2.03 s (837)
trips 09:00 to 10:00, zones 48, 161, 230: 304, 191, 342 (truth 304, 191, 342): match
```

Then the units of the run and the year (`docs/design.md`, Cost):

```
$ uv run python scripts/run_units.py --start 2026-11-26T05:49:00Z --end 2026-11-26T07:14:18Z --stream-hours 1.6   # before the teardown
$ uv run python scripts/run_units.py --recost --stream-hours 1.45     # after both teardowns (last lines)
Kinesis shard-hours            0.023925 USD
Kinesis PUT payload units      0.000177 USD
Lambda requests                0.000423 USD
Lambda duration (arm64)        0.000225 USD
DynamoDB write units           0.013857 USD
DynamoDB read units            0.003097 USD
CloudWatch Logs ingestion      0.000517 USD
total                            0.0422 USD = 0.0612 CAD
$ uv run python scripts/year_cost.py               # the last three lines
counting path: 361.22 USD = 523.77 CAD a year
rest of the design: 354.57 USD = 514.13 CAD a year
whole design: 715.80 USD = 1,037.91 CAD a year
```

Step 16:

```
$ python3 tools/check_trace.py                     # the decisions, then the last line
DECISION requirements.md:50 (under RF040 (requirements.md:49)) budget-check BC020, t00-compact-events PR #4: later, fi ...
DECISION requirements.md:76 (under ## Decisions) budget-check BC010, t00-trip-events PR #3: keep. The stream is the on ...
29 IDs, 0 problems, 2 decisions
$ uv run pytest -q
72 passed in 24.69s
$ bash scripts/teardown.sh --yes
deleted       Kinesis stream t00-trip-events (hourly)
deleted       event source mapping fd4c6e2f-7fb5-4bea-b6a8-1e093199fbf7 (t00-trip-events -> t00-count-requests)
deleted       Lambda function t00-count-requests
deleted       DynamoDB table t00-zone-counts
deleted       DynamoDB table t00-seen-events
deleted       log group /aws/lambda/t00-count-requests
nothing left with the prefix t00- (Kinesis streams, Lambda functions and mappings, DynamoDB tables, log groups)
exit 0
```

Step 6.4 of the page, deploy again, check the slice works, clean up again (`evidence/redeploy.txt`, the main lines):

```
$ uv run python scripts/stream.py up && uv run python scripts/counting.py up
created stream t00-trip-events (1 shard, provisioned)
counting path ready
$ TARGET=aws uv run behave features/js01_trips_per_zone.feature --tags="not @todo" --name "One request delivered twice"    # 2026-11-26T07:15:41Z
1 scenario passed, 0 failed, 9 skipped
$ bash scripts/teardown.sh --yes    # 2026-11-26T07:16:55Z
deleted       Kinesis stream t00-trip-events (hourly)
nothing left with the prefix t00- (Kinesis streams, Lambda functions and mappings, DynamoDB tables, log groups)
exit 0
```

Then each service asked once more, by itself (`evidence/teardown-proof.txt`):

```
# each service asked for the slice's resources, by itself, after the last teardown (2026-11-26T07:17:17Z)
$ aws kinesis list-streams --query "StreamNames[?starts_with(@, 't00-')]"
[]
$ aws kinesis describe-stream-summary --stream-name t00-trip-events

aws: [ERROR]: An error occurred (ResourceNotFoundException) when calling the DescribeStreamSummary operation: Stream t00-trip-events under account <account> not found.
$ aws lambda list-functions --query "Functions[?starts_with(FunctionName, 't00-')].FunctionName"
[]
$ aws lambda list-event-source-mappings --query "EventSourceMappings[?contains(FunctionArn, ':function:t00-')].UUID"
[]
$ aws lambda get-function --function-name t00-count-requests

aws: [ERROR]: An error occurred (ResourceNotFoundException) when calling the GetFunction operation: Function not found: arn:aws:lambda:ca-central-1:<account>:function:t00-count-requests

Additional error details:
Type: User
$ aws dynamodb list-tables --query "TableNames[?starts_with(@, 't00-')]"
[]
$ aws dynamodb describe-table --table-name t00-zone-counts

aws: [ERROR]: An error occurred (ResourceNotFoundException) when calling the DescribeTable operation: Requested resource not found: Table: t00-zone-counts not found
$ aws dynamodb describe-table --table-name t00-seen-events

aws: [ERROR]: An error occurred (ResourceNotFoundException) when calling the DescribeTable operation: Requested resource not found: Table: t00-seen-events not found
$ aws logs describe-log-groups --log-group-name-prefix /aws/lambda/t00-
[]
```

### The files of evidence/

| File | What it is |
|---|---|
| `deploy.txt` | the first deploy: `scripts/stream.py up`, `scripts/counting.py up` and the status of each resource, from an earlier commit of the scripts (they set the reserved concurrency without a line of output, and the status line printed the stream's creation time in local time with a `Z`; `scripts/stream.py` prints UTC since) |
| `deploy-tags.txt` | the tags AWS returned for each resource of the slice, the function's reserved concurrency and the mapping's settings (RF050) |
| `first-batch.txt` | the first batch on AWS: 4 records, one of them twice, before any replay |
| `rerun-up.txt` | both `up` scripts run again on the deployed slice: each resource kept or updated, nothing made twice |
| `aws-examples.txt` | the JS01 counting examples run against the deployed slice (`TARGET=aws`, `--tags="not @todo"`) |
| `rq020-x1.txt`, `rq020-x10.txt`, `rq020-x50.txt` | what `sim/replay_test.py` printed at each speed |
| `rq020-x<speed>/command.txt`, `sent.jsonl`, `summary.json` | the replayer's record of the run: the command and commit, each delivery with the time it was sent, the summary |
| `rq020-x<speed>/seen.jsonl`, `counts.jsonl` | the two tables after the run: each request with the time it entered the stream and was counted, each stored count |
| `rq020-x<speed>/report.json` | R010's and R020's data latency and the counts against SIM01's truth (RQ020) |
| `units.txt`, `units.json` | the measured units of the run from CloudWatch (records, function runs and billed time, write and read units, log bytes) and their cost |
| `units-recost.txt` | the cost again with the stream's two lifetimes, after both teardowns (`docs/design.md`, Cost) |
| `teardown-dry-run.txt` | `scripts/teardown.sh --dry-run` with the slice deployed: what it would delete |
| `teardown.txt` | `scripts/teardown.sh --yes` after the run, and its last check of each service |
| `redeploy.txt` | step 6.4 of the page: deploy again, one example on AWS, `teardown.sh --yes` again |
| `teardown-proof.txt` | each service's own list and describe calls after the last teardown: nothing named `t00-` is left |

### Pull request numbers

The numbers in the decision lines and the changed lines of `docs/` are the pull requests of this repository, one for
each change that belongs together, merged in this order:

| PR | What it holds | Where `docs/` names it |
|---|---|---|
| [#1](https://github.com/cpsc436c-2026w1/cp1-example/pull/1) | `tools/`: the traceability check at its Checkpoint 2 version (decision lines, Stakeholder input tables, a Rule needs an Example) and the seed query of SIM04 and SIM05 | not named |
| [#2](https://github.com/cpsc436c-2026w1/cp1-example/pull/2) | the base: the generator and the data of SIM01, SIM02 and SIM03, the step code, the local code in `src/rides/`, the dependencies | not named |
| [#3](https://github.com/cpsc436c-2026w1/cp1-example/pull/3) | the slice: `scripts/` (stream, counting, teardown, tags), the deployed function, the examples' AWS target, Resources, RF050 | `docs/design.md`, Resources; `docs/requirements.md`, RF050 and the BC010 decision |
| [#4](https://github.com/cpsc436c-2026w1/cp1-example/pull/4) | RF040's example tagged `@todo`, the compaction job left for the final hand-in | `docs/requirements.md`, the BC020 decision under RF040 |
| [#5](https://github.com/cpsc436c-2026w1/cp1-example/pull/5) | the simulated data: SIM04 and SIM05, `sim/check.py` and `sim/expected.toml`, the event models | `docs/design.md`, the SIM05 bullet and the event format |
| [#6](https://github.com/cpsc436c-2026w1/cp1-example/pull/6) | the Well-Architected review and its two changes in the design: the transaction and batch item failures, the provisioned shard | `docs/design.md`, Counting requests and the stream's row; `docs/reviews/well-architected.md` |
| [#7](https://github.com/cpsc436c-2026w1/cp1-example/pull/7) | the answers of RQ010 and RQ020: Cost, Experiments, the replay test, the units and the run's evidence in `evidence/` | `docs/requirements.md`, RQ010 and RQ020; `docs/design.md`, Cost and Experiments |
| [#8](https://github.com/cpsc436c-2026w1/cp1-example/pull/8) | the budget and sandbox check report, this page, the README, the eval's README and the tests of the traceability check | not named |

## What stays a draft

The parts of the design that are not deployed: the trips table and the functions of JS02 and JS03, the API and the
read function, the lake (Firehose, bucket, Glue jobs and tables, Athena) and the assistant. Their rules run on local
code (`src/rides/assign.py`, `curate.py`, `compact.py`, `assistant.py`); RF040's example is tagged `@todo`; R110's
eval runs on recorded replies, written by hand, not a model run. They come for the final hand-in.
