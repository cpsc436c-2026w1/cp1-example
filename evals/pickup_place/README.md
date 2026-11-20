# Eval pickup-place (R110)

> **Only a demonstration.** The step code here (`features/steps/pickup_steps.py`) shows how an LLM eval runs in behave. You do not write step code for Checkpoint 1: there, the eval is the `## Evals` entry and the `@eval` example, checked with `behave --dry-run`.

The eval of requirement R110 in `docs/requirements.md` (section Evals): does the assistant find the pickup place in
a rider's message, or `null` when the message does not name one?

| File | What it is |
|---|---|
| `cases.jsonl` | 10 rider messages written by the team, each with its reference value: 7 name a pickup place, 3 do not (case 8 names only a destination) |
| `places.txt` | our list of places; every reference value is a name on it, or `null` |
| `replies_recorded.jsonl` | 30 replies, 3 for each case. **Recorded examples, written by hand, not a model run**: they show the checker and the gate. Four are wrong on purpose: text around the JSON (case 3), the destination in place of the pickup (case 4, case 8), a second field (case 9) |
| `check.py` | the checker: a run is correct when its reply is a JSON object with exactly one field, `pickup_place`, whose value equals the reference value. Standard library only, no model call |

The gate is the `@eval` example in `features/js04_pickup_place.feature`; its steps, in
`features/steps/pickup_steps.py`, check the numbers they name against the files (10 cases, 3 replies for each,
30 runs) and run the checker. `REPLIES=recorded` (the default) reads `replies_recorded.jsonl`. `REPLIES=live` stops
at `ask_model_live`, where the call through the course LLM gateway goes: it is not written yet, because a live run
spends money and waits for the instructor's go.

Output below is pasted from runs on 2026-11-20, branch `main`.

## Checker alone

```
$ python3 evals/pickup_place/check.py
replies: replies_recorded.jsonl, 30 lines (recorded example, written by hand)
case  reference                 correct  wrong runs
   1  "JFK Terminal 4"          3 of 3   
   2  "Penn Station"            3 of 3   
   3  "Grand Central Terminal"  2 of 3   run 1: not JSON
   4  "Times Square"            2 of 3   run 2: pickup_place is "LaGuardia Terminal B"
   5  "Barclays Center"         3 of 3   
   6  "LaGuardia Terminal B"    3 of 3   
   7  "Yankee Stadium"          3 of 3   
   8  null                      2 of 3   run 2: pickup_place is "Penn Station"
   9  null                      2 of 3   run 3: not exactly one field pickup_place
  10  null                      3 of 3   
pickup place correct in 26 of 30 runs (accuracy 0.87)
```

## Feature on the recorded replies

```
$ uvx behave@1.3.3 features/js04_pickup_place.feature
USING RUNNER: behave.runner:Runner
@JS04 @assistant
Feature: Pickup place of a rider's message # features/js04_pickup_place.feature:2
  Covers JS04 (support agent) in a system that includes the assistant, our extension. The assistant sends the
  rider's message to the model as the user message; the output format is a JSON object with one field,
  pickup_place: a name from evals/pickup_place/places.txt, or null when the message names no pickup place.
  Step code: this example repository has step code for this feature only, to show how an LLM eval runs in behave.
  You do not write step code for Checkpoint 1.
    Example: Message that names a pickup place                                                  # features/js04_pickup_place.feature:12
      Given the rider message "I'm waiting outside JFK Terminal 4, door 6. Where is my driver?" # features/steps/pickup_steps.py:43
      When the support agent opens the message                                                  # features/steps/pickup_steps.py:48
      Then the pickup place is "JFK Terminal 4"                                                 # features/steps/pickup_steps.py:57

    Example: Message that names only a destination                                                    # features/js04_pickup_place.feature:17
      Given the rider message "Take me to Penn Station. I haven't decided where to be picked up yet." # features/steps/pickup_steps.py:43
      When the support agent opens the message                                                        # features/steps/pickup_steps.py:48
      Then the system says that the message names no pickup place                                     # features/steps/pickup_steps.py:62

    @eval
    Example: Eval of pickup places                                   # features/js04_pickup_place.feature:23
      Given the 10 cases of the eval "pickup-place"                  # features/steps/pickup_steps.py:67
      When the model that the system uses answers each case 3 times  # features/steps/pickup_steps.py:74
      Then the pickup place is correct in at least 24 of the 30 runs # features/steps/pickup_steps.py:86

1 feature passed, 0 failed, 0 skipped
1 rule passed, 0 failed, 0 skipped
3 scenarios passed, 0 failed, 0 skipped
9 steps passed, 0 failed, 0 skipped
Took 0min 0.000s
```

## Gate fails below 24 of 30

Case 6's three replies changed to `{"pickup_place": "LGA Terminal B"}` (a name that is not on the list), then put
back:

```
$ uvx behave@1.3.3 features/js04_pickup_place.feature        # from the gate on
      Then the pickup place is correct in at least 24 of the 30 runs # features/steps/pickup_steps.py:86
      ASSERT FAILED: correct in 23 of 30 runs, at least 24 needed
      case  reference                 correct  wrong runs
         1  "JFK Terminal 4"          3 of 3   
         2  "Penn Station"            3 of 3   
         3  "Grand Central Terminal"  2 of 3   run 1: not JSON
         4  "Times Square"            2 of 3   run 2: pickup_place is "LaGuardia Terminal B"
         5  "Barclays Center"         3 of 3   
         6  "LaGuardia Terminal B"    0 of 3   run 1: pickup_place is "LGA Terminal B"; run 2: pickup_place is "LGA Terminal B"; run 3: pickup_place is "LGA Terminal B"
         7  "Yankee Stadium"          3 of 3   
         8  null                      2 of 3   run 2: pickup_place is "Penn Station"
         9  null                      2 of 3   run 3: not exactly one field pickup_place
        10  null                      3 of 3   
      pickup place correct in 23 of 30 runs (accuracy 0.77)



Failing scenarios:
  features/js04_pickup_place.feature:23  Eval of pickup places

0 features passed, 1 failed, 0 skipped
0 rules passed, 1 failed, 0 skipped
2 scenarios passed, 1 failed, 0 skipped
8 steps passed, 1 failed, 0 skipped
```

The threshold in the feature changed to 27, then put back:

```
$ uvx behave@1.3.3 features/js04_pickup_place.feature        # from the gate on
      Then the pickup place is correct in at least 27 of the 30 runs # features/steps/pickup_steps.py:86
      ASSERT FAILED: correct in 26 of 30 runs, at least 27 needed
      case  reference                 correct  wrong runs
         1  "JFK Terminal 4"          3 of 3   
         2  "Penn Station"            3 of 3   
         3  "Grand Central Terminal"  2 of 3   run 1: not JSON
         4  "Times Square"            2 of 3   run 2: pickup_place is "LaGuardia Terminal B"
         5  "Barclays Center"         3 of 3   
         6  "LaGuardia Terminal B"    3 of 3   
         7  "Yankee Stadium"          3 of 3   
         8  null                      2 of 3   run 2: pickup_place is "Penn Station"
         9  null                      2 of 3   run 3: not exactly one field pickup_place
        10  null                      3 of 3   
      pickup place correct in 26 of 30 runs (accuracy 0.87)



Failing scenarios:
  features/js04_pickup_place.feature:23  Eval of pickup places

0 features passed, 1 failed, 0 skipped
0 rules passed, 1 failed, 0 skipped
2 scenarios passed, 1 failed, 0 skipped
8 steps passed, 1 failed, 0 skipped
```

`REPLIES=live` stops without a call:

```
$ REPLIES=live uvx behave@1.3.3 features/js04_pickup_place.feature
      NotImplementedError: REPLIES=live: the call through the course LLM gateway is not written yet
```

## Checks of the whole repository

```
$ uvx behave@1.3.3 --dry-run --no-snippets              # last lines: the error and the 30 undefined steps are draft rules (as on main)
0 features passed, 0 failed, 0 skipped, 4 untested
0 rules passed, 0 failed, 1 error, 0 skipped, 12 untested
0 scenarios passed, 0 failed, 1 error, 0 skipped, 19 untested
0 steps passed, 0 failed, 0 skipped, 30 undefined, 46 untested
Took 0min 0.000s
$ python3 tools/check_trace.py                          # last line
27 codes and data ids, 0 problems
$ uv run pytest -q
35 passed in 1.96s
```
