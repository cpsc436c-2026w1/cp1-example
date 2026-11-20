# Studio demo: the rides example, file by file

About one minute a step. Steps 1 to 8 are Checkpoint 1: **text that a team writes by Tuesday**, and the two checks
of that text. Steps 9 to 13 show **where Checkpoint 2 goes**: the same text made to run. Nothing calls AWS.
All output below is pasted from runs in this repository on 2026-11-20.

Before the studio: `uv` installed; `uv sync` once in this folder.

## Checkpoint 1: what a team writes for Tuesday

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

| # | Show | Say |
|---|---|---|
| 9 | `sim/datasets.py` beside Data, Simulated data for the demos; run the generator | the bullets became settings; the id is the folder name; the folders are those of `raw/trip-events/` |
| 10 | run `@RF010`; ask for a prediction; run it with `DEDUPE=off` | the example knew its answer before the system ran; with the check off the count is 3, not 2, and the simulated hour with its 4 duplicates fails too: zone 48 counts 307, not 304, because 3 of the 4 are in zone 48 |
| 11 | run `@RF020` and `@RF030` | a zone without events is `no data`; two accepts, each sent before the other has an answer: the conditional write gives the trip to one driver and refuses the other; an accept of a trip that is already assigned is refused and the trip keeps its driver |
| 12 | run `features/js04_pickup_place.feature`; then `check.py` alone | the gate reads the eval's counts from its steps: 10 cases, 3 runs each, at least 24 of 30 correct. Checker only, recorded replies: the replies are examples written by hand, so a pass shows that the checker and the gate work, not that the model meets R110; that waits for a live run through the course LLM gateway, which is not written yet. R120's example is undefined: it is a draft |
| 13 | `uv run pytest -q` | the generator's seed, the local code (with the two accepts without the condition: both drivers are told assigned), the checker with a planted error for each rule, the eval's checker |

Step 9:

```
$ uv run python -m sim.generate
SIM01 rush-hour: 2511 events, 2515 deliveries, 6 fault records (duplicate, late) -> sim/data/SIM01/
SIM02 quiet-zone: 2331 events, 2331 deliveries, 1 fault records (quiet) -> sim/data/SIM02/
SIM03 double-accept: 60 events, 60 deliveries, 10 fault records (later-first) -> sim/data/SIM03/
$ find sim/data/SIM01 -name "*.jsonl" | sort
sim/data/SIM01/_truth/events.jsonl
sim/data/SIM01/_truth/faults.jsonl
sim/data/SIM01/trip-events/dt=2026-11-23/hour=09/deliveries.jsonl
sim/data/SIM01/trip-events/dt=2026-11-23/hour=10/deliveries.jsonl
sim/data/SIM01/trip-events/dt=2026-11-23/hour=11/deliveries.jsonl
```

Step 10:

```
$ uv run behave --tags=@RF010
USING RUNNER: behave.runner:Runner
@JS01
Feature: Trips requested in each zone # features/js01_trips_per_zone.feature:2
  Covers the first part of JS01 (operations analyst): the number of trips requested in each pickup zone for each
  5-minute period. A period holds the requests with an event time from its start up to, and not including, its end.
  A table holds the only events of its example. Its columns are event fields listed in docs/design.md,
  section Data. A simulated data set is named by its id and described in the same section, under Simulated data
  for the demos.
    Example: One request delivered twice                            # features/js01_trips_per_zone.feature:60
      Given only these trip requests are received:                  # features/steps/data_steps.py:7
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000101 | t-0101  | 161            | 2026-11-23T09:11:00Z | 2026-11-23T09:11:01Z |
        | ev-000102 | t-0102  | 161            | 2026-11-23T09:12:30Z | 2026-11-23T09:12:31Z |
        | ev-000101 | t-0101  | 161            | 2026-11-23T09:11:00Z | 2026-11-23T09:12:40Z |
      When the counts are read at 2026-11-23T09:15:30Z              # features/steps/count_steps.py:24
      Then zone 161 shows 2 trips requested between 09:10 and 09:15 # features/steps/count_steps.py:29

    Example: One simulated hour with 4 requests delivered twice                                # features/js01_trips_per_zone.feature:69
      Given the simulated data set SIM01 "rush-hour"                                           # features/steps/data_steps.py:22
      When the counts are read at 2026-11-23T10:11:00Z                                         # features/steps/count_steps.py:24
      Then zones 48, 161 and 230 show 304, 191 and 342 trips requested between 09:00 and 10:00 # features/steps/count_steps.py:43

1 feature passed, 0 failed, 3 skipped
1 rule passed, 0 failed, 13 skipped
2 scenarios passed, 0 failed, 20 skipped
6 steps passed, 0 failed, 78 skipped
Took 0min 0.000s
```

Prediction: the first example's table has 3 rows and 2 different `event_id`. What does the system count for zone
161 between 09:10 and 09:15 when the duplicate check is off?

```
$ DEDUPE=off uv run behave --tags=@RF010          # from the first failure on
      Then zone 161 shows 2 trips requested between 09:10 and 09:15 # features/steps/count_steps.py:29
      ASSERT FAILED: zone 161, between 09:10 and 09:15: expected 2 trips requested, the system counted 3 (DEDUPE=off: the duplicate check is off)


    Example: One simulated hour with 4 requests delivered twice                                # features/js01_trips_per_zone.feature:69
      Given the simulated data set SIM01 "rush-hour"                                           # features/steps/data_steps.py:22
      When the counts are read at 2026-11-23T10:11:00Z                                         # features/steps/count_steps.py:24
      Then zones 48, 161 and 230 show 304, 191 and 342 trips requested between 09:00 and 10:00 # features/steps/count_steps.py:43
      ASSERT FAILED: zone 48, between 09:00 and 10:00: expected 304 trips requested, the system counted 307 (DEDUPE=off: the duplicate check is off)



Failing scenarios:
  features/js01_trips_per_zone.feature:60  One request delivered twice
  features/js01_trips_per_zone.feature:69  One simulated hour with 4 requests delivered twice

0 features passed, 1 failed, 3 skipped
0 rules passed, 1 failed, 13 skipped
0 scenarios passed, 2 failed, 20 skipped
4 steps passed, 2 failed, 78 skipped
Took 0min 0.000s
```

Step 11 (last lines of each):

```
$ uv run behave --tags=@RF020
1 feature passed, 0 failed, 3 skipped
1 rule passed, 0 failed, 13 skipped
2 scenarios passed, 0 failed, 20 skipped
10 steps passed, 0 failed, 74 skipped
Took 0min 0.000s
$ uv run behave --tags=@RF030
1 feature passed, 0 failed, 3 skipped
1 rule passed, 0 failed, 13 skipped
3 scenarios passed, 0 failed, 19 skipped
13 steps passed, 0 failed, 71 skipped
Took 0min 0.000s
```

Step 12: see `evals/pickup_place/README.md` for the output, with a forced failure.

Step 13:

```
$ uv run pytest -q
.....................................                                    [100%]
37 passed in 2.01s
```

## What stays a draft

The rules R010, R020, R030, R040, R050, R070, R090, R100, R120 and RF040 have examples and do not have step code; SIM04 and SIM05
are described and not generated; the scripts in `scripts/` do not exist yet. That is the state the text is in on Tuesday for
every rule.
