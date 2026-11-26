<!-- review: lens=budget-check lens_version=2026-11-26.3 catalog_version=none assistant=Claude Code (claude-opus-5-5) date=2026-11-26 commit=aa22b78 -->

| Question | To look at | Not checked |
|---|---|---|
| BC005 | not checked | the team's budget: this example's slice ran in the course staff's account, not in a team lease |
| BC010 | 1 line | the planned resources have no create or delete command yet |
| BC020 | 2 lines | how often the eval would run live; the delete commands of the planned Glue jobs and their trigger |
| BC030 | 1 line | the lease's Lambda limit for the reserved concurrency the scripts ask for |

## BC010 Things that cost money while nobody uses them (idle resources)

**Look at**

- `docs/design.md:72`, and `docs/design.md:94`
  - **Check:** "your design does not say what your system costs in a month when nobody uses it. Add up every idle
    resource for 30 days. If the total is more than a few dollars, your design should create those resources only
    for runs and demos."
  - **Now:** "| Kinesis data stream, provisioned, 1 shard | `t00-trip-events` | `scripts/stream.py up` | R010, R020,
    RF010, RF050 |", and "What the deployed slice costs while nobody uses it: the stream's shard, 0.0165 USD an
    hour, 11.88 USD for 30 days (price sheet, ca-central-1, 2026-11-18)". The stream is created by
    `scripts/stream.py up` and deleted first by `scripts/teardown.sh` (`scripts/teardown.sh:40`, "aws
    kinesis delete-stream ... --stream-name \"$STREAM\"").
  - **To consider:** the page: "For each resource in your design, say what costs money (the instance, the nodes, the
    stream, the address, the storage) and how your clean-up script stops it after each run: create it for a run,
    then delete it." The design says both for the stream; 11.88 USD for 30 days is more than a few dollars, so the
    stream stays a resource made only for runs and demos.
  - **Team's decision:** "Decision (budget-check BC010, t00-trip-events, PR #3): keep. The stream is the one
    resource of the slice that bills by the hour (0.0165 USD, 11.88 for 30 days); scripts/stream.py up creates it
    for a run or a demo, scripts/teardown.sh deletes it first, and nothing is kept between runs (docs/design.md,
    Resources)." (PR #3, `docs/requirements.md:76`)

## BC020 Costs that grow with each query and each run

**Look at**

- `docs/design.md:91`
  - **Check:** "an EventBridge Scheduler schedule, an EventBridge rule or a Glue trigger still exists after your
    clean-up script ran, and keeps starting work."
  - **Now:** "| Glue job, run every night at 00:30 UTC | `t00-compact-events` | planned: `scripts/compact.py up` |
    RF040, RF050 |". `scripts/teardown.sh` has no delete command for the job or its trigger yet; the design says
    their lines come with them for the final hand-in.
  - **To consider:** the page: "Your clean-up script deletes these first: ... `aws glue delete-trigger --name
    <name>`", and "To list what is left: ... `aws glue get-triggers`". A Glue job "is charged per DPU-hour (0.308
    USD) with a one-minute minimum" (page): one run a night is what RF040's freshness asks for.
  - **Team's decision:** "Decision (budget-check BC020, t00-compact-events, PR #4): later, final hand-in. The
    nightly compaction job and its 00:30 UTC trigger are not created at Checkpoint 2: RF040's example runs on the
    local stand-in (src/rides/compact.py) and is tagged @todo; scripts/compact.py and the delete of the trigger and
    the job in scripts/teardown.sh come with them." (PR #4, `docs/requirements.md:50`)
- `features/js04_pickup_place.feature:27`
  - **Check:** "your LLM calls can use up your team's 5 USD before the demo."
  - **Now:** "Then the pickup place is correct in at least 24 of the 30 runs", an `@eval` example: 10 cases × 3
    repetitions = 30 model calls each time the eval runs live. Today it runs on recorded replies: "REPLIES=live
    would ask the model through the course LLM gateway; it stops at ask_model_live below, which is not written yet"
    (`features/steps/pickup_steps.py:5`).
  - **To consider:** the page: "For each model, multiply the input tokens and the output tokens of one measured
    request by their own rates ..., then by the requests you expect, plus each eval run: cases × repetitions, every
    time you run your tests or push to CI. ... Run evals on demand, not on every push". `docs/design.md`, Cost,
    prices the assistant's messages with assumed tokens (600 input, 20 output); one measured request would replace
    the assumption.

## BC030 What your team's lease refuses

**Look at**

- `docs/design.md:78`
  - **Check:** "your team cannot find everything it created. ... When the lease ends, everything in it is deleted:
    your scripts must be able to create the system again."
  - **Now:** "| IAM role of the counting function: read the stream, write the two tables and its log group |
    `t00-count-requests-fn` | the course staff (not deleted by our scripts; a role costs nothing) | RF050 |", and
    `scripts/counting.py` uses that role by name ("role = os.environ.get(\"LAMBDA_ROLE_ARN\") or
    f\"arn:aws:iam::{account}:role/{n['role']}\"", `scripts/counting.py:85`). No script in `scripts/`
    creates it.
  - **To consider:** the page: "Give every resource the team's name prefix and the course tags, so one list (the
    `cost-and-teardown` recipe's inventory) finds what each member created." In a team lease, a script that creates
    the role (as the recipe streaming-ingestion's `create_role` does) would let the scripts create the whole slice
    again in a new lease.

## Not checked

- **BC005, the team's budget.** A budget is not in the repository, and this example's slice ran in the course
  staff's account. A team checks it with `aws budgets describe-budgets --account-id <id>` (period and limit),
  `aws budgets describe-notifications-for-budget` (the alerts) and `aws budgets describe-subscribers-for-notification`
  (the recipients), or in the console under Budgets. The page gives the console steps and a CloudShell command block
  to create one, right under BC005's Problem.
- **The planned resources** (`docs/design.md:79-92`): no create or delete command yet for `t00-track-trips`,
  `t00-assign-trip`, `t00-trips`, `t00-api`, `t00-read`, `t00-trip-events-to-lake`, `t00-lake-<account-id>`,
  `t00_lake` and its tables, `t00-curate-trips`, `t00-compact-events` and `t00-assistant`. To check again before
  their first deploy.
- **The lease's Lambda limit.** `scripts/counting.py` sets reserved concurrency 1 only when the account keeps 100
  unreserved (`scripts/counting.py:125`); in a lease of 10 it is not set, and one shard read by one batch
  at a time keeps the function at one run. `aws lambda get-account-settings` shows the account's limit.
- **How often the eval would run live**: no CI workflow in the repository.
- **What the run cost on the bill**: the cost is computed from the measured units (`evidence/units.json`,
  `docs/design.md`, Cost), not read in Cost Explorer. The page: open Cost Explorer in the console (**Billing and
  Cost Management → Cost Explorer**) and show daily costs grouped by service; the console view is free.

## Other notes

- RQ010's reply gives an estimate with its rates, not a promise: `docs/design.md`, Cost, one year at the price
  sheet's rates, with the units measured on AWS for the counting path and assumed for the rest.
- The counting function logs one line of counts for each batch, not one for each record
  (`src/rides/count_function.py:91`); measured: 444 bytes a run (`evidence/units.json`).
- The largest yearly line of the design is the counting path's DynamoDB writes: 4 write units a request, a
  transaction of 2 items (`docs/design.md`, Cost; `docs/reviews/well-architected.md`, question 1). It is not the Problem about loading
  a history row by row: each write is a new request from the stream.
- The first run on AWS sent one batch of 4 records before the replays (`evidence/first-batch.txt`).

## Since the last run

first run
