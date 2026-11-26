# Well-Architected review

Team t00, the rides case, Checkpoint 2. Our first slice is JS01's counting path: a Kinesis stream, a Lambda function
and two DynamoDB tables, fed by a stream of trip events. It is a streaming slice, so the questions come from the
[Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html), with the
[Serverless Applications Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html)
for what it says about a function that reads a stream. We read the lens pages through the AWS Knowledge server on
2026-11-26. Questions 1 and 2 led to changes made for this checkpoint; `docs/design.md` shows them.

## 1. Reliability: a batch that fails, and a request delivered twice

**Question:** BP 6.4, "Automate the recovery of analytics and ETL job failures"
([Data Analytics Lens, 6 – Design resilience for analytics workload](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/design-principle-6.html)).
The Serverless Applications Lens adds, for stream processing, that duplicated records may occur and that consumers
need both retries and idempotency, with Lambda's maximum retry attempts, maximum record age and bisect batch on
function error ([Streaming processing](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/streaming-processing.html),
[Failure management](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/failure-management.html)).

**Now:** at Checkpoint 1 the design said that the function "writes each event's id together with the count"
(`git show cp1:docs/design.md`, line 21) and nothing about a failed batch. Two separate writes, the id and then the
count, would leave a request seen and not counted when the function fails between them.

**Risk:** a throttled write in the middle of a batch makes Lambda send the whole batch again. With two separate
writes, the requests before the failure are counted again, or a request is marked seen and never counted: the
analyst sends drivers to a zone by a count that is off, and RF010 ("counted exactly once") fails without anyone
seeing it. With Lambda's default retries (until the record expires), one bad record also stops every count for
24 hours.

**Change (made, PR #6):** the id and the count are written in one DynamoDB transaction, with the condition that the id is
new (`src/rides/count_function.py`, lines 51 to 62); a record that fails is reported by its sequence number, and the
batch stops there (`src/rides/count_function.py`, line 90); the mapping splits a failing batch, retries at most 3
times and gives up records older than an hour (`scripts/counting.py`, lines 100 to 102). The test
`tests/test_slice.py::test_a_batch_sent_again_after_a_failure_counts_nothing_twice` fails a write in the middle of a
batch and sends the batch again: every request is counted once. `docs/design.md`, Workflows, Counting requests, says
so. The cost: a transaction uses 2 write units an item, so a counted request uses 4 write units, not 2 (measured,
`evidence/units.json`); over a year that is the largest line of [Cost](../design.md#cost). Still open: a record that
fails 3 times is given up and only its sequence number is logged; a failure destination (an SQS queue) would keep
it. Later, for the final hand-in.

## 2. Cost: the stream's capacity mode

**Question:** BP 14.1, "Evaluate the infrastructure usage patterns then choose payment options accordingly"
([Data Analytics Lens, 14 – Use optimal pricing models based on infrastructure usage patterns](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/design-principle-14.html)).

**Now:** the Checkpoint 1 design named a Kinesis data stream without a capacity mode (`git show cp1:docs/design.md`,
line 67). The rate is known from DS01: the whole subset sends about 6.8 events a second (195,030 trips a day, three
events each), and the replay at 50 times SIM01's speed about 27 a second (`evidence/rq020-x50/summary.json`).

**Risk:** a stream on demand bills 0.048 USD an hour while it exists, a provisioned shard 0.0165 (price sheet,
ca-central-1, 2026-11-18): 8.06 against 2.77 USD a week, from a team budget of 30 USD. Left on until the final
hand-in on 15 December (456 hours), the on-demand stream alone would cost 21.89 USD, the provisioned shard 7.52.

**Change (made, PR #6):** the stream is provisioned with 1 shard (`scripts/stream.py`, line 22): one shard takes 1,000
records a second, far above our rate, so no resharding is needed. It is created for a run and deleted first by
`scripts/teardown.sh` (line 39); the decision to keep it in the design is under
[Decisions](../requirements.md#decisions). `docs/design.md`, Resources, first row.

## 3. Operational excellence: a feed that stops

**Question:** BP 1.2, "Monitor operational metrics of data processing jobs and the availability of source data",
suggestion 1.2.1, "Alert when new data has not arrived or become available within the expected time"
([Data Analytics Lens, best practice 1.2](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/best-practice-1.2---monitor-operational-metrics-of-data-processing-jobs-and-the-availability-of-source-data..html)).

**Now:** RF020 shows a zone and period without events as `no data` (`docs/requirements.md`, line 47), and the slice
has no alarm: the function writes one log line of counts for each batch (`src/rides/count_function.py`, line 91),
and nobody reads it.

**Risk:** when the trips service stops sending, every zone shows `no data`, which is also what a quiet zone shows
(SIM02). The analyst cannot tell an empty zone from a broken feed, the reason RF020 was asked for.

**Change:** none at this checkpoint. Planned for the final hand-in, with the read function: an alarm when the stream
receives no record for 5 minutes in the hours the app runs (Kinesis `IncomingRecords`), and one on the mapping's
`IteratorAge` (the consumer falling behind). An alarm costs 0.10 USD a month (price sheet).

## 4. Security: who may write the counts

**Question:** BP 4.1, "Allow data owners to determine which people or systems can access data in analytics and
downstream workloads", suggestion 4.1.2, a permission matrix of users and roles
([Data Analytics Lens, best practice 4.1](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/best-practice-4.1---allow-data-owners-to-determine-which-people-or-systems-can-access-data-in-analytics-and-downstream-workloads..html)).

**Now:** the function runs with its own role, `t00-count-requests-fn` (`scripts/counting.py`, line 85): it may read
the stream `t00-trip-events`, put, update and check items of `t00-zone-counts` and `t00-seen-events`, and write its
own log group; nothing else. The examples and the replay test write to the stream and read the tables with the
team's sign-in.

| Who | Stream `t00-trip-events` | `t00-zone-counts` | `t00-seen-events` |
|---|---|---|---|
| function `t00-count-requests` (role `t00-count-requests-fn`) | read | write | write |
| team members (scripts, examples, replay test) | write | read, empty between runs | read, empty between runs |
| the read function `t00-read` (planned) | none | read | none |

**Risk:** a mistake in the function cannot reach another table or stream; a team member's sign-in can change the
counts by hand.

**Change:** none. When the read function comes (final hand-in) it gets its own role that only reads
`t00-zone-counts`.
