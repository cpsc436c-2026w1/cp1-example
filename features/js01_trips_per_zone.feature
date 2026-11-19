@JS01
Feature: Trips requested in each zone
  Covers the first part of JS01 (operations analyst): the number of trips requested in each pickup zone for each
  5-minute period. A period holds the requests with an event time from its start up to, and not including, its end.
  A table holds the only events of its example. A column left out has the example value of its field in
  docs/design.md, section Data, Event kinds. A simulated data set is named by its id and described in
  Simulated data sets.

  @R010
  Rule: When a 5-minute period ends, one count of requested trips is stored for each pickup zone that had a request

    Example: Three requests in one period
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000001 | t-0001  | 161            | 2026-11-23T09:01:10Z | 2026-11-23T09:01:11Z |
        | ev-000002 | t-0002  | 161            | 2026-11-23T09:03:40Z | 2026-11-23T09:03:41Z |
        | ev-000003 | t-0003  | 230            | 2026-11-23T09:04:58Z | 2026-11-23T09:04:59Z |
      When the period between 09:00 and 09:05 ends
      Then within 60 s zone 161 has 2 trips requested between 09:00 and 09:05
      And within 60 s zone 230 has 1 trip requested between 09:00 and 09:05

  @R020
  Rule: If a request is received after its period ended, it is added to the stored count of the period of its event time

    Example: Request received 7 minutes late
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000011 | t-0011  | 161            | 2026-11-23T09:01:10Z | 2026-11-23T09:01:11Z |
        | ev-000012 | t-0012  | 161            | 2026-11-23T09:04:00Z | 2026-11-23T09:11:00Z |
      When the time is 2026-11-23T09:12:00Z
      Then zone 161 has 2 trips requested between 09:00 and 09:05

  @R030
  Rule: Every count is shown with its zone and the start and end of its period

    Example: One count on the dashboard
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000021 | t-0021  | 230            | 2026-11-23T09:16:20Z | 2026-11-23T09:16:21Z |
      When the dashboard is opened at 2026-11-23T09:21:00Z
      Then the dashboard has a row with zone 230, start 09:15, end 09:20 and 1 trip requested

  @RF010
  Rule: Every trip request is counted exactly once, even when the stream delivers its event twice

    Example: One request delivered twice
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000101 | t-0101  | 161            | 2026-11-23T09:11:00Z | 2026-11-23T09:11:01Z |
        | ev-000102 | t-0102  | 161            | 2026-11-23T09:12:30Z | 2026-11-23T09:12:31Z |
        | ev-000101 | t-0101  | 161            | 2026-11-23T09:11:00Z | 2026-11-23T09:12:40Z |
      When the counts are read at 2026-11-23T09:16:00Z
      Then zone 161 shows 2 trips requested between 09:10 and 09:15

    Example: One simulated hour with 4 requests delivered twice
      Given the simulated data set SIM01 "rush-hour"
      When the counts are read at 2026-11-23T10:11:00Z
      Then every zone and period shows the count computed from the data set's record of events

    # Replay limit: a second delivery up to 24 hours after the first is not counted. We assume the app does not
    # send an event again after that (Q030).
    # Question (Q010): does a trip that the rider cancels still count as requested?

  @RF020
  Rule: A zone and period without events is shown as no data, not as 0 trips

    Example: Zone without a request in one period
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000201 | t-0201  | 48             | 2026-11-23T09:22:10Z | 2026-11-23T09:22:11Z |
        | ev-000202 | t-0202  | 161            | 2026-11-23T09:27:30Z | 2026-11-23T09:27:31Z |
        | ev-000203 | t-0203  | 48             | 2026-11-23T09:31:05Z | 2026-11-23T09:31:06Z |
      When the counts are read at 2026-11-23T09:36:00Z
      Then zone 48 shows no data between 09:25 and 09:30
      And zone 48 shows 1 trip requested between 09:20 and 09:25
      And zone 161 shows 1 trip requested between 09:25 and 09:30

    Example: Zone 48 quiet for 10 minutes of a simulated hour
      Given the simulated data set SIM02 "quiet-zone"
      When the counts are read at 2026-11-23T10:11:00Z
      Then zone 48 shows no data between 09:25 and 09:30
      And zone 48 shows no data between 09:30 and 09:35
      And every zone and period shows the count computed from the data set's record of events
