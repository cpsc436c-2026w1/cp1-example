# Checkpoint 1 example: the rides case

A complete example of what a team hands in for Checkpoint 1 of the CPSC 436C project, for a team "t00" whose
system receives the trip events of a ride-hailing app (the case of lectures 1 to 14). It is built on public trip
records of New York (NYC TLC, High Volume For-Hire Vehicle trips); `docs/design.md`, section Data, says exactly
which, where they live and how the simulated events are made from them.

## What is Checkpoint 1, and what is not

**For Tuesday a team writes text only.** That is the upper part of the table. Tag `cp1` of this repository is
that state: `git checkout cp1` shows it, `git checkout main` comes back.

**The lower part shows where Checkpoint 2 goes** and is here so that the studio can run one worked example: a
generator for three of the five data sets, and code for four of the fourteen rules (R110 checker only, on recorded replies). The other rules stay drafts.

| File | What it is | Due |
|---|---|---|
| `docs/proposal.md` | the proposal as tagged; sections 4 and 5 now point to the design | done |
| `docs/requirements.md` | job stories JS01 to JS04 as headings; under each, requirement lines R010 … in EARS form, each ending with a `[Scenario]` link to its feature file; under Stakeholder input, the feedback IDs RF010 … and RQ010, RQ020 as a list in the same form; one eval entry; assumptions | Tuesday |
| `docs/design.md` | a sketch, workflows, resources with the script that will create each, what is outside the system, and the section Data: our data (DS01 …) in a few sentences, the simulated data for the demos (SIM01 …) as bullets in words, and the event format | Tuesday |
| `features/*.feature` | one feature for what a user gets, tagged with its stories; one `Rule:` for each requirement and testable RF, tagged with its ID; examples with small tables or a data set named by its ID | Tuesday |
| `features/steps/.gitkeep`, `behave.ini` | for a team, an empty folder, so that the dry run works; two display settings. This example also has `features/steps/pickup_steps.py` there, a demonstration of the eval of R110 | Tuesday |
| `tools/check_trace.py` | checks that every ID is defined once and used where it must be | provided |
| `sim/seed/ds01_sample.csv`, `tools/extract_seed.sql` | 837 rows of DS01 that the data sets are built from, and the query that wrote them | Checkpoint 2 |
| `sim/datasets.py`, `sim/generate.py` | the simulated data sets of the design as settings, and the generator that writes them to `sim/data/<id>/` | Checkpoint 2 |
| `src/rides/counting.py`, `src/rides/assign.py` | local code for two things: the count of requests by zone and period, and the accept with a condition | Checkpoint 2 |
| `features/environment.py`, `features/steps/*.py` | what makes the examples of RF010, RF020, RF030 and R110 run | Checkpoint 2 |
| `evals/pickup_place/` | the eval of R110: 10 cases, 30 recorded example replies (written by hand, not a model run), the list of places and a checker | Checkpoint 2 |
| `tests/` | pytest: the checker, with one injected error for each check, the generator's seed, the local code | Checkpoint 2 |
| `DEMO.md` | the order to show all of this in the studio, with commands and their output | |

## Commands

```bash
python3 tools/check_trace.py                      # traceability: 0 problems
uvx behave@1.3.3 --dry-run --no-snippets          # every feature parses (Tuesday's check)
uv run python -m sim.generate                     # write the simulated data sets
uv run behave --no-snippets --tags=@RF010         # a duplicate is counted once
uv run behave --no-snippets --tags=@RF020         # a quiet zone is shown as no data
uv run behave --no-snippets --tags=@RF030         # two drivers, one trip
uvx behave@1.3.3 features/js04_pickup_place.feature   # checker only, recorded replies (R120's example: undefined)
python3 evals/pickup_place/check.py               # the eval's checker alone: per case and the total
DEDUPE=off uv run behave --no-snippets --tags=@RF010   # the duplicate check off: the example fails
uv run pytest -q
```

Nothing here calls AWS or a model. The data is from NYC TLC trip records ([terms](https://www.nyc.gov/main/terms-of-use)).
