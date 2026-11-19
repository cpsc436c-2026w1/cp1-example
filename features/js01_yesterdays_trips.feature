@JS01
Feature: Yesterday's completed trips in one table
  Covers the second part of JS01 (operations analyst): each morning, yesterday's completed trips in one table.
  A simulated data set is named by its id and described in docs/design.md, section Data.
  Each example starts with tables trips_curated and trips_rejected empty.

  @R040
  Rule: When the file of a day's completed trips arrives, each row that has a fare above 0 is loaded into table trips_curated

    Example: File for 2026-11-22
      Given the simulated data set SIM04 "trips-day"
      When the file for 2026-11-22 arrives at 2026-11-23T05:10:00Z
      Then before 2026-11-23T06:00:00Z table trips_curated has 18590 rows for 2026-11-22

  @R050
  Rule: If a completed trip in the file has a fare that is missing, 0 or negative, it is left out of trips_curated and written to trips_rejected with the reason

    Example: File with a missing, a zero and a negative fare
      Given a file of completed trips with these rows:
        | trip_id | driver_id | dropoff_zone_id | trip_miles | trip_time_s | fare  | driver_pay | event_time           |
        | t-0401  | d-0046    | 68              | 0.86       | 462         | 9.11  | 6.56       | 2026-11-22T12:11:21Z |
        | t-0402  | d-0131    | 230             | 1.62       | 731         |       | 31.49      | 2026-11-22T14:30:00Z |
        | t-0403  | d-0007    | 161             | 2.40       | 905         | 0.00  | 12.80      | 2026-11-22T16:02:10Z |
        | t-0404  | d-0188    | 48              | 0.95       | 388         | -4.50 | 5.47       | 2026-11-22T18:45:33Z |
      When the file arrives at 2026-11-23T05:10:00Z
      Then before 2026-11-23T06:00:00Z table trips_curated has 1 row for 2026-11-22, trip t-0401
      And table trips_rejected has trip t-0402 with reason "no fare"
      And table trips_rejected has trip t-0403 with reason "fare not above 0"
      And table trips_rejected has trip t-0404 with reason "fare not above 0"

  @RF040 @live
  Rule: The count by zone over 30 days stays fast while the stream adds a small file to raw/ every minute
    The count is trips requested in each pickup zone from 2026-10-24 to 2026-11-22, read from the compacted files.

    Example: Thirty days of small files, compacted
      Given the simulated data set SIM05 "raw-30-days"
      And the data set is copied to raw/trip-events/ in the bucket
      And job t00-compact-events has run for each of the 30 days
      When the count by zone over 30 days runs 5 times in Athena while one small file a minute is added to raw/trip-events/
      Then table trip_events_compacted has 30 files, one for each day
      And every run counts 142310, 188010 and 194309 trips requested for zones 48, 161 and 230
      And the median run time is under 5 s
