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

## Resources

Every resource is in ca-central-1, has a name that starts with `t00-` (the Glue database uses `t00_lake`), and
carries the tags `Project=436c`, `Team=t00`, `Owner=<name>` (RF050). The scripts are written at Checkpoint 2.

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

Outside our system. We do not create these; our system relies on what the last column says.

| Who | Sends | To | What we rely on |
|---|---|---|---|
| the app's trips service | each trip event | stream `t00-trip-events` | one JSON object as in Data, Event kinds; an event may arrive twice or late; an event is not sent again more than 24 hours after it was first sent (Q030) |
| the app's trips service | each accept, as one request | API `t00-api` | the body holds `event_id`, `driver_id` and `event_time`; the app passes our answer to the driver's phone |
| the app's nightly export | one CSV file with the day's completed trips | `raw/trip-exports/dt=<day>/` in our bucket | the columns are the fields of `trip_completed`; the file arrives by 05:30 UTC |
| the rider's page and the analyst's browser | reads and questions | API `t00-api` | none |

## Data

Three parts: the real data, the events, and the simulated data sets the examples use. On Monday this is text: no
file in `sim/data/` or in the bucket has to exist.

### Sources

| Id | Data set | Link | Rows | Size |
|---|---|---|---|---|
| DS01 | NYC TLC High Volume For-Hire Vehicle trips, March 2024: one row a finished trip | [fhvhv_tripdata_2024-03.parquet](https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-03.parquet) ([trip record page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)) | 21,280,788 (*measured* 2026-11-19, DuckDB) | 0.51 GB, Parquet |
| DS02 | NYC TLC taxi zones: id, borough and name | [taxi_zone_lookup.csv](https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv) | 265 (*measured*) | CSV, 4 columns |

The bucket `t00-lake-<account-id>`, in ca-central-1:

```
s3://t00-lake-<account-id>/
├── source/    DS01 and DS02, copied once
├── raw/       events as received (raw/trip-events/) and the nightly export files (raw/trip-exports/)
├── curated/   completed trips with a fare, rejected rows, and the events compacted to one file a day
└── sim/       the simulated data sets, one folder for each id, laid out as raw/
```

### Event kinds

Every event is one JSON object. Three fields are in every kind:

| Field | Type | Example | Valid values |
|---|---|---|---|
| `event_id` | text | `ev-000412` | the same id again is the same event |
| `event_type` | text | `trip_requested` | one of: `trip_requested`, `trip_accepted`, `trip_completed` |
| `event_time` | UTC time | `2026-11-23T09:01:10Z` | when it happened in the app |

**`trip_requested`**: a rider asked for a trip.

| Field | Type | Example | Valid values |
|---|---|---|---|
| `trip_id` | text | `t-0412` | one id for one trip, the same in all its events |
| `rider_id` | text | `p-00317` | the id of a rider |
| `pickup_zone_id` | whole number | `161` | one of the zone ids of DS02 |
| `dropoff_zone_id` | whole number | `230` | one of the zone ids of DS02 |
| `quoted_fare` | decimal | `27.13` | > 0, in USD |

**`trip_accepted`**: a driver took the trip. The body of an accept sent to the API has the same fields.

| Field | Type | Example | Valid values |
|---|---|---|---|
| `trip_id` | text | `t-0412` | the id of a trip that was requested |
| `driver_id` | text | `d-0046` | the id of a driver |

**`trip_completed`**: the driver closed the trip.

| Field | Type | Example | Valid values |
|---|---|---|---|
| `trip_id` | text | `t-0412` | the id of a trip that was accepted |
| `driver_id` | text | `d-0046` | the id of the driver who was assigned |
| `dropoff_zone_id` | whole number | `230` | one of the zone ids of DS02 |
| `trip_miles` | decimal | `1.38` | >= 0 |
| `trip_time_s` | whole number | `670` | >= 0, in seconds |
| `fare` | decimal | `27.13` | > 0, in USD; otherwise the row is rejected (R050) |
| `driver_pay` | decimal | `20.35` | any amount, in USD |

**`delivery`**: one arrival of an event at our system. It has the fields of the event and:

| Field | Type | Example | Valid values |
|---|---|---|---|
| `received_time` | UTC time | `2026-11-23T09:01:11Z` | not before the event time |

### Simulated data sets

Each set is DS01 rows turned into events, moved to 2026-11-23 or the 30 days before. A fault is not a field of an
event: the system under test is not told.

| Id | Name | Holds | Injected faults | Codes |
|---|---|---|---|---|
| SIM01 | `rush-hour` | one hour of zones 48, 161 and 230 (ids of DS02) from DS01: 837 trips, 2,511 events | `duplicate`: 4 requests delivered twice; `late`: 2 requests received 6 to 10 minutes late | RF010 |
| SIM02 | `quiet-zone` | as SIM01 (from DS01), without its faults and the trips below: 2,331 events | `quiet`: zone 48 has no trips between 09:25 and 09:35 | RF020 |
| SIM03 | `double-accept` | 20 trips of zone 161 from DS01, each with one request and two accepts from different drivers: 60 rows | `later-first`: for 10 trips the later accept is first in the file | R080, RF030 |
| SIM04 | `trips-day` | one CSV file of a day's completed trips of the three zones from DS01: 18,593 rows | `bad-fare`: 3 rows without a fare above 0 | R040 |
| SIM05 | `raw-30-days` | 30 days of events of the three zones from DS01 (524,629 trips), one small file a minute | none | RF040 |
