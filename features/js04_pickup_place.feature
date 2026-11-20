@JS04 @assistant
Feature: Pickup place of a rider's message
  Covers JS04 (support agent) in a system that includes the assistant, our extension. The assistant sends the
  rider's message to the model as the user message; the output format is a JSON object with one field,
  pickup_place: a name from evals/pickup_place/places.txt, or null when the message names no pickup place.
  Step code: this example repository has step code for this feature only, to show how an LLM eval runs in behave.
  You do not write step code for Checkpoint 1.

  @R110
  Rule: Where the system includes the assistant, a rider's message is shown with the pickup place it names, or the system says that it names no pickup place

    Example: Message that names a pickup place
      Given the rider message "I'm waiting outside JFK Terminal 4, door 6. Where is my driver?"
      When the support agent opens the message
      Then the pickup place is "JFK Terminal 4"

    Example: Message that names only a destination
      Given the rider message "Take me to Penn Station. I haven't decided where to be picked up yet."
      When the support agent opens the message
      Then the system says that the message names no pickup place

    @eval
    Example: Eval of pickup places
      Given the 10 cases of the eval "pickup-place"
      When the model that the system uses answers each case 3 times
      Then the pickup place is correct in at least 24 of the 30 runs
