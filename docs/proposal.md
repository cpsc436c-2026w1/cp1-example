# Proposal (tagged `proposal`, short version for this example)

Team t00. A ride-hailing app on New York taxi zones, the case of lectures 1 to 14.

## 1. Business case

The app takes trip requests from riders, offers each to drivers nearby, and records the trip until it is completed
and paid. Our system receives the app's trip events and gives operations staff a live count of requests in each
zone, gives drivers and riders one answer about who has a trip, and keeps completed trips for analysis.

## 2. Job stories

From Checkpoint 1 the stories are headings in [`requirements.md`](requirements.md); that file is the record.

- **JS01 Operations analyst: trips requested in each zone** (operational and analytical)
- **JS02 Driver: is the trip mine** (operational)
- **JS03 Rider: who is coming**

## 3. Project shape and extensions

Operational first: the trips table answers drivers and riders, and the stream feeds the counts and the lake.
Extension: ~~an assistant that answers the analyst's questions about counts (R060).~~ An assistant that finds the
pickup place in a rider's message to support (JS04, R110; changed after the proposal).

## 4. Data and workflows

Moved to [`design.md`](design.md), sections Workflows and Data.

## 5. Architecture sketch

Moved to [`design.md`](design.md), section Sketch.

## 6. Experiments

None in this example.

## 7. User interaction points

A dashboard page with the counts by zone and period (JS01); an API answer to an accept (JS02) and to "who is
coming" (JS03).
