"""Yesterday's completed trips in one table (R040, R050).

Local code for the job `t00-curate-trips`: when the file of a day's completed trips arrives, each row with a fare
above 0 goes to table `trips_curated`, and each other row to `trips_rejected` with the reason. `Lake` stands in for
the two Glue tables (partitioned by the file's day); on AWS the same rule runs in the Glue job, which is not
deployed at Checkpoint 2 (docs/design.md, Resources). Standard library only.
"""
NO_FARE, NOT_ABOVE_0 = "no fare", "fare not above 0"


def reason(row: dict) -> str | None:
    """Why a row is left out of trips_curated, or None when its fare is above 0."""
    fare = row.get("fare")
    if fare in (None, ""):
        return NO_FARE
    return None if float(fare) > 0 else NOT_ABOVE_0


class Lake:
    """trips_curated and trips_rejected: the rows of each day's file."""

    def __init__(self):
        self.curated: dict[str, list[dict]] = {}
        self.rejected: dict[str, list[dict]] = {}

    def load_file(self, day: str, rows: list[dict]) -> tuple[int, int]:
        """One run of the job on the file of `day`. A second run of the same file replaces that day: no row twice."""
        self.curated[day] = [r for r in rows if reason(r) is None]
        self.rejected[day] = [{**r, "reason": reason(r)} for r in rows if reason(r) is not None]
        return len(self.curated[day]), len(self.rejected[day])
