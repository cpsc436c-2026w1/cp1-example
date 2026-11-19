@JS01 @assistant
Feature: Questions about trip counts in plain language
  Covers JS01 (operations analyst) in a system that includes the assistant, our extension.

  @R060
  Rule: Where the system includes the assistant, a reply gives the count the question asks for and states only counts that are in the rows its query returned

    Example: Zone and period without rows
      Given the query for zone 48 between 09:25 and 09:30 returns 0 rows
      When the analyst asks "How many trips were requested in zone 48 between 09:25 and 09:30?"
      Then the reply says there is no data
      And the reply does not state a count

    @eval
    Example: Eval of count answers
      Then the eval "count-answers" scores at least 0.8
