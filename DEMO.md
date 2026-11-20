# Studio demo: the rides example, file by file

About one minute a step. Steps 1 to 8 are Checkpoint 1: **text that a team writes by Monday**, and the two checks
of that text. Steps 9 to 13 show **where Checkpoint 2 goes**: the same text made to run. Nothing calls AWS.
All output below is pasted from runs in this repository on 2026-11-19, steps 8, 10, 11 and 13 again on 2026-11-20.

Before the studio: `uv` installed; `uv sync` once in this folder.

## Checkpoint 1: what a team writes for Monday

| # | Show | Say |
|---|---|---|
| 1 | `README.md`, the table | the upper rows are Monday's hand-in, the lower rows are Checkpoint 2 |
| 2 | `docs/requirements.md`, JS01 | a story is a heading; under it lines R010 … in five forms: WHEN (R010), IF … THEN (R020), no keyword (R030), WHILE (R090 under JS03), WHERE with WHEN (R110 under JS04). A code is used once in the file; a number after `|` is the requirement's target; `[Scenario]` at the end of a line links the feature file that has its rule |
| 3 | `docs/requirements.md`, Stakeholder input | the feedback codes with their wording, then `We:` and what the team does; the line ends with `[Scenario]` and the feature file (RF010 to RF040) or with `Read:` and what staff will read (RF050); RQ010 has a note for Checkpoint 1 that says what the team will show at Checkpoint 2; then the Evals entry for R110: cases, what counts as correct, runs, the count that passes, the model in use |
| 4 | `docs/design.md`, Data, Our data | four sentences: DS01 and DS02, the subset with its rows and size, and what the events are built from. Run the count below |
| 5 | `docs/design.md`, Data, Simulated data for the demos | SIM01 to SIM05, one bullet each in words: what it holds, its injected faults with exact counts, the code it shows |
| 6 | `docs/design.md`, Data, Event fields the scenarios use | one line for each kind of event; the fields are the columns of an example's table. Field types and valid values come at Checkpoint 2 |
| 7 | `features/js01_trips_per_zone.feature`, rule `@RF010` | story tag on the feature, code tag on the rule; one example with a 3-row table, one with `Given the simulated data set SIM01 "rush-hour"`. Then `trip_assignment.feature`: two story tags, a rule with two code tags (`@R080 @RF030`). Then the `@eval` gate in `js04_pickup_place.feature` |
| 8 | the two checks below | the traceability table, then the dry run on the Monday state |

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
Code   Defined                Used
JS01   requirements.md:5      js01_trips_per_zone.feature:2, js01_yesterdays_trips.feature:2
R010   requirements.md:11     js01_trips_per_zone.feature:10, design.md (4 lines)
R020   requirements.md:12     js01_trips_per_zone.feature:23, design.md (3 lines)
R030   requirements.md:13     js01_trips_per_zone.feature:48, design.md (4 lines)
R040   requirements.md:14     js01_yesterdays_trips.feature:8, design.md (5 lines)
R050   requirements.md:15     js01_yesterdays_trips.feature:16, design.md (4 lines)
JS02   requirements.md:17     trip_assignment.feature:2
R070   requirements.md:22     trip_assignment.feature:9, design.md (5 lines)
R080   requirements.md:23     trip_assignment.feature:17, design.md (5 lines)
JS03   requirements.md:25     trip_assignment.feature:2
R090   requirements.md:29     trip_assignment.feature:37, design.md (6 lines)
R100   requirements.md:30     trip_assignment.feature:46, design.md (6 lines)
JS04   requirements.md:32     js04_pickup_place.feature:2
R110   requirements.md:38     js04_pickup_place.feature:8, design.md (3 lines)
RF010  requirements.md:44     js01_trips_per_zone.feature:58, design.md (5 lines)
RF020  requirements.md:45     js01_trips_per_zone.feature:79, design.md (6 lines)
RF030  requirements.md:46     trip_assignment.feature:17, design.md (4 lines)
RF040  requirements.md:47     js01_yesterdays_trips.feature:32, design.md (6 lines)
RF050  requirements.md:48     design.md (1 lines)
RQ010  requirements.md:49     read, not run
DS01   design.md:93           requirements.md:7, SIM01, SIM02, SIM03, SIM04, SIM05
DS02   design.md:97           not used
SIM01  design.md:103          js01_trips_per_zone.feature:70
SIM02  design.md:105          js01_trips_per_zone.feature:93
SIM03  design.md:107          trip_assignment.feature:29
SIM04  design.md:109          js01_yesterdays_trips.feature:11
SIM05  design.md:111          js01_yesterdays_trips.feature:36

27 codes and data ids, 0 problems
$ echo $?
0
```

RF050 and RQ010 are read, not run, so they do not have a rule. To see a problem, change
`SIM02` to `SIM09` in the feature file and run it again:
`PROBLEM js01_trips_per_zone.feature:93: SIM09 is not defined in docs/design.md, section Data`, exit code 1.

Step 8, the dry run on what a team hands in (tag `cp1`: no step code, `features/steps/.gitkeep` only):

```
$ git checkout -q cp1
$ uvx behave@1.3.3 --dry-run --no-snippets        # last lines
0 features passed, 0 failed, 4 error, 0 skipped
0 rules passed, 0 failed, 13 error, 0 skipped
0 scenarios passed, 0 failed, 19 error, 0 skipped
0 steps passed, 0 failed, 0 skipped, 72 undefined
$ grep -c "^ *Example:" features/*.feature        # 17 in all
features/js01_yesterdays_trips.feature:3
features/js01_count_questions.feature:2
features/js01_trips_per_zone.feature:7
features/trip_assignment.feature:5
$ git checkout -q main
```

"error" and "undefined" are what Monday looks like: every feature was read, and no step has code yet. The count
of scenarios (17) equals the number of `Example:` lines.

## Checkpoint 2: the same text, running

| # | Show | Say |
|---|---|---|
| 9 | `sim/datasets.py` beside Data, Simulated data for the demos; run the generator | the bullets became settings; the id is the folder name; the folders are those of `raw/trip-events/` |
| 10 | run `@RF010`; ask for a prediction; run it with `DEDUPE=off` | the example knew its answer before the system ran; with the check off the count is 3, not 2, and the simulated hour with its 4 duplicates fails too |
| 11 | run `@RF020` and `@RF030` | a zone without events is `no data`; two accepts, each sent before the other has an answer: the conditional write gives the trip to one driver and refuses the other |
| 12 | run `features/js04_pickup_place.feature`; then `check.py` alone | the gate reads the eval's counts from its steps: 10 cases, 3 runs each, at least 24 of 30 correct. The replies are recorded examples written by hand; a live run through the course LLM gateway is not written yet |
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
    Example: One request delivered twice                            # features/js01_trips_per_zone.feature:46
      Given only these trip requests are received:                  # features/steps/data_steps.py:7
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000101 | t-0101  | 161            | 2026-11-23T09:11:00Z | 2026-11-23T09:11:01Z |
        | ev-000102 | t-0102  | 161            | 2026-11-23T09:12:30Z | 2026-11-23T09:12:31Z |
        | ev-000101 | t-0101  | 161            | 2026-11-23T09:11:00Z | 2026-11-23T09:12:40Z |
      When the counts are read at 2026-11-23T09:16:00Z              # features/steps/count_steps.py:24
      Then zone 161 shows 2 trips requested between 09:10 and 09:15 # features/steps/count_steps.py:29

    Example: One simulated hour with 4 requests delivered twice                                # features/js01_trips_per_zone.feature:55
      Given the simulated data set SIM01 "rush-hour"                                           # features/steps/data_steps.py:22
      When the counts are read at 2026-11-23T10:11:00Z                                         # features/steps/count_steps.py:24
      Then every zone and period shows the count computed from the data set's record of events # features/steps/count_steps.py:43

1 feature passed, 0 failed, 3 skipped
1 rule passed, 0 failed, 12 skipped
2 scenarios passed, 0 failed, 18 skipped
6 steps passed, 0 failed, 70 skipped
Took 0min 0.000s
```

Prediction: the first example's table has 3 rows and 2 different `event_id`. What does the system count for zone
161 between 09:10 and 09:15 when the duplicate check is off?

```
$ DEDUPE=off uv run behave --tags=@RF010          # from the first failure on
      Then zone 161 shows 2 trips requested between 09:10 and 09:15 # features/steps/count_steps.py:29
      ASSERT FAILED: zone 161, between 09:10 and 09:15: expected 2 trips requested, the system counted 3 (DEDUPE=off: the duplicate check is off)


    Example: One simulated hour with 4 requests delivered twice                                # features/js01_trips_per_zone.feature:55
      Given the simulated data set SIM01 "rush-hour"                                           # features/steps/data_steps.py:22
      When the counts are read at 2026-11-23T10:11:00Z                                         # features/steps/count_steps.py:24
      Then every zone and period shows the count computed from the data set's record of events # features/steps/count_steps.py:43
      ASSERT FAILED: zone 48, between 09:00 and 09:05: expected 20 trips requested, the system counted 21 (DEDUPE=off: the duplicate check is off)



Failing scenarios:
  features/js01_trips_per_zone.feature:46  One request delivered twice
  features/js01_trips_per_zone.feature:55  One simulated hour with 4 requests delivered twice

0 features passed, 1 failed, 3 skipped
0 rules passed, 1 failed, 12 skipped
0 scenarios passed, 2 failed, 18 skipped
4 steps passed, 2 failed, 70 skipped
Took 0min 0.000s
```

Step 11 (last lines of each):

```
$ uv run behave --tags=@RF020
1 feature passed, 0 failed, 3 skipped
1 rule passed, 0 failed, 12 skipped
2 scenarios passed, 0 failed, 18 skipped
10 steps passed, 0 failed, 66 skipped
Took 0min 0.000s
$ uv run behave --tags=@RF030
1 feature passed, 0 failed, 3 skipped
1 rule passed, 0 failed, 12 skipped
2 scenarios passed, 0 failed, 18 skipped
8 steps passed, 0 failed, 68 skipped
Took 0min 0.000s
```

Step 12: see `evals/pickup_place/README.md` for the output, with a forced failure.

Step 13:

```
$ uv run pytest -q
...............................                                          [100%]
35 passed in 1.96s
```

## What stays a draft

The rules R010, R020, R030, R040, R050, R070, R090, R100 and RF040 have examples and no step code; SIM04 and SIM05
are described and not generated; no script in `scripts/` exists. That is the state the text is in on Monday for
every rule.
