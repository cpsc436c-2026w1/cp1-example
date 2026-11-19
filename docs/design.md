# Design

Team t00, the rides case. Sections Workflows and Sketch were sections 4 and 5 of the proposal.

## Sketch

![Sketch of the system](sketch.svg)

Source: [sketch.puml](sketch.puml) (PlantUML). Every box is a row in [Resources](#resources), or in the table of what
is outside our system.

## Workflows

Each workflow names the codes it serves and the components it uses; every component is a row in
[Resources](#resources).

### Counting requests · R010, R020, RF010, RF020

The trips service sends each trip event to the stream. The counting function counts requests by pickup zone in
5-minute periods and stores each count within 60 s of the period's end; a late request corrects the count of its
period. It writes each event's id together with the count, so an event delivered twice is counted once.

Components: `t00-trip-events`, `t00-count-requests`, `t00-zone-counts`, `t00-seen-events`

### Assigning trips · R070, R080, R090, R100, RF030

The tracking function keeps each trip current from the stream. A driver's accept comes to the API as one request;
the assign function makes one conditional write, so only one of two accepts for a trip is answered `assigned`,
within 2 s.

Components: `t00-trip-events`, `t00-track-trips`, `t00-api`, `t00-assign-trip`, `t00-trips`

### Reading counts and trips · R030, R090, R100, RF020

The read function answers the rider's and the analyst's pages through the API. A zone and period without a count
is shown as no data, not as 0.

Components: `t00-api`, `t00-read`, `t00-zone-counts`, `t00-trips`

### Lake and nightly jobs · R040, R050, RF040

Firehose writes the stream to the bucket about once a minute, and at 00:30 UTC the compaction job rewrites the day
before as one Parquet file. The curation job loads the nightly export's completed trips with a fare above 0 before
06:00 UTC and sets the other rows aside.

Components: `t00-trip-events-to-lake`, `t00-lake-<account-id>`, `t00_lake`, `t00-compact-events`, `t00-curate-trips`

### Questions to the assistant · R060

The assistant answers the analyst's questions about counts by querying the lake with Athena, and states only
counts it read.

Components: `t00-api`, `t00-assistant`, `t00_lake`

## Correctness properties

- **P010** for any zone and period, once every request received up to 10 minutes late has arrived and 60 s have passed, the stored count equals the number of distinct `event_id` of requests with an event time in that period, when no event is delivered again more than 24 hours after its first delivery; validates R010, R020, RF010
- **P020** for any trip, at most one accept is answered `assigned`; validates R080

## Resources

Every resource is in ca-central-1, has a name that starts with `t00-`, and carries the tags `Project=436c`,
`Team=t00`, `Owner=<name>` (RF050). The Glue database and its tables are the exception in the names: they use an
underscore (`t00_lake`, `trips_curated`), so that a query does not have to quote them. The scripts are written for
Checkpoint 2.

| Resource | Name | Created by | Serves |
|---|---|---|---|
| Kinesis data stream | `t00-trip-events` | `scripts/stream.py up` | R010, R020, RF010 |
| Lambda function | `t00-count-requests` | `scripts/counting.py up` | R010, R020, RF010, RF020 |
| DynamoDB tables | `t00-zone-counts`, `t00-seen-events` | `scripts/counting.py up` | R010, R030, RF010, RF020 |
| Lambda function | `t00-track-trips` | `scripts/assignment.py up` | R070, R090, R100 |
| Lambda function | `t00-assign-trip` | `scripts/assignment.py up` | R070, R080, RF030 |
| DynamoDB table | `t00-trips` | `scripts/assignment.py up` | R070, R080, R090, R100, RF030 |
| API Gateway HTTP API | `t00-api` | `scripts/api.py up` | R030, R060, R070, R080, R090, R100 |
| Lambda function | `t00-read` | `scripts/api.py up` | R030, R090, R100, RF020 |
| Firehose stream | `t00-trip-events-to-lake` | `scripts/lake.py up` | RF040 |
| S3 bucket | `t00-lake-<account-id>` | `scripts/lake.py up` | R040, R050, RF040 |
| Glue database and tables | `t00_lake` | `scripts/lake.py up` | R040, R050, RF040 |
| Glue job | `t00-curate-trips` | `scripts/curate.py up` | R040, R050 |
| Glue job, run every night at 00:30 UTC | `t00-compact-events` | `scripts/compact.py up` | RF040 |
| Lambda function (the assistant) | `t00-assistant` | `scripts/assistant.py up` | R060 |

The routes of `t00-api`:

| Route | Answered by | For |
|---|---|---|
| `POST /trips/{trip_id}/accept` | `t00-assign-trip` | the accept of a driver: `assigned` or `refused` (R070, R080) |
| `GET /trips/{trip_id}` | `t00-read` | the rider: the trip's driver, and the fare once the trip is completed (R090, R100) |
| `GET /counts` | `t00-read` | the counts by zone and period, `no data` where a count does not exist (R030, RF020) |
| `GET /dashboard` | `t00-read` | the analyst's page, which shows the counts of `GET /counts` (R030) |
| `POST /questions` | `t00-assistant` | a question about counts in plain language (R060) |

Outside our system. We do not create these; our system relies on what the last column says.

| Who | Sends | To | What we rely on |
|---|---|---|---|
| the app's trips service | each trip event | stream `t00-trip-events` | one JSON object as in Data, part (c); an event may arrive twice or late; an event is not sent again more than 24 hours after it was first sent (Q030) |
| the app's trips service | each accept, as one request | `POST /trips/{trip_id}/accept` | the body holds `event_id`, `driver_id` and `event_time`; the app passes our answer to the driver's phone |
| the app's nightly export | one CSV file with the day's completed trips | `raw/trip-exports/dt=<day>/` in our bucket | the columns are the fields of `trip_completed`; the file arrives by 05:30 UTC |
| the rider's page and the analyst's browser | reads and questions | the `GET` routes and `POST /questions` | none |

## Data

Five parts, in this order: (a) the real data the system is built on, (b) where data lives in our system,
(c) the events, (d) the simulated data sets the scenarios use, (e) which requirement and scenario uses which data.
On Monday all five are text: every path below is named, and no file under `sim/data/` or in the bucket has to
exist. At Checkpoint 2 the generator writes the files of part (d) and behave loads each by its id.

A number below is marked *measured* (we ran a query; the date and the tool are given), *given* (a source page
states it) or *our choice* (we chose it).

### (a) Sources

| Id | Data set | Owner and licence | Where the original lives | Format and size | How it updates | Subset we use | Course copy |
|---|---|---|---|---|---|---|---|
| DS01 | High Volume For-Hire Vehicle (HVFHV) trip records: one row for each finished trip of a high-volume for-hire service in New York | NYC Taxi and Limousine Commission (TLC). Terms: [NYC.gov Terms of Use](https://www.nyc.gov/main/terms-of-use); TLC states it did not create the data and does not vouch for its accuracy ([trip record page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)) | one file a month over HTTPS: `https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-03.parquet` (linked from the trip record page). Not read from S3: see the note below | Parquet. March 2024: 21,280,788 rows, 24 columns, 0.51 GB (*measured* 2026-11-19, DuckDB over HTTPS) | a new month about two months after it ends (*given*, trip record page). The page does not say whether a published month can change, so `scripts/load_source.py` records the size and the SHA-256 of the file it copies | Uber trips (`hvfhs_license_num = 'HV0003'`) picked up in a Manhattan zone in March 2024: 6,045,943 rows, 0.20 GB as Parquet, 67 pickup zones (*measured* 2026-11-19) | `course.course_rides.rides` in Athena: New York for-hire rides, January 2023 to December 2025, 17.4 GB (*given*, course resources page) |
| DS02 | Taxi zone lookup: the id, borough and name of each zone | TLC, same terms | `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv` | CSV, 265 rows, 4 columns (*measured* 2026-11-19) | rarely | the 69 rows of borough Manhattan (*measured*) | `course.course_rides.zones` (*given*, course records; not queried here) |

Notes on the sources:

- **S3.** The Registry of Open Data on AWS lists DS01 as bucket `s3://nyc-tlc` in Region `us-east-1`, "AWS account
  required" ([entry](https://registry.opendata.aws/nyc-tlc-trip-records-pds/)). From our account both a listing and
  a read of one object were refused on 2026-11-19, so we read the HTTPS address above.
- **Columns of DS01 we use:** `hvfhs_license_num`, `request_datetime`, `dropoff_datetime`, `PULocationID`,
  `DOLocationID`, `trip_miles`, `trip_time` (seconds), `base_passenger_fare`, `driver_pay`. The times are New York
  local time without a zone. `HV0003` is Uber in TLC's data dictionary (*given*; we did not re-read the dictionary).
- **What DS01 does not have:** a driver, a rider, the time of the accept, or any event other than the finished
  trip. Part (c) says where each field of our events comes from.
- **Missing data in the subset:** 228 of the 6,045,943 rows have a fare of 0 or less (*measured*), which is why
  R050 exists.
- **How to check:** `uvx --from duckdb-cli duckdb`, then
  `SELECT count(*) FROM 'https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-03.parquet';`
  reads the file's footer only.

### (b) Where data lives in our system

One bucket, in ca-central-1. `<account-id>` is read from `aws sts get-caller-identity` and never written here.

```
s3://t00-lake-<account-id>/
├── source/
│   ├── ds01/month=2024-03/trips.parquet     the subset of DS01, copied once
│   └── ds02/taxi_zone_lookup.csv            DS02, copied once
├── raw/
│   ├── trip-events/dt=2026-11-23/hour=09/   events as received, about one file a minute
│   └── trip-exports/dt=2026-11-22/          the app's file of a day's completed trips
├── curated/
│   ├── trips/dt=2026-11-22/                 completed trips with a fare, one file a day
│   ├── trip_events/dt=2026-11-22/           the day's events of raw/trip-events/, compacted into one file
│   └── trips_rejected/dt=2026-11-22/        rows left out, with the reason
├── sim/
│   └── SIM01/trip-events/dt=2026-11-23/hour=09/   a simulated data set, laid out as raw/
└── athena-results/
```

| Prefix | Glue table in `t00_lake` | File format | Folders mean | Written by |
|---|---|---|---|---|
| `source/ds01/` | `source_trips` | Parquet | `month`: month of the trips | `scripts/load_source.py`, once |
| `source/ds02/` | `zones` | CSV | none | `scripts/load_source.py`, once |
| `raw/trip-events/` | `trip_events_raw` | JSONL (one event a line), gzip | `dt`, `hour`: day and hour the event was received, UTC | Firehose stream `t00-trip-events-to-lake` |
| `raw/trip-exports/` | `trip_exports_raw` | CSV | `dt`: the day the trips were completed | the app's nightly export |
| `curated/trips/` | `trips_curated` | Parquet | `dt`: the day the trip was completed | Glue job `t00-curate-trips` |
| `curated/trips_rejected/` | `trips_rejected` | Parquet | `dt`: as above | Glue job `t00-curate-trips` |
| `curated/trip_events/` | `trip_events_compacted` | Parquet, one file a day | `dt`: the day the events were received, UTC | Glue job `t00-compact-events`, at 00:30 UTC for the day before |
| `sim/<id>/` | none: read by the tests | as the prefix it stands in for | as the prefix it stands in for | `sim/generate.py`, then `aws s3 sync sim/data/ s3://t00-lake-<account-id>/sim/` |

The folders of `raw/trip-events/` follow the time of receipt, not the event time: Firehose names a folder from the
arrival time of the oldest record in the file, in UTC ([custom prefixes](https://docs.aws.amazon.com/firehose/latest/dev/s3-prefixes.html)).
A late request may therefore be in a later hour folder than its period, so a query by event time reads one hour
more than it asks for. Firehose puts records one after another, so the stream is set to add a line break after each
([new line delimiter](https://docs.aws.amazon.com/firehose/latest/dev/dynamic-partitioning-s3bucketprefix.html)).

The operational store, DynamoDB:

| Table | Key | Holds | Written by |
|---|---|---|---|
| `t00-trips` | `trip_id` | the trip's current state: `status`, `driver_id`, `pickup_zone_id`, and `fare` once the trip is completed | `t00-track-trips` (the request and the completion); `t00-assign-trip` (the driver, with the condition that the trip does not have a driver yet) |
| `t00-zone-counts` | `zone_id` and `period_start` | `trips_requested` for that zone and period; an item exists only if the period had a request | `t00-count-requests`, in one transaction with the id in `t00-seen-events` |
| `t00-seen-events` | `event_id` | the ids already counted. Each id has an expiry time 24 hours after its first delivery (DynamoDB time to live). DynamoDB deletes an expired item later, typically within a few days ([TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)), so an id is kept for at least 24 hours | `t00-count-requests`, in one transaction with the count |

How long raw events are kept and who may delete them (RQ010): due at Checkpoint 2. The note for Monday is in the
row of RQ010 in `docs/requirements.md`.

The count by zone over 30 days (RF040) reads the compacted table, 30 files for 30 days, while Firehose goes on
adding small files to `raw/trip-events/`:

```sql
SELECT pickup_zone_id, count(DISTINCT event_id) AS trips_requested
FROM t00_lake.trip_events_compacted
WHERE event_type = 'trip_requested' AND dt BETWEEN '2026-10-24' AND '2026-11-22'
GROUP BY pickup_zone_id;
```

### (c) Event kinds

Every event is one JSON object. Three fields are in every kind:

| Field | Type | Example | Valid values | Comes from |
|---|---|---|---|---|
| `event_id` | text | `ev-000412` | any text; one id for one event, so the same id again is the same event | generated (our choice) |
| `event_type` | text | `trip_requested` | one of: `trip_requested`, `trip_accepted`, `trip_completed` | generated (our choice) |
| `event_time` | UTC time | `2026-11-23T09:01:10Z` | any time: when it happened on the phone or in the app | see each kind |

**`trip_requested`**: a rider asked for a trip.

| Field | Type | Example | Valid values | Comes from |
|---|---|---|---|---|
| `trip_id` | text | `t-0412` | any text; one id for one trip, the same in all its events | generated: one for each row of DS01 |
| `rider_id` | text | `p-00317` | the id of a rider | generated (our choice): DS01 does not have riders |
| `pickup_zone_id` | whole number | `161` | one of the zone ids of DS02 | DS01 `PULocationID` |
| `dropoff_zone_id` | whole number | `230` | one of the zone ids of DS02 | DS01 `DOLocationID` |
| `quoted_fare` | decimal | `27.13` | > 0, in USD | DS01 `base_passenger_fare` (our choice: the quote equals the final fare) |
| `event_time` | UTC time | `2026-11-23T09:01:10Z` | as above | DS01 `request_datetime`, moved to the simulated day (part d) |

**`trip_accepted`**: a driver took the trip. On the stream it is the accept that our API answered with `assigned`; the body of an accept sent to the API has the same fields.

| Field | Type | Example | Valid values | Comes from |
|---|---|---|---|---|
| `trip_id` | text | `t-0412` | the id of a trip that was requested | as above |
| `driver_id` | text | `d-0046` | the id of a driver | generated (our choice): DS01 does not have drivers; 200 drivers |
| `event_time` | UTC time | `2026-11-23T09:01:18Z` | as above | generated (our choice): 3 to 15 s after the request |

**`trip_completed`**: the driver closed the trip.

| Field | Type | Example | Valid values | Comes from |
|---|---|---|---|---|
| `trip_id` | text | `t-0412` | the id of a trip that was accepted | as above |
| `driver_id` | text | `d-0046` | the id of the driver who was assigned | as in `trip_accepted` |
| `dropoff_zone_id` | whole number | `230` | one of the zone ids of DS02 | DS01 `DOLocationID` |
| `trip_miles` | decimal | `1.38` | >= 0 | DS01 `trip_miles` |
| `trip_time_s` | whole number | `670` | >= 0, in seconds | DS01 `trip_time` |
| `fare` | decimal | `27.13` | > 0, in USD; a trip with a missing, 0 or negative fare is rejected (R050) | DS01 `base_passenger_fare` |
| `driver_pay` | decimal | `20.35` | any amount, in USD | DS01 `driver_pay` |
| `event_time` | UTC time | `2026-11-23T09:17:28Z` | as above | generated (our choice): the accept, plus 5 minutes to the pickup, plus `trip_time_s` |

**`delivery`**: one arrival of an event at our system. It has the fields of the event and:

| Field | Type | Example | Valid values | Comes from |
|---|---|---|---|---|
| `received_time` | UTC time | `2026-11-23T09:01:11Z` | any time, not before the event time: set by our system when the event arrives; the folder in `raw/` follows it | generated (our choice): 1 s after the event time unless a fault says otherwise |

An injected fault is not a field of the event: the system under test must not be told. It is recorded beside the
data, in `_truth/faults.jsonl`.

### (d) Simulated data sets

DS01 holds finished trips of 2024; our system receives live events. So each data set below is built from DS01:
its rows are sampled and turned into events (part c), with the times moved to the simulated day. The sample is
`sim/seed/ds01_sample.csv`, written by `tools/extract_seed.sql`: the 837 trips of the subset requested between
08:00 and 09:00 New York time on Thursday 2024-03-14 from zones 48 Clinton East (304 trips), 161 Midtown Center
(191) and 230 Times Sq/Theatre District (342) (*measured*). Its hour is moved to 09:00 to 10:00 UTC on
2026-11-23, with minute and second kept. All data sets use seed 436.

| Id | Name | Kind | From | Holds | Rates and timing | Injected faults, and how often | Written to |
|---|---|---|---|---|---|---|---|
| SIM01 | `rush-hour` | event stream | DS01 (the sample); zone ids of DS02 | the three events of each of the 837 trips: 2,511 events | 837 requests in the hour, 9 to 38 in a zone and period (*measured*); an event is received 1 s after its event time | `duplicate`: 4 requests delivered a second time, 2 to 30 s after the first; `late`: 2 other requests received 6 to 10 minutes late (exact counts) | `sim/data/SIM01/` and `s3://t00-lake-<account-id>/sim/SIM01/`, laid out as `raw/trip-events/` |
| SIM02 | `quiet-zone` | event stream | DS01 (the sample); zone ids of DS02 | as SIM01 without its faults, less the trips below: 2,331 events | as SIM01 | `quiet`: every event of the 60 trips requested in zone 48 between 09:25 and 09:35 is left out | `sim/data/SIM02/` and `s3://t00-lake-<account-id>/sim/SIM02/`, laid out as `raw/trip-events/` |
| SIM03 | `double-accept` | two concurrent writers | DS01 (the sample); zone ids of DS02 | the first 20 trips of zone 161: one request and two accepts each, from two different drivers: 60 rows. An accept is the body of a request to `POST /trips/{trip_id}/accept`, stored as a `trip_accepted` row; the example sends it to the API, not to the stream | the event times of a trip's two accepts differ by 1 or 2 s. The example sends the two accepts together: both requests are sent before either has an answer, so both conditional writes are under way before either is finished, and the table decides. Exactly one driver must get the trip. Both rows carry the same `received_time`; that marks the pair and is not what makes the accepts concurrent | `later-first`: for 10 of the 20 trips the accept with the later event time is first in the file; the order in the file does not decide who wins (Q020) | `sim/data/SIM03/` and `s3://t00-lake-<account-id>/sim/SIM03/`, laid out as `raw/trip-events/` |
| SIM04 | `trips-day` | batch file | DS01 (the subset); zone ids of DS02 | one CSV file with the trips of zones 48, 161 and 230 completed on 2024-03-13 that have a fare above 0, as rows of `trip_completed` dated 2026-11-22: 18,593 rows (*measured*) | one file a night, arriving at 05:10 UTC | `bad-fare`: 3 of the rows do not have a fare above 0 (one empty, one 0, one negative), so 18,590 load and 3 are rejected | `sim/data/SIM04/` and `s3://t00-lake-<account-id>/sim/SIM04/`, laid out as `raw/trip-exports/`; not generated in this example |
| SIM05 | `raw-30-days` | lake table | DS01 (the subset); zone ids of DS02 | table `trip_events_raw` after 30 days: the events of the 524,629 trips of zones 48, 161 and 230 requested from 2024-03-01 to 2024-03-30 (142,310, 188,010 and 194,309 trips, *measured* 2026-11-19, DuckDB over HTTPS), moved to the 30 days from 2026-10-24 to 2026-11-22: about 1.57 million events, 3 for each trip | one file a minute: 43,200 files in 30 days (our choice); the request of a trip is in the folder of the day it was requested | none; the sizes are a first guess, and we set them so that the count is slow before compaction | `s3://t00-lake-<account-id>/sim/SIM05/`, laid out as `raw/trip-events/`; not generated in this example |

The files of a stream data set (from Checkpoint 2; `uv run python -m sim.generate` writes them):

```
sim/data/SIM01/
├── trip-events/dt=2026-11-23/hour=09/deliveries.jsonl   what the system receives, in the order received
├── trip-events/dt=2026-11-23/hour=10/deliveries.jsonl   late requests and trips completed after 10:00
├── _truth/events.jsonl                                  each event once, as it happened
└── _truth/faults.jsonl                                  each injected fault; never sent to the system
```

Expected answers are computed from `_truth/events.jsonl`, never from the system's output. A few hand-picked
events go in a table inside the example itself, with the fields of part (c) as columns; a data set is for the
cases where the number of events matters.

### (e) Which requirement and which scenario uses each data set

| Data set | Built from | Requirements | Scenarios (feature file: example) |
|---|---|---|---|
| SIM01 | DS01, DS02 | R010, RF010 | `js01_trips_per_zone.feature`: One simulated hour; One simulated hour with 4 requests delivered twice |
| SIM02 | DS01, DS02 | RF020 | `js01_trips_per_zone.feature`: Zone 48 quiet for 10 minutes of a simulated hour |
| SIM03 | DS01, DS02 | R080, RF030 | `trip_assignment.feature`: Twenty trips, two drivers each |
| SIM04 | DS01, DS02 | R040, R050 | `js01_yesterdays_trips.feature`: File for 2026-11-22; File with 3 trips that do not have a fare above 0 |
| SIM05 | DS01, DS02 | RF040 | `js01_yesterdays_trips.feature`: Thirty days of small files, compacted |

R020, R030, R060, R070, R090 and R100 use tables or single events inside their examples and no data set.
