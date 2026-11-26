-- Writes the three seed files in sim/seed/: the DS01 rows the simulated data sets are built from.
-- The subset in docs/design.md (Uber trips picked up in Manhattan, March 2024), three pickup zones.
-- Reads the month once (508 MB over HTTPS). Run from the repository root:
--   uvx --from duckdb-cli duckdb < tools/extract_seed.sql
CREATE TEMP TABLE three_zones AS
  SELECT request_datetime, pickup_datetime, dropoff_datetime,
         PULocationID AS pickup_zone_id, DOLocationID AS dropoff_zone_id,
         trip_miles, trip_time AS trip_time_s, base_passenger_fare AS fare, driver_pay
  FROM 'https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-03.parquet'
  WHERE hvfhs_license_num = 'HV0003'                     -- Uber
    AND PULocationID IN (48, 161, 230);                  -- Clinton East, Midtown Center, Times Sq/Theatre District

-- SIM01, SIM02, SIM03: one morning hour, New York local time as in the source. 837 rows.
COPY (
  SELECT * FROM three_zones
  WHERE request_datetime >= TIMESTAMP '2024-03-14 08:00:00'
    AND request_datetime <  TIMESTAMP '2024-03-14 09:00:00'
  ORDER BY request_datetime, pickup_zone_id, dropoff_datetime, trip_miles
) TO 'sim/seed/ds01_sample.csv' (HEADER);

-- SIM04: the whole day 2024-03-14. 19,074 rows.
COPY (
  SELECT request_datetime, pickup_zone_id, dropoff_zone_id, trip_miles, trip_time_s, fare, driver_pay
  FROM three_zones
  WHERE request_datetime >= TIMESTAMP '2024-03-14 00:00:00'
    AND request_datetime <  TIMESTAMP '2024-03-15 00:00:00'
  ORDER BY request_datetime, pickup_zone_id, dropoff_zone_id, trip_miles, fare, driver_pay, trip_time_s
) TO 'sim/seed/ds01_trips_day.csv.gz' (HEADER, COMPRESSION gzip);

-- SIM05: the requests of 2024-03-01 to 2024-03-30, counted by minute and zone (524,629 requests in 42,790 minutes).
COPY (
  SELECT strftime(date_trunc('minute', request_datetime), '%Y-%m-%d %H:%M') AS minute, pickup_zone_id,
         count(*) AS requests
  FROM three_zones
  WHERE request_datetime >= TIMESTAMP '2024-03-01 00:00:00'
    AND request_datetime <  TIMESTAMP '2024-03-31 00:00:00'
  GROUP BY 1, 2 ORDER BY 1, 2
) TO 'sim/seed/ds01_requests_by_minute.csv.gz' (HEADER, COMPRESSION gzip);
