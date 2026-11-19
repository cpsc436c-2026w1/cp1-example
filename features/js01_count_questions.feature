@JS01 @assistant
Feature: Questions about trip counts in plain language
  Covers JS01 (operations analyst) in a system that includes the assistant, our extension.

  @R060
  Rule: Where the system includes the assistant, a reply gives the count the question asks for and states only counts that are in the rows its query returned

    Example: Zone and period with a count
      Given the query for zone 161 between 09:10 and 09:15 returns these rows:
        | zone_id | period_start         | period_end           | trips_requested |
        | 161     | 2026-11-23T09:10:00Z | 2026-11-23T09:15:00Z | 12              |
      When the analyst asks "How many trips were requested in zone 161 between 09:10 and 09:15?"
      Then the reply states 12 trips requested
      And the reply does not state another count

    @eval
    Example: Eval of count answers
      Then the eval "count-answers" scores at least 0.8
