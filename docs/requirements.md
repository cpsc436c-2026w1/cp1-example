# Requirements

Team t00, the rides case: a ride-hailing app on New York taxi zones.

## JS01 Operations analyst: trips requested in each zone

When demand moves between zones during the morning rush (837 completed trips in one morning hour in our three zones in DS01,
*measured*, and one request for each, *assumed*, Q050), I want the number of trips requested in each pickup zone for
each 5-minute period, and each morning yesterday's completed trips with a fare above 0 loaded into one table, so that
I can send free drivers where the requests are and query yesterday's fares in that table.

- **R010** WHEN a 5-minute period ends THE SYSTEM SHALL store one count of requested trips for each pickup zone that had a request in the period | data latency under 60 s at p95, from the period's end to the stored count of the requests received by then (SLO) [Scenario](../features/js01_trips_per_zone.feature)
- **R020** IF a request is received after its period ended THEN THE SYSTEM SHALL add it to the stored count of the period of its event time, and store a count of 1 if its zone does not have a count for that period yet | for a request received up to 10 minutes after its event time, data latency under 60 s at p95, from its receipt to the corrected count (SLO) [Scenario](../features/js01_trips_per_zone.feature)
- **R030** THE SYSTEM SHALL show every count with its zone and the start and end of its period [Scenario](../features/js01_trips_per_zone.feature)
- **R040** WHEN the file of a day's completed trips arrives THE SYSTEM SHALL load each row that has a fare above 0 into table `trips_curated` | data latency under 30 min at p95, from the file's arrival to its rows in `trips_curated` (SLO) [Scenario](../features/js01_yesterdays_trips.feature)
- **R050** IF a completed trip in the file has a fare that is missing, 0 or negative THEN THE SYSTEM SHALL leave it out of `trips_curated` and write it to table `trips_rejected` with the reason [Scenario](../features/js01_yesterdays_trips.feature)

## JS02 Driver: is the trip mine

When I accept a trip offer on my phone (other drivers nearby see the same offer), I want to know within 2 seconds
whether the trip is mine, so that I do not drive to a pickup that another driver took.

- **R070** WHEN a driver accepts a trip that is requested and not assigned THE SYSTEM SHALL assign the trip to that driver | response time under 2 s at p99, from the accept reaching our API to the driver's answer (SLO) [Scenario](../features/trip_assignment.feature)
- **R080** IF a driver accepts a trip that is already assigned THEN THE SYSTEM SHALL refuse the accept and leave the trip with its driver | response time under 2 s at p99, from the accept reaching our API to the driver's answer (SLO) [Scenario](../features/trip_assignment.feature)

## JS03 Rider: who is coming

When I have requested a trip, I want to see which driver is coming, so that I know which car to look for.

- **R090** WHILE a trip is assigned and not completed THE SYSTEM SHALL show the rider the trip's driver [Scenario](../features/trip_assignment.feature)
- **R100** WHEN a trip is completed THE SYSTEM SHALL show the rider the fare | data latency under 5 s at p95, from the completion (SLO) [Scenario](../features/trip_assignment.feature)

## JS04 Support agent: pickup place of a rider's message (added after the proposal)

When a rider writes to support about a trip (free text, about 200 messages a day, Q040), I want to see the pickup
place that the message names, or that it does not name one, so that I can find the trip without guessing where the
rider was waiting.

- **R110** WHERE the system includes the assistant, WHEN a support agent opens a rider's message THE SYSTEM SHALL show the pickup place that the message names, as a name from our list of places, or say that the message names no pickup place | eval `pickup-place`: at least 10 cases, each run 3 times, and the pickup place is correct in at least 80% of the runs (24 of 30 runs for 10 cases) [Scenario](../features/js04_pickup_place.feature)
- **R120** IF a rider's message names more than one pickup place THEN THE SYSTEM SHALL say that the message names more than one pickup place, and not show any of them as the pickup place [Scenario](../features/js04_pickup_place.feature)

## Stakeholder input

From the proposal feedback issue, with its IDs and wording.

- **RF010** Every trip request must be counted exactly once, even when the stream delivers its event twice. Reply: the count uses distinct `event_id`; an id is kept for 24 hours (Q030). [Scenario](../features/js01_trips_per_zone.feature)
- **RF020** A zone and period without events must be shown as no data, not as 0 trips: an empty period and a broken feed look the same. Reply: a count is stored only for a zone with a request in the period, and every other zone and period is shown as `no data`; the RF020 rule checks what is shown. [Scenario](../features/js01_trips_per_zone.feature)
- **RF030** Say what happens when two drivers accept the same trip at the same moment, and show it. Reply [R080]: the write that assigns a trip has a condition: the trip is not assigned yet. [Scenario](../features/trip_assignment.feature)
- **RF040** The count by zone over 30 days must stay fast while the stream adds a small file to `raw/` every minute. Reply: a nightly job compacts each day of `raw/trip-events/` into one file, and the count reads those files; response time under 5 s at p50, from the start of the count query to its result (SLO), run on AWS. [Scenario](../features/js01_trips_per_zone.feature)
- **RF050** Every AWS resource carries the course tags. Reply: each script in `scripts/` tags what it creates with `Project=436c`, `Team=t00` and `Owner=course` (`scripts/common.py`, with the recipe helper `scripts/tags.py`), and every name starts with `t00-`. Read: `scripts/`, and `evidence/deploy-tags.txt`, the tags AWS returned for each resource of the slice on 2026-11-26. (PR #3)
- **RQ010** Choose a meaningful long-term horizon for your system, for example 3 months, 6 months or a year, and calculate what your cloud architecture costs to run over it, in CAD, using the course price sheet. Reply: We will calculate the cost of one year in CAD, based on the completed trips a day in DS01 (*measured*), one request for each of them (*assumed*, Q050) and the course price sheet: processing the stream in Lambda, DynamoDB write units, and the Athena data scanned for the counts. Read at Checkpoint 2: `docs/design.md`, section Cost.
- **RQ020** Analyze your data latency against changes in your replay speed. Reply: We will write the test that replays SIM01 at 1, 10 and 50 times its speed and checks R010's data latency at each speed. Read at Checkpoint 2: `docs/design.md`, section Experiments, with the test's results.

## Evals

- **pickup-place**, for R110 [Scenario](../features/js04_pickup_place.feature)
  - Cases: 10 rider messages written by the team, each with its reference value: 7 that name a pickup place, 3 that do not (one of them names only a destination). File `evals/pickup_place/cases.jsonl`; our list of places is `evals/pickup_place/places.txt`.
  - Correct when (checked by code): the reply is a JSON object with one field, `pickup_place`, and its value equals the reference value. A reply with text around the JSON or with another field is not correct.
  - Runs: each case 3 times, 30 runs, because the model's replies vary from run to run.
  - Passes when: the pickup place is correct in at least 24 of the 30 runs (accuracy at least 80%).
  - Model in use: Qwen 3.8 27B (`qwen3.8-27b`) through the course LLM gateway.

## Assumptions

| Id | What the case does not say | Who would answer | We assume | Affects |
|---|---|---|---|---|
| Q010 | Does a trip that the rider cancels still count as requested? | the operations analyst | yes, the count is of requests | R010, RF010 |
| Q020 | Which driver gets the trip when two accept at the same moment? | the product owner | the one whose write reaches the table first | R080, RF030 |
| Q030 | Can the app send an event again more than 24 hours after it first sent it? | the app's team | no: the app's retries end within minutes | RF010 |
| Q040 | How many messages do riders send to support a day? | the support team's lead | about 200 | R110 |
| Q050 | How many trip requests are there for each completed trip? DS01 has only completed trips | the operations analyst | one request for each completed trip | JS01, R010, RQ010 |

## Decisions

- Decision (budget-check BC010, t00-trip-events, PR #3): keep. The stream is the one resource of the slice that bills by the hour (0.0165 USD, 11.88 for 30 days); scripts/stream.py up creates it for a run or a demo, scripts/teardown.sh deletes it first, and nothing is kept between runs (docs/design.md, Resources).
