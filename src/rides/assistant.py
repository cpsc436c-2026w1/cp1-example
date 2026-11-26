"""What the support agent is shown for a rider's message (R110, R120): local code for the function `t00-assistant`.

The model's reply must be a JSON object with one field, `pickup_place`. The page shows the value when it is a name
on our list of places (evals/pickup_place/places.txt), that the message names no pickup place for `null`, that it
names more than one for "more than one" (R120), and no answer for anything else. The function and the call through
the course LLM gateway are not deployed at Checkpoint 2 (docs/design.md, Resources).
"""
import json

MORE_THAN_ONE = "more than one"
NO_ANSWER = "no answer"


def shown(reply: str, places: list[str]):
    """The place, None (no pickup place), MORE_THAN_ONE, or NO_ANSWER for a reply the page cannot show."""
    try:
        value = json.loads(reply)
    except json.JSONDecodeError:
        return NO_ANSWER
    if not isinstance(value, dict) or set(value) != {"pickup_place"}:
        return NO_ANSWER
    place = value["pickup_place"]
    if place is None or place == MORE_THAN_ONE or place in places:
        return place
    return NO_ANSWER
