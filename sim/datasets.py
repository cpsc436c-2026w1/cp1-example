"""The simulated data sets of docs/design.md, section Data, Simulated data for the demos, as settings the generator reads.

Same ids as the bullets there. The numbers each bullet states are checked apart from these settings, in
sim/expected.toml (sim/check.py): change a number here, then the bullet and expected.toml with it.
SIM03 holds pairs of accepts; what makes a pair concurrent is how the example sends it (features/steps/assign_steps.py).
SIM05 is 42,797 files: it is written on demand (`uv run python -m sim.generate SIM05`, or the first example that
names it) and not committed (.gitignore).
"""
from datetime import date, datetime, timezone

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
    "SIM04": dict(name="trips-day", kind="daily file", source="DS01",
                  seed_rows="sim/seed/ds01_trips_day.csv.gz",          # 19,074 rows: tools/extract_seed.sql
                  seed_day=date(2024, 3, 14), day=date(2026, 11, 22),
                  arrives="2026-11-23T05:10:00Z",                     # the export's file, the morning after
                  bad_fares=[None, 0.0, -4.5]),                       # missing, 0, negative: one row each
    "SIM05": dict(name="raw-30-days", kind="minute files", source="DS01",
                  seed_rows="sim/seed/ds01_requests_by_minute.csv.gz",  # requests by minute and zone
                  seed_first=date(2024, 3, 1), first=date(2026, 10, 24), days=30),
}

COMMITTED = ("SIM01", "SIM02", "SIM03", "SIM04")    # written to sim/data/ and committed; SIM05 is not
