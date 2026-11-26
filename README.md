# Project example: the rides case, Checkpoints 1 and 2

A complete example of what a team hands in for the CPSC 436C project, for a team "t00" whose system receives the
trip events of a ride-hailing app (the case of lectures 1 to 14). It is built on public trip records of New York
(NYC TLC, High Volume For-Hire Vehicle trips); `docs/design.md`, section Data, says exactly which, where they live
and how the simulated events are made from them.

Tag `cp1` is the Checkpoint 1 hand-in: text only (`git checkout cp1` shows it). Tag `cp2` is the Checkpoint 2
hand-in: the same text, running, with JS01's counting path deployed on AWS once, measured and deleted.
`DEMO.md` shows both, with the commands and their output.

| File | What it is | Checkpoint |
|---|---|---|
| `docs/proposal.md` | the proposal as tagged; sections 4 and 5 now point to the design | 1 |
| `docs/requirements.md` | job stories JS01 to JS04, requirement lines R010 … in EARS form with `[Scenario]` links; Stakeholder input with a `Reply:` for each RF and RQ (at Checkpoint 2, RQ010 and RQ020 with their answers); one eval entry; assumptions; the team's decisions | 1, 2 |
| `docs/design.md` | sketch, workflows, resources (the deployed ones with their scripts), what is outside the system, Data (DS01, DS02, SIM01 to SIM05, event format), and at Checkpoint 2 Cost (RQ010) and Experiments (RQ020) | 1, 2 |
| `docs/reviews/well-architected.md`, `docs/reviews/budget-check.md` | the Well-Architected review: four questions from the Data Analytics Lens, two of them with a change made; and the report of the budget and sandbox check on this repository | 2 |
| `features/*.feature` | one feature for what a user gets; one `Rule:` for each requirement and testable RF, tagged with its ID | 1 |
| `features/environment.py`, `features/steps/*.py` | the step code: every example runs, on the local code by default and, for JS01's counts, on AWS with `TARGET=aws` | 2 |
| `sim/` | `datasets.py` (the bullets as settings), `generate.py` (seeded, standard library only), `check.py` and `expected.toml` (the files against the bullets' numbers), `replay.py` (the course replayer), `replay_test.py` (RQ020); `data/SIM01` to `SIM04` committed, SIM05 written on demand; `seed/` (DS01 rows, `tools/extract_seed.sql`) | 2 |
| `src/rides/` | the system's code: `counting.py` and `count_function.py` (the deployed function), `aws_slice.py` (the examples' view of AWS), `assign.py`, `curate.py`, `compact.py`, `assistant.py` (local code of the rules not deployed yet), `events.py` (Pydantic models) | 2 |
| `scripts/` | `stream.py`, `counting.py` (create the slice, safe to run again), `teardown.sh` (deletes everything they create), `run_units.py`, `year_cost.py` (the measured units and the cost) | 2 |
| `evidence/` | the run on AWS of 2026-11-26: deploy, tags, the replays at 1, 10 and 50 times SIM01's speed, the examples on AWS, units, teardown | 2 |
| `evals/pickup_place/` | the eval of R110: 10 cases, 30 recorded replies (written by hand, not a model run), places, checker | 1, 2 |
| `tools/check_trace.py` | checks that every ID is defined once and used where it must be (the course's copy) | provided |
| `tests/` | pytest: the checkers with planted errors, the generator, the function with a stand-in for DynamoDB | 2 |

## Commands

```bash
python3 tools/check_trace.py                      # traceability: 0 problems
uvx behave@1.3.3                                  # every example, local code (standard library only)
uv run python -m sim.generate                     # write SIM01 to SIM04 (and SIM05 with: ... sim.generate SIM05)
uv run python sim/check.py                        # every data set against its bullet
uv run pytest -q
# on AWS (a sign-in to the team's account; costs money while the stream exists):
uv run python scripts/stream.py up && uv run python scripts/counting.py up
TARGET=aws uv run behave features/js01_trips_per_zone.feature --tags="not @todo"
uv run python sim/replay_test.py --speed 50
bash scripts/teardown.sh --yes
```

Nothing here calls a model: R110's eval runs on recorded replies. The data is from NYC TLC trip records
([terms](https://www.nyc.gov/main/terms-of-use)).
