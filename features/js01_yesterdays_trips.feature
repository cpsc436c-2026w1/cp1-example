@JS01
Feature: Yesterday's completed trips in one table
  Covers the second part of JS01 (operations analyst): each morning, yesterday's completed trips with a fare above 0
  loaded into one table.
  A simulated data set is named by its id and described in docs/design.md, section Data.
  Each example starts with tables trips_curated and trips_rejected empty.

  @R040
  Rule: When the file of a day's completed trips arrives, the system shall load each row that has a fare above 0 into table trips_curated

    Example: File for 2026-11-22
      Given the simulated data set SIM04 "trips-day"
      When the file for 2026-11-22 arrives at 2026-11-23T05:10:00Z
      Then by 2026-11-23T05:30:00Z table trips_curated has 19074 rows for 2026-11-22

  @R050
  Rule: If a completed trip in the file has a fare that is missing, 0 or negative, then the system shall leave it out of trips_curated and write it to table trips_rejected with the reason

    Example: File with a missing, a zero and a negative fare
      Given a file of completed trips with these rows:
        | trip_id | driver_id | dropoff_zone_id | trip_miles | trip_time_s | fare  | driver_pay | event_time           |
        | t-0401  | d-0046    | 68              | 0.86       | 462         | 9.11  | 6.56       | 2026-11-22T12:11:21Z |
        | t-0402  | d-0131    | 230             | 1.62       | 731         |       | 31.49      | 2026-11-22T14:30:00Z |
        | t-0403  | d-0007    | 161             | 2.40       | 905         | 0.00  | 12.80      | 2026-11-22T16:02:10Z |
        | t-0404  | d-0188    | 48              | 0.95       | 388         | -4.50 | 5.47       | 2026-11-22T18:45:33Z |
      When the file arrives at 2026-11-23T05:10:00Z
      Then by 2026-11-23T05:30:00Z table trips_curated has 1 row for 2026-11-22, trip t-0401
      And table trips_rejected has trip t-0402 with reason "no fare"
      And table trips_rejected has trip t-0403 with reason "fare not above 0"
      And table trips_rejected has trip t-0404 with reason "fare not above 0"
