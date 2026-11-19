# Requirements

Team t00, the rides case: a ride-hailing app on New York taxi zones. Codes are used once in this file.

## JS01 Operations analyst: trips requested in each zone (focus)

When demand moves between zones during the morning rush (about 840 requests an hour in our three zones, from DS01), I want the
number of trips requested in each pickup zone for each 5-minute period, and each morning yesterday's completed trips
in one table, so that I can send free drivers where the requests are and check yesterday's fares.

- **R010** WHEN a 5-minute period ends THE SYSTEM SHALL store one count of requested trips for each pickup zone that had a request in the period | within 60 s of the period's end, from the requests received by then (SLO) · BDD: [js01_trips_per_zone.feature](../features/js01_trips_per_zone.feature)
- **R020** IF a request is received after its period ended THEN THE SYSTEM SHALL add it to the stored count of the period of its event time, and store a count of 1 if its zone does not have a count for that period yet | a request received up to 10 minutes after its event time is in the count within 60 s of its receipt (SLO) · BDD: [js01_trips_per_zone.feature](../features/js01_trips_per_zone.feature)
- **R030** THE SYSTEM SHALL show every count with its zone and the start and end of its period · BDD: [js01_trips_per_zone.feature](../features/js01_trips_per_zone.feature)
- **R040** WHEN the file of a day's completed trips arrives THE SYSTEM SHALL load each row that has a fare above 0 into table `trips_curated` | a file that arrives by 05:30 UTC is loaded before 06:00 UTC (SLO) · BDD: [js01_yesterdays_trips.feature](../features/js01_yesterdays_trips.feature)
- **R050** IF a completed trip in the file has a fare that is missing, 0 or negative THEN THE SYSTEM SHALL leave it out of `trips_curated` and write it to table `trips_rejected` with the reason · BDD: [js01_yesterdays_trips.feature](../features/js01_yesterdays_trips.feature)
- **R060** WHERE the system includes the assistant, WHEN the analyst asks about trip counts in plain language THE SYSTEM SHALL answer with the count the question asks for and state only counts that are in the rows its query returned | eval `count-answers` scores at least 0.8, which is 5 of its 6 cases correct (SLO) · BDD: [js01_count_questions.feature](../features/js01_count_questions.feature)

## JS02 Driver: is the trip mine (focus)

When I accept a trip offer on my phone (other drivers nearby see the same offer), I want to know within 2 seconds
whether the trip is mine, so that I do not drive to a pickup that another driver took.

- **R070** WHEN a driver accepts a trip that is requested and not assigned THE SYSTEM SHALL assign the trip to that driver | the driver has the answer within 2 s (SLO) · BDD: [trip_assignment.feature](../features/trip_assignment.feature)
- **R080** IF a driver accepts a trip that is already assigned THEN THE SYSTEM SHALL refuse the accept and leave the trip with its driver | the driver has the answer within 2 s (SLO) · BDD: [trip_assignment.feature](../features/trip_assignment.feature)

## JS03 Rider: who is coming

When I have requested a trip, I want to see which driver is coming, so that I know which car to look for.

R070 and R080 also serve this story: the rider and the driver read the same assignment.

- **R090** WHILE a trip is assigned and not completed THE SYSTEM SHALL show the rider the trip's driver · BDD: [trip_assignment.feature](../features/trip_assignment.feature)
- **R100** WHEN a trip is completed THE SYSTEM SHALL show the rider the fare | within 5 s of the completion (SLO) · BDD: [trip_assignment.feature](../features/trip_assignment.feature)

## Constraints and requests

From our Feedback 1 issue, with its codes and its wording. A `Check` cell starts with `examples tagged` or `read:`.

| Code | Constraint or request | What we do or will show | Check | Due | Issue |
|---|---|---|---|---|---|
| RF010 | Every trip request must be counted exactly once, even when the stream delivers its event twice. | the count uses distinct `event_id`: the id and the count are written in one transaction, and an id is kept for 24 hours, so a second delivery up to 24 hours after the first is not counted (Q030) | examples tagged `@RF010` | cp2 | |
| RF020 | A zone and period without events must be shown as no data, not as 0 trips: an empty period and a broken feed look the same. | a count is stored only for a zone with a request in the period; the reader shows `no data` for the rest | examples tagged `@RF020` | cp2 | |
| RF030 | Say what happens when two drivers accept the same trip at the same moment, and show it. | each accept is one request to our API; the write that assigns a trip has a condition: the trip is not assigned yet (R080) | examples tagged `@RF030` | cp2 | |
| RF040 | The count by zone over 30 days must stay fast while the stream adds a small file to `raw/` every minute. | a nightly job compacts each day of `raw/trip-events/` into one file of table `trip_events_compacted`, and the count reads that table; our target is a median under 5 s (SLO, not measured yet) | examples tagged `@RF040`, run on AWS | cp2 | |
| RF050 | Every AWS resource carries the course tags. | each script in `scripts/` tags what it creates: `Project=436c`, `Team=t00`, `Owner=<name>` | read: `scripts/` and the tags on the resources | cp2 | |
| RQ010 | Say how long raw events are kept and who may delete them. | note for cp1: at Checkpoint 2 we will show, in `docs/design.md`, section Data, part (b), the number of days raw events are kept, the rule that deletes them and the role that may delete them | read: `docs/design.md`, section Data, part (b) | cp2 | |

## Evals

One row for each requirement that a model's answers must meet. The cases are described in words at Checkpoint 1.

| Eval | For | Cases | What counts as correct | Threshold |
|---|---|---|---|---|
| `count-answers` | R060 | 6 questions with the rows their query returns: 4 where the rows hold the count, 2 where the query returns 0 rows (injected fault `no-rows`) | checked by code: with rows, the reply states the count the question asks for and every count in the reply is in the rows; without rows the reply says there is no data and does not state a count | 0.8, which with 6 cases is at least 5 correct |

## Assumptions

| Id | What the case does not say | Who would answer | Assumed value | Affects |
|---|---|---|---|---|
| Q010 | Does a trip that the rider cancels still count as requested? | the operations analyst | yes, the count is of requests | R010, RF010 |
| Q020 | Which driver gets the trip when two accept at the same moment? | the product owner | the one whose write reaches the table first; we do not compare the phones' times | R080, RF030 |
| Q030 | Can the app send an event again more than 24 hours after it first sent it? | the app's team | no: the stream keeps a record for 24 hours, and the app's retries end within minutes | RF010 |
