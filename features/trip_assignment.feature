@JS02 @JS03
Feature: One driver for each trip
  Covers JS02 (driver): whether the trip I accepted is mine.
  Covers JS03 (rider): which driver is coming.
  A table holds the only events of its example. Its columns are event fields listed in docs/design.md, section Data.
  An accept is one request to our API. A simulated data set is named by its id and described in the same section.

  @R070
  Rule: When a driver accepts a trip that is requested and not assigned, the system shall assign the trip to that driver

    Example: One driver accepts
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000301 | t-0301  | 161            | 2026-11-23T09:20:00Z | 2026-11-23T09:20:01Z |
      When this accept is received:
        | event_id  | trip_id | driver_id | event_time           | received_time        |
        | ev-000302 | t-0301  | d-0046    | 2026-11-23T09:20:05Z | 2026-11-23T09:20:05Z |
      Then by 2026-11-23T09:20:06Z driver d-0046 has the answer that the trip is assigned to them

  @R080 @RF030
  Rule: If a driver accepts a trip that is already assigned, then the system shall refuse the accept and leave the trip with its driver

    Example: Two drivers accept at the same time
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000310 | t-0303  | 161            | 2026-11-23T09:20:00Z | 2026-11-23T09:20:01Z |
      When these accepts are sent together, each before the other has an answer:
        | event_id  | trip_id | driver_id | event_time           | received_time        |
        | ev-000311 | t-0303  | d-0046    | 2026-11-23T09:20:05Z | 2026-11-23T09:20:06Z |
        | ev-000312 | t-0303  | d-0131    | 2026-11-23T09:20:04Z | 2026-11-23T09:20:06Z |
      Then trip t-0303 is assigned to exactly one of drivers d-0046 and d-0131
      And 1 accept is refused

    Example: Accept of a trip that is already assigned
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000320 | t-0306  | 161            | 2026-11-23T09:30:00Z | 2026-11-23T09:30:01Z |
      And this accept is received:
        | event_id  | trip_id | driver_id | event_time           | received_time        |
        | ev-000321 | t-0306  | d-0046    | 2026-11-23T09:30:05Z | 2026-11-23T09:30:05Z |
      When this accept is received:
        | event_id  | trip_id | driver_id | event_time           | received_time        |
        | ev-000322 | t-0306  | d-0131    | 2026-11-23T09:30:09Z | 2026-11-23T09:30:09Z |
      Then by 2026-11-23T09:30:10Z driver d-0131 has the answer that the accept is refused
      And trip t-0306 is assigned to driver d-0046

    Example: Twenty trips, two drivers each
      Given the simulated data set SIM03 "double-accept"
      When the two accepts of every trip are sent together, each before the other has an answer
      Then every trip is assigned to exactly one of its two drivers
      And 20 accepts are refused

    # Question (Q020): which driver gets the trip when two accept at the same moment?

  @R090
  Rule: While a trip is assigned and not completed, the system shall show the rider the trip's driver

    Example: Rider looks after the accept
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000330 | t-0304  | 230            | 2026-11-23T09:35:00Z | 2026-11-23T09:35:01Z |
      And this accept is received:
        | event_id  | trip_id | driver_id | event_time           | received_time        |
        | ev-000331 | t-0304  | d-0046    | 2026-11-23T09:35:06Z | 2026-11-23T09:35:06Z |
      When the rider of trip t-0304 asks who is coming at 2026-11-23T09:36:00Z
      Then the rider is shown driver d-0046

  @R100
  Rule: When a trip is completed, the system shall show the rider the fare

    Example: Rider looks after the trip is completed
      Given only these trip requests are received:
        | event_id  | trip_id | pickup_zone_id | event_time           | received_time        |
        | ev-000340 | t-0305  | 48             | 2026-11-23T09:20:00Z | 2026-11-23T09:20:01Z |
      And this accept is received:
        | event_id  | trip_id | driver_id | event_time           | received_time        |
        | ev-000341 | t-0305  | d-0046    | 2026-11-23T09:20:07Z | 2026-11-23T09:20:07Z |
      When this completion is received:
        | trip_id | driver_id | dropoff_zone_id | trip_miles | trip_time_s | fare  | driver_pay | event_time           | received_time        |
        | t-0305  | d-0046    | 230             | 2.40       | 953         | 27.13 | 19.80      | 2026-11-23T09:41:00Z | 2026-11-23T09:41:01Z |
      Then by 2026-11-23T09:41:03Z the rider of trip t-0305 is shown the fare 27.13
