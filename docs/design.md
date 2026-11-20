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
5-minute periods and stores each count within 60 s of the period's end (p95); a late request corrects the count of its
period. It writes each event's id together with the count, so an event delivered twice is counted once.

Components: `t00-trip-events`, `t00-count-requests`, `t00-zone-counts`, `t00-seen-events`

### Assigning trips · R070, R080, R090, R100, RF030

The tracking function keeps each trip current from the stream. A driver's accept comes to the API as one request;
the assign function makes one conditional write, so only one of two accepts for a trip is answered `assigned`,
within 2 s (p99).

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

### Pickup place of a message · R110

The support agent's page sends a rider's message through the API to the assistant function. The function sends it
to the model through the course LLM gateway as the user message, with our list of places in the system prompt and
the output format a JSON object with one field, `pickup_place`. The function shows the value if it is a name on the
list or `null`; any other reply is shown as no answer.

Components: `t00-api`, `t00-assistant`

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
| API Gateway HTTP API | `t00-api` | `scripts/api.py up` | R030, R070, R080, R090, R100, R110 |
| Lambda function | `t00-read` | `scripts/api.py up` | R030, R090, R100, RF020 |
| Firehose stream | `t00-trip-events-to-lake` | `scripts/lake.py up` | RF040 |
| S3 bucket | `t00-lake-<account-id>` | `scripts/lake.py up` | R040, R050, RF040 |
| Glue database and tables | `t00_lake` | `scripts/lake.py up` | R040, R050, RF040 |
| Glue job | `t00-curate-trips` | `scripts/curate.py up` | R040, R050 |
| Glue job, run every night at 00:30 UTC | `t00-compact-events` | `scripts/compact.py up` | RF040 |
| Lambda function (the assistant) | `t00-assistant` | `scripts/assistant.py up` | R110 |

Outside our system. We do not create these; our system relies on what the last column says.

| Who | Sends | To | What we rely on |
|---|---|---|---|
| the app's trips service | each trip event | stream `t00-trip-events` | one JSON object with the event fields of Data; an event may arrive twice or late; an event is not sent again more than 24 hours after it was first sent (Q030) |
| the app's trips service | each accept, as one request | API `t00-api` | the body holds `event_id`, `driver_id` and `event_time`; the app passes our answer to the driver's phone |
| the app's nightly export | one CSV file with the day's completed trips | `raw/trip-exports/dt=<day>/` in our bucket | the columns are the fields of `trip_completed`; the file arrives by 05:30 UTC |
| the rider's page, the analyst's browser and the support agent's page | reads and rider messages | API `t00-api` | none |
| the course LLM gateway | the model's reply to each message | function `t00-assistant` | for each key at most 2 CAD and 120 requests a minute |

## Data

### Our data

DS01 is the High Volume For-Hire Vehicle trip records of the NYC Taxi and Limousine Commission: one row for each
finished trip, one [Parquet file a month](https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-03.parquet)
over HTTPS ([trip record page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)). We use the Uber trips
picked up in Manhattan in March 2024: 6,045,943 of the month's 21,280,788 rows, 0.20 GB as Parquet (*measured*
2026-11-19, DuckDB). DS02, the TLC [taxi zone lookup](https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv),
gives the borough and name of each of its 265 zones. The system's events are simulated from DS01 rows of zones 48,
161 and 230, with their times moved to 2026-11-23.

### Simulated data for the demos

- **SIM01 Rush hour.** One morning hour in zones 48, 161 and 230, taken from the real trips (DS01): about 840 trips.
  4 requests arrive twice and 2 arrive 6 to 10 minutes late. Shows RF010.
- **SIM02 Quiet zone.** The same hour from DS01 without those faults, and zone 48 has no trips between 09:25 and
  09:35. Shows RF020.
- **SIM03 Double accept.** 20 trips of zone 161 from DS01, each accepted by two drivers at the same moment; for 10
  of them the later accept is first in the file. Shows R080 and RF030.
- **SIM04 Trips day.** One day's file of completed trips in the three zones from DS01: 18,593 rows, 3 of them
  without a fare above 0. Shows R040.
- **SIM05 Thirty days.** 30 days of events in the three zones from DS01, about 525,000 trips, as one small file a
  minute. Shows RF040.

**Event format** (each delivery also has `received_time`, set when the event arrives):

- `trip_requested`: `event_id`, `trip_id`, `pickup_zone_id`, `event_time`
- `trip_accepted`: `event_id`, `trip_id`, `driver_id`, `event_time` (also the body of an accept sent to the API)
- `trip_completed`: `trip_id`, `driver_id`, `dropoff_zone_id`, `trip_miles`, `trip_time_s`, `fare`, `driver_pay`,
  `event_time`
