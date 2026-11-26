# Design

Team t00, the rides case. Sections Workflows and Sketch were sections 4 and 5 of the proposal.

## Sketch

![Sketch of the system](sketch.svg)

Source: [sketch.puml](sketch.puml) (PlantUML). Every box is a row in [Resources](#resources), or in the table of what
is outside our system.

## Workflows

Each workflow names the IDs it serves in brackets after its name, and the components it uses; every component is a row in
[Resources](#resources).

### Counting requests [R010, R020, RF010, RF020]

The trips service sends each trip event to the stream. The counting function counts requests by pickup zone in
5-minute periods and stores each count within 60 s of the period's end (p95); a late request corrects the count of its
period. It writes each event's id together with the count, so an event delivered twice is counted once.

Components: `t00-trip-events`, `t00-count-requests`, `t00-zone-counts`, `t00-seen-events`

### Assigning trips [R070, R080, R090, R100, RF030]

The tracking function keeps each trip current from the stream. A driver's accept comes to the API as one request;
the assign function makes one conditional write, so only one of two accepts for a trip is answered `assigned`,
within 2 s (p99).

Components: `t00-trip-events`, `t00-track-trips`, `t00-api`, `t00-assign-trip`, `t00-trips`

### Reading counts and trips [R030, R090, R100, RF020]

The read function answers the rider's and the analyst's pages through the API. A zone and period without a count
is shown as no data, not as 0.

Components: `t00-api`, `t00-read`, `t00-zone-counts`, `t00-trips`

### Lake and nightly jobs [R040, R050, RF040]

Firehose writes the stream to the bucket about once a minute, and at 00:30 UTC the compaction job rewrites the day
before as one Parquet file. The curation job loads the nightly export's completed trips with a fare above 0 within
30 minutes of the file's arrival (p95) and sets the other rows aside.

Components: `t00-trip-events-to-lake`, `t00-lake-<account-id>`, `t00_lake`, `t00-compact-events`,
`trip_events_compacted`, `t00-curate-trips`, `trips_curated`, `trips_rejected`

### Pickup place of a message [R110, R120]

The support agent's page sends a rider's message through the API to the assistant function. The function sends it
to the model through the course LLM gateway as the user message, with our list of places in the system prompt and
the output format a JSON object with one field, `pickup_place`. The function shows the value if it is a name on the
list, `null`, or `"more than one"` when the message names more than one pickup place; any other reply is shown as no
answer.

Components: `t00-api`, `t00-assistant`

## Resources

Every resource is in ca-central-1, has a name that starts with `t00-` (the Glue database is `t00_lake`, and its tables
are named without the prefix), and carries the tags `Project=436c`, `Team=t00`, `Owner=course` (RF050). At
Checkpoint 2 the counting path of JS01 is deployed: the first six rows, created by `scripts/stream.py up` and
`scripts/counting.py up`, and deleted by `scripts/teardown.sh --yes`, the stream first. They exist only for a run or
a demo; between runs nothing is kept. The other rows are planned: their scripts, and their lines in
`scripts/teardown.sh`, come with them for the final hand-in (PR #3).

| Resource | Name | Created by | IDs |
|---|---|---|---|
| Kinesis data stream | `t00-trip-events` | `scripts/stream.py up` | R010, R020, RF010, RF050 |
| Lambda function, Python 3.12 on arm64, 128 MB, at most 1 run at a time | `t00-count-requests` | `scripts/counting.py up` | R010, R020, RF010, RF020, RF050 |
| Lambda event source mapping, batches of up to 100 records or 1 s, 3 retries | `t00-trip-events` to `t00-count-requests` | `scripts/counting.py up` | R010, R020, RF010 |
| DynamoDB table, on demand, key `zone_id`, `period_start` | `t00-zone-counts` | `scripts/counting.py up` | R010, R020, R030, RF020, RF050 |
| DynamoDB table, on demand, key `event_id`, items expire after 24 hours | `t00-seen-events` | `scripts/counting.py up` | RF010, RF050 |
| CloudWatch log group, kept 7 days | `/aws/lambda/t00-count-requests` | `scripts/counting.py up` | RF050 |
| IAM role of the counting function: read the stream, write the two tables and its log group | `t00-count-requests-fn` | the course staff (not deleted by our scripts; a role costs nothing) | RF050 |
| Lambda function | `t00-track-trips` | planned: `scripts/assignment.py up` | R070, R090, R100, RF050 |
| Lambda function | `t00-assign-trip` | planned: `scripts/assignment.py up` | R070, R080, RF030, RF050 |
| DynamoDB table | `t00-trips` | planned: `scripts/assignment.py up` | R070, R080, R090, R100, RF030, RF050 |
| API Gateway HTTP API | `t00-api` | planned: `scripts/api.py up` | R030, R070, R080, R090, R100, R110, R120, RF050 |
| Lambda function | `t00-read` | planned: `scripts/api.py up` | R030, R090, R100, RF020, RF050 |
| Firehose stream | `t00-trip-events-to-lake` | planned: `scripts/lake.py up` | RF040, RF050 |
| S3 bucket | `t00-lake-<account-id>` | planned: `scripts/lake.py up` | R040, R050, RF040, RF050 |
| Glue database | `t00_lake` | planned: `scripts/lake.py up` | R040, R050, RF040, RF050 |
| Glue table, in `t00_lake` | `trips_curated` | planned: `scripts/curate.py up` | R040, R050, RF050 |
| Glue table, in `t00_lake` | `trips_rejected` | planned: `scripts/curate.py up` | R050, RF050 |
| Glue job | `t00-curate-trips` | planned: `scripts/curate.py up` | R040, R050, RF050 |
| Glue table, in `t00_lake` | `trip_events_compacted` | planned: `scripts/compact.py up` | RF040, RF050 |
| Glue job, run every night at 00:30 UTC | `t00-compact-events` | planned: `scripts/compact.py up` | RF040, RF050 |
| Lambda function (the assistant) | `t00-assistant` | planned: `scripts/assistant.py up` | R110, R120, RF050 |

What the deployed slice costs while nobody uses it: the stream's shard, 0.0165 USD an hour, 11.88 USD for 30 days
(price sheet, ca-central-1, 2026-11-18); the tables and the log group bill only what they store (a few kilobytes
after a run), and the function and its mapping only when records arrive. So the stream is created for a run and
deleted after it ([Decisions](requirements.md#decisions)).

Outside our system. We do not create these; our system relies on what the last column says.

| Who | Sends | To | What we rely on |
|---|---|---|---|
| the app's trips service | each trip event | stream `t00-trip-events` | one JSON object with the event fields of Data; an event may arrive twice or late; an event is not sent again more than 24 hours after it was first sent (Q030) |
| the app's trips service | each accept, as one request | API `t00-api` | the body holds `event_id`, `trip_id`, `driver_id` and `event_time`; the app passes our answer to the driver's phone |
| the app's nightly export | one CSV file with the day's completed trips | `raw/trip-exports/dt=<day>/` in our bucket | the columns are the fields of `trip_completed`; the file arrives by 05:30 UTC |
| the rider's page, the analyst's browser and the support agent's page | reads and rider messages | API `t00-api` | none |
| the course LLM gateway | the model's reply to each message | function `t00-assistant` | the team's keys share one pool of 7.25 CAD (5 USD); 120 requests a minute per key |

## Data

### Our data

DS01 is the High Volume For-Hire Vehicle trip records of the NYC Taxi and Limousine Commission: one row for each
finished trip, one [Parquet file a month](https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-03.parquet)
over HTTPS ([trip record page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)). We use the Uber trips
picked up in Manhattan in March 2024 (*our choice*): 6,045,943 of the month's 21,280,788 rows, 0.20 GB as Parquet
(*measured* 2026-11-19, DuckDB). DS02, the TLC [taxi zone lookup](https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv),
gives the borough and name of each of its 265 zones (*measured* 2026-11-20, DuckDB). The system's events are simulated
from DS01 rows of zones 48, 161 and 230 (*our choice*); each bullet below says which days of DS01 it uses and the
dates they are moved to (*our choice*).

### Simulated data for the demos

- **SIM01 Rush hour** [RF010] One morning hour from DS01: the 837 trips requested in zones 48, 161 and 230 on
  2024-03-14 between 08:00 and 09:00 New York time, moved to 09:00 to 10:00 UTC on 2026-11-23: 304, 191 and 342
  trips, 2,511 events sent as 2,515 deliveries: 4 requests arrive twice, and 2 arrive 6 to 10 minutes late.
- **SIM02 Quiet zone** [RF020] SIM01's hour from DS01 without its 6 faults, and without the 60 trips of zone 48
  requested between 09:25 and 09:35: 777 trips (244, 191 and 342 in zones 48, 161 and 230), 2,331 events.
- **SIM03 Double accept** [R080, RF030] The first 20 trips of zone 161 in SIM01's hour from DS01, at the same times:
  60 events, 20 requests and 40 accepts. Each trip is accepted by two drivers at the same moment; for 10 of the 20
  trips the later accept is first in the file.
- **SIM04 Trips day** [R040] One day's file of completed trips from DS01: the 19,074 trips requested in the three
  zones on 2024-03-14 (*measured* 2026-11-20, DuckDB), moved to 2026-11-22, and 3 rows added with a bad fare: 1
  without a fare, 1 with a fare of 0 and 1 with a negative fare. 19,077 rows.
- **SIM05 Thirty days** [RF040] 30 days of requests from DS01: the 524,629 trips requested in the three zones from
  2024-03-01 to 2024-03-30 (142,310, 188,010 and 194,309 in zones 48, 161 and 230, *measured* 2026-11-20, DuckDB),
  moved to 2026-10-24 to 2026-11-22, one `trip_requested` event each, as one small file for each minute of receipt:
  42,797 files. The minute and the pickup zone of each request come from DS01; its second, rider, dropoff zone and
  quoted fare are made up (*our choice*). It does not have injected faults. (PR #5)

**Event format** (each delivery also has `received_time`, set when the event arrives; the field types are the Pydantic
models of `src/rides/events.py`, every time in UTC written like `2026-11-23T09:00:00Z`; PR #5):

- `trip_requested`: `event_id`, `trip_id`, `rider_id`, `pickup_zone_id`, `dropoff_zone_id`, `quoted_fare`, `event_time`
- `trip_accepted`: `event_id`, `trip_id`, `driver_id`, `event_time` (also the body of an accept sent to the API)
- `trip_completed`: `event_id`, `trip_id`, `driver_id`, `dropoff_zone_id`, `trip_miles`, `trip_time_s`, `fare`,
  `driver_pay`, `event_time`; a row of the nightly export has the same fields without `event_id` (SIM04)

From a DS01 row come the request time, the pickup and dropoff zones, `trip_miles`, `trip_time_s`, `fare` (also the
request's `quoted_fare`) and `driver_pay`. DS01 does not have riders, drivers or accepts, so the generator makes up
the rest (*our choice*): `event_id`, `trip_id`, `rider_id` and `driver_id`; the accept 3 to 15 s after the request;
the completion 5 minutes plus the trip time after the accept; and `received_time`, 1 s after the event unless a
bullet says otherwise. The rider messages of R110 and R120 are written by the team.
