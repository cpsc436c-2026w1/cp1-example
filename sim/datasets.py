"""The simulated data sets of docs/design.md, section Data, Simulated data for the demos, as settings the generator reads.

Same ids as the bullets there; the counts of injected faults match them. Change a number in both places.
SIM04 and SIM05 are described in the design and not generated in this example.
SIM03 holds pairs of accepts; what makes a pair concurrent is how the example sends it (features/steps/assign_steps.py).
"""
from datetime import datetime, timezone

SEED = 436
SEED_ROWS = "sim/seed/ds01_sample.csv"     # 837 rows of DS01: tools/extract_seed.sql wrote it
SEED_START = datetime(2024, 3, 14, 8, 0)   # the sample's hour, New York local time as in DS01
SIM_START = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)   # where that hour is moved to

DATA_SETS = {
    "SIM01": dict(name="rush-hour", kind="event stream", source="DS01",
                  duplicates=4, late=2, late_minutes=(6, 10)),
    "SIM02": dict(name="quiet-zone", kind="event stream", source="DS01",
                  quiet_zone=48, quiet_from="09:25", quiet_to="09:35"),
    "SIM03": dict(name="double-accept", kind="two concurrent writers", source="DS01",
                  zone=161, trips=20, later_first=10),
}

COMMITTED = ("SIM01", "SIM02", "SIM03")    # written to sim/data/ and committed
